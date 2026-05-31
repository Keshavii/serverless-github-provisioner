"""
Input Validation for Repository Creation Requests

Validates repository creation requests from JIRA webhooks with minimal overhead.
Since JIRA form fields enforce value constraints at submission time, this module
focuses exclusively on repository name format validation (kebab-case convention)
and presence checks for required fields.

Validation Philosophy:
    - Trust JIRA form validation for field content quality
    - Enforce strict repository naming conventions (GitHub requirements)
    - Fail fast on validation errors (non-retryable failures)
    - Provide actionable error messages for ticket creators
"""

import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from ..shared import ValidationError
from ..observability import log_and_monitor, log_execution_time


class RepositoryRequest(BaseModel):
    """
    Validation model for repository creation requests.

    Lightweight validation layer that trusts JIRA form field validation while
    enforcing strict repository naming conventions and presence checks for required
    organizational metadata.

    Validation Strategy:
        - Repository name: Strict kebab-case format validation (GitHub requirement)
        - Required fields: Presence check only (values pre-validated by JIRA)
        - Optional fields: No validation (may be null/empty)

    All mandatory fields are marked with `...` (Pydantic required field marker).
    """

    repo_name: str = Field(..., description="Repository name in kebab-case format (lowercase, hyphens only)")
    github_org: str = Field(..., description="Target GitHub organization for repository creation")
    description: str = Field(..., description="Repository purpose and scope description")
    vp_name: str = Field(..., description="Approving VP full name")
    director_name: str = Field(..., description="Approving Director full name")
    em_name: str = Field(..., description="Requesting Engineering Manager full name")
    product_line: str = Field(..., description="Product line or business unit")
    department: str = Field(..., description="Engineering department or team")
    repo_type: str = Field(..., description="Repository visibility type (Private or Internal)")
    code_type: str = Field(..., description="Primary programming language or framework")

    documentation_link: Optional[str] = Field(None, description="Optional link to technical design documentation")
    bucket_name: Optional[str] = Field(None, description="Optional AWS S3 bucket name for artifacts")
    additional_notes: Optional[str] = Field(None, description="Optional supplementary information or special requirements")
    cost_center: Optional[str] = Field(None, description="Optional cost center code for billing allocation")
    project_id: Optional[str] = Field(None, description="Optional project tracking identifier")
    jira_ticket_id: Optional[str] = Field(None, description="JIRA ticket ID for request tracking and status updates")

    @field_validator("repo_name")
    @classmethod
    def validate_repo_name(cls, v):
        """
        Validate repository name follows kebab-case convention.

        Enforces GitHub repository naming requirements and organizational standards.
        Repository names must be URL-safe, human-readable, and follow consistent
        naming patterns across the organization.

        Validation Rules:
            - Character set: Lowercase letters (a-z), numbers (0-9), hyphens (-)
            - Start/End: Must begin and end with alphanumeric character
            - Separators: Single hyphens only (no consecutive hyphens)
            - Length: 1-100 characters (GitHub repository name limit)

        Args:
            v: Repository name to validate

        Returns:
            str: Validated repository name

        Raises:
            ValidationError: If name violates any kebab-case formatting rules

        Examples:
            Valid: "my-service", "api-gateway-v2", "data-processor-123"
            Invalid: "MyService", "my_service", "my--service", "my-service-"
        """
        if not v or not v.strip():
            raise ValidationError(
                field="repo_name",
                message="Repository name cannot be empty",
                expected_format="kebab-case (e.g., my-service-name)",
            )

        pattern = r"^[a-z0-9]+([a-z0-9-]*[a-z0-9]+)?$"

        if not re.match(pattern, v):
            raise ValidationError(
                field="repo_name",
                message=f"Invalid repository name: '{v}'. Must be in kebab-case format.",
                expected_format="lowercase letters, numbers, and hyphens only. "
                "Example: my-service-name",
            )

        if "--" in v:
            raise ValidationError(
                field="repo_name",
                message=f"Invalid repository name: '{v}'. Consecutive hyphens are not allowed.",
                expected_format="no consecutive hyphens (e.g., my-service not my--service)",
            )

        if len(v) > 100:
            raise ValidationError(
                field="repo_name",
                message=f"Repository name too long: {len(v)} characters (max 100)",
                expected_format="1-100 characters",
            )

        return v.strip()

    @field_validator("github_org", "description")
    @classmethod
    def validate_required_non_empty(cls, v, info):
        """
        Validate that required text fields are not empty.

        Ensures critical fields like GitHub organization and repository description
        contain actual content and are not just whitespace. While Pydantic ensures
        these fields are present, it allows empty strings which would cause failures
        during GitHub API calls.

        Args:
            v: Field value to validate
            info: Pydantic field information context

        Returns:
            str: Validated and trimmed field value

        Raises:
            ValidationError: If field is None, empty string, or only whitespace
        """
        field_name = info.field_name
        if not v or not v.strip():
            raise ValidationError(
                field=field_name,
                message=f"{field_name.replace('_', ' ').title()} cannot be empty",
                expected_format="non-empty text value",
            )
        return v.strip()

    @field_validator("vp_name", "director_name", "em_name", "product_line", "department")
    @classmethod
    def validate_organizational_fields(cls, v, info):
        """
        Validate organizational approval and metadata fields.

        Ensures all organizational metadata (approver names, department info) are
        populated with actual values. These fields are required for audit trails,
        cost allocation, and organizational reporting.

        Args:
            v: Field value to validate
            info: Pydantic field information context

        Returns:
            str: Validated and trimmed field value

        Raises:
            ValidationError: If field is None, empty string, or only whitespace
        """
        field_name = info.field_name
        if not v or not v.strip():
            raise ValidationError(
                field=field_name,
                message=f"{field_name.replace('_', ' ').title()} cannot be empty",
                expected_format="non-empty text value",
            )
        return v.strip()


