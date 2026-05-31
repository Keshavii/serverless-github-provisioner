"""
Custom Exception Hierarchy

Defines specialized exception classes for GitHub repository automation workflows.
Provides structured error information with context metadata, supports JSON serialization
for structured logging, and categorizes errors by retryability for intelligent Dead
Letter Queue routing and retry logic.

Exception Hierarchy:
    BaseAutomationError (abstract base)
    ├── ValidationError (non-retryable)
    ├── ConfigurationError (non-retryable)
    ├── GitHubAPIError (conditionally retryable)
    │   ├── OrganizationNotFoundError (non-retryable)
    │   ├── RepositoryAlreadyExistsError (non-retryable, treated as success)
    │   └── InsufficientPermissionsError (non-retryable except rate limits)
    └── JiraAPIError (conditionally retryable)

Retryability Strategy:
    Non-Retryable: Validation, configuration, 4xx client errors (except rate limits)
    Retryable: Network errors, 5xx server errors, rate limits (403/429)
"""


class BaseAutomationError(Exception):
    """
    Base exception class for all automation workflow errors.

    Provides common exception interface with structured error details and serialization
    support for consistent error handling and logging across the application.

    Attributes:
        message: Human-readable error description
        details: Dictionary containing additional error context
    """

    def __init__(self, message: str, details: dict = None):
        """
        Initialize base automation error.

        Args:
            message: Error description for logging and user feedback
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """
        Serialize exception to dictionary for structured logging.

        Converts exception to JSON-compatible dictionary format for log_and_monitor
        integration and CloudWatch Insights queries.

        Returns:
            Dictionary containing error_type, message, and details fields
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(BaseAutomationError):
    """
    Raised when input validation fails due to malformed or missing data.

    Non-retryable permanent failure indicating client-side error requiring corrective
    action. Triggers immediate notification and Dead Letter Queue routing.

    Common Scenarios:
        - Missing required fields (repo_name, jira_ticket_id)
        - Invalid format (malformed repository name, invalid ticket key)
        - Out-of-range values (repository name too long)

    Attributes:
        field: Name of the field that failed validation
        expected_format: Description of expected format or constraints
    """

    def __init__(self, field: str, message: str, expected_format: str = None):
        """
        Initialize validation error with field context.

        Args:
            field: Field name that failed validation (e.g., 'repo_name', 'jira_ticket_id')
            message: Detailed validation failure message
            expected_format: Optional description of expected format or constraints
        """
        details = {"field": field, "expected_format": expected_format}
        super().__init__(message, details)
        self.field = field
        self.expected_format = expected_format


class GitHubAPIError(BaseAutomationError):
    """
    Raised when GitHub REST API calls fail or return error responses.

    Potentially retryable transient failure depending on HTTP status code. Supports
    automatic retry logic for network errors and rate limit scenarios.

    Retryable Scenarios:
        - Network timeouts and connection errors (no status code)
        - Rate limit errors (403 with rate limit message, 429)
        - Server errors (500, 502, 503, 504)
        - Request timeouts (408)

    Non-Retryable Scenarios:
        - Client errors (400, 401, 404, 422)
        - Permission errors (403 without rate limit)

    Attributes:
        status_code: HTTP status code from GitHub API response
        response_body: Parsed JSON response body with error details
    """

    def __init__(
        self, message: str, status_code: int = None, response_body: dict = None
    ):
        """
        Initialize GitHub API error with response metadata.

        Args:
            message: Error description from API or generated message
            status_code: HTTP status code (None for network errors)
            response_body: Parsed JSON response containing GitHub error details
        """
        details = {"status_code": status_code, "response_body": response_body}
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body

    @property
    def is_retryable(self) -> bool:
        """
        Determine if error should trigger automatic retry.

        Analyzes HTTP status code and error message to categorize as transient
        (retryable) or permanent (non-retryable) failure.

        Returns:
            True if error is transient and retry may succeed, False otherwise

        Retry Logic:
            - Network errors (no status code): Always retryable
            - Rate limits (403/429 with rate limit message): Retryable
            - Server errors (5xx): Retryable
            - Client errors (4xx): Not retryable
        """
        if self.status_code is None:
            return True

        retryable_codes = {
            408,
            429,
            500,
            502,
            503,
            504,
        }

        if self.status_code == 403 and self.message and "rate limit" in self.message.lower():
            return True

        return self.status_code in retryable_codes


