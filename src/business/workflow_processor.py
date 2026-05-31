"""
Repository Creation Workflow Processor

Contains core business logic for GitHub repository creation workflows.
Implements a clean separation from AWS Lambda infrastructure to enable
testability, reusability across different execution contexts, and easier
unit testing without AWS mocking.
"""

import traceback
from typing import Dict, Any

from ..integrations.github import create_github_repository, check_repository_exists
from ..integrations.jira.client import update_jira_success, update_jira_failure, update_jira_already_exists
from .validators import validate_input
from ..shared import ValidationError, GitHubAPIError, JiraAPIError
from ..observability import log_and_monitor
from ..integrations.messaging import (
    notify_validation_error,
    notify_permission_error,
    notify_github_error,
    notify_jira_error
)
from ..shared import categorize_github_error, format_error_message_for_jira, should_retry_error


def process_repository_request(message_data: Dict[str, Any], correlation_id: str) -> bool:
    """
    Process repository creation request from JIRA ticket data.

    Orchestrates the complete repository creation workflow including validation,
    idempotency checks, repository creation, and JIRA ticket updates. Implements
    comprehensive error handling with categorization for retry decisions.

    Workflow Steps:
        1. Validate input data from JIRA ticket
        2. Check repository existence for idempotency
        3. Create GitHub repository with specified configuration
        4. Update JIRA ticket with success or error details
        5. Handle errors with appropriate categorization and notifications

    Args:
        message_data: Dictionary containing JIRA ticket data including
                     repo_name, org_name, ticket_id, and optional fields
        correlation_id: Unique identifier for request tracing across logs

    Returns:
        True if processing completed successfully or encountered a permanent
             failure (message should be removed from queue)
        False if transient error occurred (message should be retried via SQS)

    Error Handling:
        - Validation errors: Notify user, return True (permanent failure)
        - Permission errors: Notify user, return True (permanent failure)
        - Business rule violations: Notify user, return True (permanent failure)
        - Transient errors: Log and return False (retry)
    """
    ticket_id = message_data.get('ticket_id')
    
    try:
        log_and_monitor(
            "validating_input",
            level="INFO",
            correlation_id=correlation_id,
            ticket_id=ticket_id
        )
        
        validated_data = validate_input(message_data, correlation_id)
        
        repo_exists, existing_repo_data = check_repository_exists(
            org=validated_data.github_org,
            repo_name=validated_data.repo_name,
            correlation_id=correlation_id
        )

        if repo_exists:
            log_and_monitor(
                "repository_already_exists",
                level="INFO",
                correlation_id=correlation_id,
                ticket_id=ticket_id,
                repo_name=validated_data.repo_name,
                repo_url=existing_repo_data["html_url"]
            )

            update_jira_already_exists(
                ticket_id,
                existing_repo_data,
                correlation_id
            )
            return True

        log_and_monitor(
            "creating_repository",
            level="INFO",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            repo_name=validated_data.repo_name
        )

        repo_data = create_github_repository(validated_data, correlation_id)

        log_and_monitor(
            "updating_jira_success",
            level="INFO",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            repo_url=repo_data.get('html_url')
        )

        update_jira_success(ticket_id, repo_data, correlation_id)

        return True

    except ValidationError as e:
        return _handle_validation_error(e, ticket_id, message_data, correlation_id)

    except GitHubAPIError as e:
        return _handle_github_error(e, ticket_id, correlation_id)

    except JiraAPIError as e:
        return _handle_jira_error(e, ticket_id, correlation_id)

    except Exception as e:
        return _handle_unexpected_error(e, ticket_id, correlation_id)


def _handle_validation_error(
    error: ValidationError,
    ticket_id: str,
    message_data: Dict[str, Any],
    correlation_id: str
) -> bool:
    """
    Handle validation errors.
    
    Validation errors are permanent (don't retry).
    """
    log_and_monitor(
        "validation_error",
        level="ERROR",
        correlation_id=correlation_id,
        ticket_id=ticket_id,
        error=str(error),
        error_category="validation"
    )

    update_jira_failure(ticket_id, str(error), correlation_id)

    notify_validation_error(
        ticket_id=ticket_id,
        repo_name=message_data.get('repo_name', 'unknown'),
        github_org=message_data.get('github_org', 'unknown'),
        error_message=str(error),
        correlation_id=correlation_id
    )

    return True


def _handle_github_error(error: GitHubAPIError, ticket_id: str, correlation_id: str) -> bool:
    """
    Handle GitHub API errors.

    Transient errors (5xx, 429, etc.) trigger retry.
    Permanent errors (4xx) update JIRA and don't retry.
    """
    error_category = categorize_github_error(error)

    if should_retry_error(error_category):
        log_and_monitor(
            "retryable_github_error",
            level="WARNING",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            error=str(error),
            error_category=error_category,
            status_code=error.status_code,
            message="Retrying silently. JIRA will be updated only if all retries fail (via DLQ handler)"
        )

        return False

    else:
        log_and_monitor(
            "permanent_github_error",
            level="ERROR",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            error=str(error),
            error_category=error_category,
            status_code=error.status_code
        )

        error_msg = format_error_message_for_jira(error, error_category)

        update_jira_failure(ticket_id, error_msg, correlation_id)

        if error_category == "permission":
            notify_permission_error(
                ticket_id=ticket_id,
                error_message=error_msg,
                correlation_id=correlation_id
            )
        else:
            notify_github_error(
                ticket_id=ticket_id,
                error_type=error_category,
                error_message=error_msg,
                status_code=error.status_code,
                correlation_id=correlation_id
            )

        return True


def _handle_jira_error(error: JiraAPIError, ticket_id: str, correlation_id: str) -> bool:
    """
    Handle JIRA API errors.

    Transient errors trigger retry with idempotency protection.
    Permanent errors require manual intervention.
    """
    if error.is_retryable:
        log_and_monitor(
            "retryable_jira_error",
            level="WARNING",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            error=str(error),
            status_code=error.status_code,
            message="JIRA temporarily unavailable. Retrying - idempotency will handle duplicate repo creation"
        )

        return False

    else:
        log_and_monitor(
            "permanent_jira_error",
            level="ERROR",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            error=str(error),
            status_code=error.status_code,
            message="Repository created successfully but JIRA update failed permanently. Manual JIRA update required."
        )

        notify_jira_error(
            ticket_id=ticket_id,
            error_message=str(error),
            status_code=error.status_code,
            correlation_id=correlation_id
        )

        return True


def _handle_unexpected_error(error: Exception, ticket_id: str, correlation_id: str) -> bool:
    """
    Handle unexpected errors.

    Logs the error, attempts to update JIRA (best effort), and triggers retry.
    """
    log_and_monitor(
        "unexpected_error",
        level="ERROR",
        correlation_id=correlation_id,
        ticket_id=ticket_id,
        error=str(error),
        error_type=type(error).__name__,
        traceback=traceback.format_exc()
    )

    try:
        update_jira_failure(ticket_id, str(error), correlation_id)
    except Exception:
        pass

    return False