def validate_input(
    event_data: Dict[str, Any], correlation_id: str = None
) -> RepositoryRequest:
    """
    Validate repository creation request from JIRA webhook.

    Primary validation entry point that processes raw JIRA webhook data and returns
    a validated RepositoryRequest object. Delegates to Pydantic for field presence
    and type validation, with custom kebab-case validation for repository names.

    Validation Scope:
        - Repository name format (kebab-case via custom validator)
        - Required field presence (Pydantic required fields)
        - Type correctness for all fields (Pydantic type annotations)

    Error Handling:
        All validation errors are non-retryable (permanent failures). When validation
        fails, the request is sent to the Dead Letter Queue for manual review. JIRA
        ticket is updated with specific validation error details to guide correction.

    Performance:
        Execution time is monitored and logged for performance tracking. Typical
        validation completes in <10ms for standard requests.

    Args:
        event_data: Raw event data dictionary from JIRA webhook payload
        correlation_id: Optional correlation ID for distributed tracing across services

    Returns:
        RepositoryRequest: Validated and typed repository request object

    Raises:
        ValidationError: On any validation failure (non-retryable, permanent error)

    Example:
        >>> event = {
        ...     "repo_name": "my-service",
        ...     "github_org": "my-org",
        ...     "description": "New microservice",
        ...     ...
        ... }
        >>> request = validate_input(event, correlation_id="abc-123")
        >>> print(request.repo_name)
        'my-service'
    """
    with log_execution_time(
        "validate_input",
        correlation_id=correlation_id,
        jira_ticket_id=event_data.get("jira_ticket_id"),
    ):
        try:
            validated = RepositoryRequest(**event_data)

            log_and_monitor(
                "input_validation_success",
                level="INFO",
                correlation_id=correlation_id,
                jira_ticket_id=validated.jira_ticket_id,
                repo_name=validated.repo_name,
                github_org=validated.github_org,
            )

            return validated

        except ValidationError:
            raise

        except Exception as e:
            error_msg = str(e)
            field = "unknown"

            if hasattr(e, "errors"):
                pydantic_errors = e.errors()
                if pydantic_errors:
                    first_error = pydantic_errors[0]
                    field = first_error.get("loc", ("unknown",))[0]
                    error_msg = first_error.get("msg", str(e))

            log_and_monitor(
                "input_validation_failed",
                level="ERROR",
                correlation_id=correlation_id,
                field=field,
                error=error_msg,
            )

            raise ValidationError(
                field=field, message=f"Validation failed: {error_msg}"
            )
