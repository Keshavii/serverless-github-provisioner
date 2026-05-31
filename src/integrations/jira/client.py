"""
Function 4: JIRA API Integration
Update JIRA tickets with success or failure messages.
"""

import time
from typing import Dict

from jira import JIRA
from jira.exceptions import JIRAError

from ...config import get_settings
from ...shared import JiraAPIError
from ...observability import log_and_monitor, log_execution_time, emit_latency_metric


class JiraClient:
    """JIRA API client wrapper with error handling."""

    def __init__(self):
        """
        Initialize JIRA client using settings from config.py.

        All credentials are loaded from environment variables via get_settings().
        No parameter overrides allowed - ensures single source of truth.
        """
        settings = get_settings()
        self.jira_url = settings.jira_url
        self.email = settings.jira_email
        self.api_token = settings.jira_api_token
        self.timeout = settings.jira_api_timeout

        try:
            self.client = JIRA(
                server=self.jira_url,
                basic_auth=(self.email, self.api_token),
                timeout=self.timeout,
            )
            # Verify authentication
            self.client.myself()
        except Exception as e:
            raise JiraAPIError(
                message=f"Failed to authenticate with JIRA: {str(e)}",
                status_code=None,
                response_body=None,
            )

    def _handle_jira_exception(self, e: Exception, operation: str) -> None:
        """
        Convert JIRA exceptions to JiraAPIError.

        Args:
            e: Exception from JIRA API
            operation: Operation being performed (for error message)

        Raises:
            JiraAPIError: Converted exception with status code and details
        """
        if isinstance(e, JIRAError):
            status_code = e.status_code
            response_body = {"message": str(e)}

            # Extract more details if available
            if hasattr(e, "response") and e.response:
                try:
                    response_body = e.response.json()
                except Exception:
                    response_body = {"text": e.response.text}

            error_msg = f"JIRA API error during {operation}: {str(e)}"

            # Add specific error messages for common status codes
            if status_code == 401:
                error_msg = "JIRA authentication failed. Please check your credentials."
            elif status_code == 403:
                error_msg = (
                    f"JIRA permission denied during {operation}. "
                    "Please check your user has the required permissions."
                )
            elif status_code == 404:
                error_msg = f"JIRA ticket not found during {operation}."

            raise JiraAPIError(
                message=error_msg, status_code=status_code, response_body=response_body
            )
        else:
            # Generic exception (network errors, timeouts, etc.)
            raise JiraAPIError(
                message=f"Unexpected error during {operation}: {str(e)}",
                status_code=None,
                response_body={"error": str(e)},
            )