class JiraAPIError(BaseAutomationError):
    """
    Raised when JIRA REST API calls fail or return error responses.

    Potentially retryable transient failure depending on HTTP status code. Supports
    automatic retry logic for network errors and server-side issues.

    Retryable Scenarios:
        - Network timeouts and connection errors (no status code)
        - Rate limit errors (429)
        - Server errors (500, 502, 503, 504)
        - Request timeouts (408)

    Non-Retryable Scenarios:
        - Client errors (400, 401, 404)
        - Permission errors (403)
        - Resource conflict errors (409)

    Attributes:
        status_code: HTTP status code from JIRA API response
        response_body: Parsed JSON response body with error details
    """

    def __init__(
        self, message: str, status_code: int = None, response_body: dict = None
    ):
        """
        Initialize JIRA API error with response metadata.

        Args:
            message: Error description from API or generated message
            status_code: HTTP status code (None for network errors)
            response_body: Parsed JSON response containing JIRA error details
        """
        details = {"status_code": status_code, "response_body": response_body}
        super().__init__(message, details)
        self.status_code = status_code
        self.response_body = response_body

    @property
    def is_retryable(self) -> bool:
        """
        Determine if error should trigger automatic retry.

        Analyzes HTTP status code to categorize as transient (retryable) or
        permanent (non-retryable) failure for JIRA API operations.

        Returns:
            True if error is transient and retry may succeed, False otherwise

        Retry Logic:
            - Network errors (no status code): Always retryable
            - Rate limits (429): Retryable
            - Server errors (5xx): Retryable
            - Client errors (4xx): Not retryable
        """
        if self.status_code is None:
            return True

        retryable_codes = {
            408,
            429,
            500,
            502,
            503,
            504,
        }

        return self.status_code in retryable_codes


class ConfigurationError(BaseAutomationError):
    """
    Raised when environment configuration is invalid or missing.

    Non-retryable permanent failure indicating deployment or environment setup issue.
    Requires administrator intervention to resolve missing secrets, invalid URLs,
    or misconfigured environment variables.

    Common Scenarios:
        - Missing AWS Secrets Manager secret ARN
        - Invalid GitHub API endpoint URL
        - Missing required environment variables
        - Malformed configuration values

    Usage:
        Should be raised during application initialization or settings validation
        before processing workflow requests.
    """

    pass


class OrganizationNotFoundError(GitHubAPIError):
    """
    Raised when specified GitHub organization does not exist.

    Non-retryable permanent failure indicating incorrect organization name in
    configuration or JIRA ticket metadata. Requires verification of organization
    name and correction in source system.

    Common Causes:
        - Typographical error in organization name
        - Organization renamed or deleted
        - Token lacks access to organization

    Attributes:
        org_name: The organization name that was not found
    """

    def __init__(self, org_name: str):
        """
        Initialize organization not found error.

        Args:
            org_name: GitHub organization name that does not exist
        """
        super().__init__(
            message=f"GitHub organization '{org_name}' not found",
            status_code=404,
            response_body={"error": "organization_not_found", "org_name": org_name},
        )
        self.org_name = org_name

    @property
    def is_retryable(self) -> bool:
        """
        Override retryability check for organization not found.

        Returns:
            False - Organization existence will not change on retry
        """
        return False


class RepositoryAlreadyExistsError(GitHubAPIError):
    """
    Raised when attempting to create repository that already exists.

    Non-retryable idempotent scenario indicating successful prior creation. Workflow
    treats this as success and updates JIRA ticket with existing repository information.

    Handling Strategy:
        - Not treated as error in workflow logic
        - JIRA ticket updated with repository_already_exists status
        - No Slack notification sent (silent success)
        - No retry or DLQ routing

    Attributes:
        repo_name: Repository name that already exists
        org_name: Organization containing the existing repository
    """

    def __init__(self, repo_name: str, org_name: str):
        """
        Initialize repository already exists error.

        Args:
            repo_name: Name of repository that already exists
            org_name: GitHub organization containing the repository
        """
        super().__init__(
            message=f"Repository '{org_name}/{repo_name}' already exists",
            status_code=422,
            response_body={
                "error": "repository_already_exists",
                "repo_name": repo_name,
                "org_name": org_name,
            },
        )
        self.repo_name = repo_name
        self.org_name = org_name

    @property
    def is_retryable(self) -> bool:
        """
        Override retryability check for repository already exists.

        Returns:
            False - Repository existence will not change on retry
        """
        return False


class InsufficientPermissionsError(GitHubAPIError):
    """
    Raised when GitHub token lacks required permissions for operation.

    Non-retryable permanent failure unless caused by rate limiting. Indicates
    GitHub token needs elevated permissions or organization admin intervention.

    Required Permissions:
        - Repository creation: admin:org or repo scope
        - Organization access: read:org scope minimum
        - Team membership: read:org scope

    Common Causes:
        - Personal Access Token with insufficient scopes
        - GitHub App with restricted permissions
        - Organization security settings blocking API access
        - User not member of target organization

    Attributes:
        operation: Description of operation that was denied
    """

    def __init__(self, operation: str, message: str = None):
        """
        Initialize insufficient permissions error.

        Args:
            operation: Operation that was denied (e.g., 'create repository')
            message: Optional custom error message (default: generated from operation)
        """
        default_msg = f"Insufficient permissions to {operation}"
        super().__init__(
            message=message or default_msg,
            status_code=403,
            response_body={"error": "insufficient_permissions", "operation": operation},
        )
        self.operation = operation

    @property
    def is_retryable(self) -> bool:
        """
        Override retryability check for permission errors.

        Permission errors are non-retryable except when 403 status indicates
        rate limiting rather than authorization failure.

        Returns:
            True only if error message contains rate limit indication, False otherwise
        """
        return "rate limit" in self.message.lower()