def update_jira_success(
    ticket_id: str, repo_data: Dict, correlation_id: str = None
) -> bool:
    """
    Function 4: Update JIRA Ticket with Success Message

    Updates the JIRA ticket with repository creation success details.
    This function is retryable for transient errors.

    Args:
        ticket_id: JIRA ticket ID (e.g., 'ENG-12345')
        repo_data: Repository data from GitHub (URLs, ID, etc.)
        correlation_id: Correlation ID for tracing

    Returns:
        bool: True if update succeeded

    Raises:
        JiraAPIError: When JIRA update fails (retryable)
    """
    with log_execution_time(
        "update_jira_success",
        correlation_id=correlation_id,
        jira_ticket_id=ticket_id,
        repo_name=repo_data.get("name"),
    ):
        try:
            client = JiraClient()

            # Build success comment
            comment_text = _build_success_comment(repo_data)

            # Add comment to JIRA ticket
            api_start_time = time.time()
            client.client.add_comment(ticket_id, comment_text)
            api_duration = (time.time() - api_start_time) * 1000

            # Emit latency metric for JIRA add_comment
            emit_latency_metric(
                'JiraAPI',
                api_duration,
                dimensions={'Operation': 'add_comment'}
            )

            # Add labels
            try:
                api_start_time = time.time()
                issue = client.client.issue(ticket_id)
                current_labels = issue.fields.labels or []
                new_labels = list(set(current_labels + ["repository-created", "automated"]))
                issue.update(fields={"labels": new_labels})
                api_duration = (time.time() - api_start_time) * 1000

                # Emit latency metric for JIRA get_issue and update
                emit_latency_metric(
                    'JiraAPI',
                    api_duration,
                    dimensions={'Operation': 'update_labels'}
                )
            except Exception as label_error:
                # Log warning but don't fail if labels can't be updated
                log_and_monitor(
                    "jira_label_update_warning",
                    level="WARNING",
                    correlation_id=correlation_id,
                    jira_ticket_id=ticket_id,
                    error=str(label_error),
                )

            # NEW: Transition ticket to Done (if enabled)
            transition_ticket_on_success(ticket_id, repo_data, correlation_id)

            log_and_monitor(
                "jira_update_success",
                level="INFO",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                repo_name=repo_data.get("name"),
                repo_url=repo_data.get("html_url"),
            )

            return True

        except JiraAPIError:
            # Re-raise our custom error
            log_and_monitor(
                "jira_update_failed",
                level="ERROR",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                error_type="JiraAPIError",
            )
            raise

        except JIRAError as e:
            # Handle JIRA-specific exceptions
            log_and_monitor(
                "jira_update_failed",
                level="ERROR",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                error=str(e),
                error_type="JIRAError",
            )

            client_instance = JiraClient()
            client_instance._handle_jira_exception(e, "update ticket with success")

        except Exception as e:
            # Handle unexpected errors
            log_and_monitor(
                "jira_update_failed",
                level="ERROR",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            raise JiraAPIError(
                message=f"Unexpected error updating JIRA ticket: {str(e)}",
                status_code=None,
                response_body={"error": str(e)},
            )


def transition_ticket_on_success(
    ticket_id: str,
    repo_data: Dict,
    correlation_id: str = None
) -> bool:
    """
    Transition ticket to 'Done' state after successful repository creation.

    This function implements automatic ticket closure to reduce manual work
    and improve workflow tracking in JIRA.

    Args:
        ticket_id: JIRA ticket ID
        repo_data: Repository data from GitHub
        correlation_id: Correlation ID for tracing

    Returns:
        bool: True if transition succeeded, False otherwise (best-effort)
    """
    settings = get_settings()

    # Check if auto-transition is enabled
    if not settings.auto_transition_on_success:
        log_and_monitor(
            "ticket_transition_skipped",
            level="INFO",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            reason="auto_transition_disabled"
        )
        return False

    try:
        client = JiraClient()

        # Get available transitions for this ticket
        api_start_time = time.time()
        transitions = client.client.transitions(ticket_id)
        api_duration = (time.time() - api_start_time) * 1000

        # Emit latency metric for JIRA get transitions
        emit_latency_metric(
            'JiraAPI',
            api_duration,
            dimensions={'Operation': 'get_transitions'}
        )

        # Find the target transition
        target_transition = None
        for t in transitions:
            if t['name'].lower() == settings.success_transition_name.lower():
                target_transition = t['id']
                break

        if not target_transition:
            log_and_monitor(
                "transition_not_found",
                level="WARNING",
                correlation_id=correlation_id,
                ticket_id=ticket_id,
                target_status=settings.success_transition_name,
                available_transitions=[t['name'] for t in transitions]
            )
            return False

        # Prepare transition fields (some workflows require resolution)
        transition_fields = {}
        if settings.success_resolution:
            transition_fields['resolution'] = {
                'name': settings.success_resolution
            }

        # Execute the transition
        api_start_time = time.time()
        client.client.transition_issue(
            ticket_id,
            target_transition,
            fields=transition_fields if transition_fields else None
        )
        api_duration = (time.time() - api_start_time) * 1000

        # Emit latency metric for JIRA transition
        emit_latency_metric(
            'JiraAPI',
            api_duration,
            dimensions={'Operation': 'transition_issue'}
        )

        log_and_monitor(
            "ticket_transitioned_to_done",
            level="INFO",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            new_status=settings.success_transition_name,
            repo_name=repo_data.get('name')
        )

        return True

    except Exception as e:
        # Best-effort: log warning but don't fail the overall process
        log_and_monitor(
            "ticket_transition_failed",
            level="WARNING",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            error=str(e),
            error_type=type(e).__name__
        )
        return False


def _build_success_comment(repo_data: Dict) -> str:
    """
    Build formatted success comment for JIRA.

    Args:
        repo_data: Repository data from GitHub

    Returns:
        str: Formatted comment text in JIRA markup
    """
    comment_lines = [
        "✅ *Repository Created Successfully!*",
        "",
        "*Repository Details:*",
        f"• *Name:* {repo_data.get('name')}",
        f"• *Organization:* {repo_data.get('owner')}",
        f"• *Visibility:* {repo_data.get('visibility')}",
        "",
        "*Repository URLs:*",
        f"• *Web:* [{repo_data.get('html_url')}|{repo_data.get('html_url')}]",
        f"• *Clone (HTTPS):* {{code}}{repo_data.get('clone_url')}{{code}}",
        f"• *Clone (SSH):* {{code}}{repo_data.get('ssh_url')}{{code}}",
        "",
        f"• *Repository ID:* {repo_data.get('id')}",
        f"• *Created At:* {repo_data.get('created_at', 'N/A')}",
        "",
        "*Next Steps:*",
        "# Clone the repository using one of the URLs above",
        "# Push your initial code to the repository",
        "# Verify the repository settings and permissions",
        "# Close this Change Request",
        "",
        "---",
        "_This repository was created automatically by the GitHub Auto-Provisioning System._",
    ]

    return "\n".join(comment_lines)


def update_jira_already_exists(
    ticket_id: str, repo_data: Dict, correlation_id: str = None
) -> bool:
    """
    Update JIRA Ticket when Repository Already Exists (Idempotent)

    Updates the JIRA ticket when the repository already exists in GitHub.
    This is part of the idempotent design - if a repository already exists,
    we treat it as success but with a different message.

    Args:
        ticket_id: JIRA ticket ID (e.g., 'ENG-12345')
        repo_data: Existing repository data from GitHub (URLs, ID, etc.)
        correlation_id: Correlation ID for tracing

    Returns:
        bool: True if update succeeded

    Raises:
        JiraAPIError: When JIRA update fails (retryable)
    """
    with log_execution_time(
        "update_jira_already_exists",
        correlation_id=correlation_id,
        jira_ticket_id=ticket_id,
        repo_name=repo_data.get("name"),
    ):
        try:
            client = JiraClient()

            # Build "already exists" comment
            comment_text = _build_already_exists_comment(repo_data)

            # Add comment to JIRA ticket
            client.client.add_comment(ticket_id, comment_text)

            # Add labels (different from creation)
            try:
                issue = client.client.issue(ticket_id)
                current_labels = issue.fields.labels or []
                new_labels = list(set(current_labels + ["repository-already-exists", "automated"]))
                issue.update(fields={"labels": new_labels})
            except Exception as label_error:
                # Log warning but don't fail if labels can't be updated
                log_and_monitor(
                    "jira_label_update_warning",
                    level="WARNING",
                    correlation_id=correlation_id,
                    jira_ticket_id=ticket_id,
                    error=str(label_error),
                )

            # NOTE: We might not want to auto-transition when repo already exists
            # Users might want to manually verify it's the correct repo
            # added beacuse there should be a way to auto close tickets when repo already exists
            transition_ticket_on_success(ticket_id, repo_data, correlation_id)


            log_and_monitor(
                "jira_already_exists_update_success",
                level="INFO",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                repo_name=repo_data.get("name"),
                repo_url=repo_data.get("html_url"),
            )

            return True

        except JiraAPIError:
            # Re-raise our custom error
            log_and_monitor(
                "jira_already_exists_update_failed",
                level="ERROR",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                error_type="JiraAPIError",
            )
            raise

        except JIRAError as e:
            # Handle JIRA-specific exceptions
            log_and_monitor(
                "jira_already_exists_update_failed",
                level="ERROR",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                error=str(e),
                error_type="JIRAError",
            )

            client_instance = JiraClient()
            client_instance._handle_jira_exception(e, "update ticket with already exists message")

        except Exception as e:
            # Handle unexpected errors
            log_and_monitor(
                "jira_already_exists_update_failed",
                level="ERROR",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            raise JiraAPIError(
                message=f"Unexpected error updating JIRA ticket: {str(e)}",
                status_code=None,
                response_body={"error": str(e)},
            )


def _build_already_exists_comment(repo_data: Dict) -> str:
    """
    Build formatted comment for when repository already exists.

    Args:
        repo_data: Repository data from GitHub

    Returns:
        str: Formatted comment text in JIRA markup
    """
    comment_lines = [
        "⚠️  *Repository Already Exists*",
        "",
        "The requested repository already exists in GitHub. This is normal behavior (idempotent operation).",
        "",
        "*Repository Details:*",
        f"• *Name:* {repo_data.get('name')}",
        f"• *Organization:* {repo_data.get('owner')}",
        f"• *Visibility:* {repo_data.get('visibility')}",
        f"• *Created At:* {repo_data.get('created_at', 'N/A')}",
        "",
        "*Repository URLs:*",
        f"• *Web:* [{repo_data.get('html_url')}|{repo_data.get('html_url')}]",
        f"• *Clone (HTTPS):* {{code}}{repo_data.get('clone_url')}{{code}}",
        f"• *Clone (SSH):* {{code}}{repo_data.get('ssh_url')}{{code}}",
        "",
        f"• *Repository ID:* {repo_data.get('id')}",
        "",
        "*What This Means:*",
        "✅ Your repository is ready to use",
        "✅ No changes were made (repository already exists)",
        "✅ This is expected behavior - the system is idempotent",
        "",
        "*Next Steps:*",
        "# Verify this is the correct repository",
        "# Check that you have the appropriate access permissions",
        "# Review the repository settings if needed",
        "# Close this Change Request",
        "",
        "---",
        "_This message was generated automatically by the GitHub Auto-Provisioning System._",
    ]

    return "\n".join(comment_lines)


def update_jira_failure(
    ticket_id: str, error_message: str, correlation_id: str = None
) -> bool:
    """
    Update JIRA Ticket with Failure Message

    Updates the JIRA ticket with repository creation failure details.
    This function is best-effort and logs warnings if it fails.

    Args:
        ticket_id: JIRA ticket ID (e.g., 'ENG-12345')
        error_message: Error message describing the failure
        correlation_id: Correlation ID for tracing

    Returns:
        bool: True if update succeeded, False otherwise
    """
    with log_execution_time(
        "update_jira_failure",
        correlation_id=correlation_id,
        jira_ticket_id=ticket_id,
    ):
        try:
            client = JiraClient()
            settings = get_settings()

            # Build failure comment
            comment_text = _build_failure_comment(error_message)

            # Add comment to JIRA ticket
            api_start_time = time.time()
            client.client.add_comment(ticket_id, comment_text)
            api_duration = (time.time() - api_start_time) * 1000

            # Emit latency metric for JIRA add_comment (failure)
            emit_latency_metric(
                'JiraAPI',
                api_duration,
                dimensions={'Operation': 'add_comment_failure'}
            )

            # Add labels
            try:
                api_start_time = time.time()
                issue = client.client.issue(ticket_id)
                current_labels = issue.fields.labels or []
                new_labels = list(
                    set(current_labels + ["repository-creation-failed", "automated"])
                )
                issue.update(fields={"labels": new_labels})
                api_duration = (time.time() - api_start_time) * 1000

                # Emit latency metric for JIRA update_labels (failure)
                emit_latency_metric(
                    'JiraAPI',
                    api_duration,
                    dimensions={'Operation': 'update_labels_failure'}
                )
            except Exception as label_error:
                log_and_monitor(
                    "jira_label_update_warning",
                    level="WARNING",
                    correlation_id=correlation_id,
                    jira_ticket_id=ticket_id,
                    error=str(label_error),
                )

            # Auto-transition to failure status if enabled
            if settings.auto_transition_on_failure:
                try:
                    # Get available transitions for this ticket
                    api_start_time = time.time()
                    transitions = client.client.transitions(ticket_id)
                    api_duration = (time.time() - api_start_time) * 1000

                    # Emit latency metric for JIRA get_transitions (failure)
                    emit_latency_metric(
                        'JiraAPI',
                        api_duration,
                        dimensions={'Operation': 'get_transitions_failure'}
                    )

                    # Find the target transition
                    target_transition = None
                    for t in transitions:
                        if t['name'].lower() == settings.failure_transition_name.lower():
                            target_transition = t['id']
                            break

                    if target_transition:
                        # Prepare transition fields (some workflows require resolution)
                        transition_fields = {}
                        if settings.failure_resolution:
                            transition_fields['resolution'] = {
                                'name': settings.failure_resolution
                            }

                        # Execute the transition
                        api_start_time = time.time()
                        client.client.transition_issue(
                            ticket_id,
                            target_transition,
                            fields=transition_fields if transition_fields else None
                        )
                        api_duration = (time.time() - api_start_time) * 1000

                        # Emit latency metric for JIRA transition_issue (failure)
                        emit_latency_metric(
                            'JiraAPI',
                            api_duration,
                            dimensions={'Operation': 'transition_issue_failure'}
                        )

                        log_and_monitor(
                            "ticket_transitioned_to_manual_review",
                            level="INFO",
                            correlation_id=correlation_id,
                            ticket_id=ticket_id,
                            new_status=settings.failure_transition_name
                        )
                    else:
                        log_and_monitor(
                            "failure_transition_not_found",
                            level="WARNING",
                            correlation_id=correlation_id,
                            ticket_id=ticket_id,
                            target_status=settings.failure_transition_name,
                            available_transitions=[t['name'] for t in transitions]
                        )
                except Exception as transition_error:
                    # Best-effort: log warning but don't fail the overall process
                    log_and_monitor(
                        "ticket_transition_on_failure_failed",
                        level="WARNING",
                        correlation_id=correlation_id,
                        ticket_id=ticket_id,
                        error=str(transition_error),
                        error_type=type(transition_error).__name__
                    )

            log_and_monitor(
                "jira_failure_update_success",
                level="INFO",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
            )

            return True

        except Exception as e:
            # Best effort - log warning but don't raise
            log_and_monitor(
                "jira_failure_update_failed",
                level="WARNING",
                correlation_id=correlation_id,
                jira_ticket_id=ticket_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


def _build_failure_comment(error_message: str) -> str:
    """
    Build formatted failure comment for JIRA.

    Args:
        error_message: Error message describing the failure

    Returns:
        str: Formatted comment text in JIRA markup
    """
    comment_lines = [
        "❌ *Repository Creation Failed*",
        "",
        "*Error Details:*",
        f"{{panel:title=Error Message|borderStyle=solid|borderColor=#ff0000|titleBGColor=#ff0000|bgColor=#ffcccc}}",
        error_message,
        "{{panel}}",
        "",
        "*Troubleshooting Steps:*",
        "# Verify all required fields are filled correctly",
        "# Check the repository name follows kebab-case format",
        "# Ensure the GitHub organization exists and you have access",
        "# Contact the Platform Team if the issue persists",
        "",
        "*Need Help?*",
        "Contact: hiya.modi.here@gmail.com",
        "",
        "---",
        "_This message was generated automatically by the GitHub Auto-Provisioning System._",
    ]

    return "\n".join(comment_lines)
