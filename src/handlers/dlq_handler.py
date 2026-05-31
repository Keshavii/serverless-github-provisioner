"""
Dead Letter Queue (DLQ) Handler
Handles messages that failed after all retry attempts.
"""
import json
from typing import Any, Dict
from ..integrations.jira import update_jira_failure
from ..observability import log_and_monitor, generate_correlation_id, emit_metric
from ..integrations.messaging.notifications import notify_dlq_alert
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for DLQ messages.
    This function processes messages from the Dead Letter Queue after they've
    failed all retry attempts in the main queue.
    Args:
        event: SQS DLQ event containing failed messages
        context: Lambda context object
    Returns:
        Processing results
    """
    correlation_id = context.aws_request_id
    records_count = len(event.get('Records', []))
    log_and_monitor(
        "dlq_lambda_invocation",
        level="CRITICAL",
        correlation_id=correlation_id,
        records_count=records_count
    )
    # CRITICAL: Emit metric for DLQ messages received
    # This should trigger immediate alerts
    emit_metric(
        'DLQMessageReceived',
        value=records_count,
        dimensions={'Source': 'repo_creator_lambda'}
    )
    results = []
    # Process each DLQ message
    for record in event.get('Records', []):
        try:
            message_body = json.loads(record['body'])
            result = _process_dlq_message(message_body, correlation_id)
            results.append(result)
        except Exception as e:
            log_and_monitor(
                "dlq_message_processing_error",
                level="CRITICAL",
                correlation_id=correlation_id,
                error=str(e)
            )
    return {
        "statusCode": 200,
        "body": json.dumps({"processed": len(results)})
    }
def _process_dlq_message(message_data: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """
    Handler for Dead Letter Queue messages (failed after all retries).
    This function is triggered when a message has been retried 3 times
    and still failed. It performs final cleanup:
    1. Extract original message and error details
    2. Update JIRA ticket with final failure message
    3. Send alert to platform team
    4. Log for monitoring/alerting
    Args:
        message_data: Failed message data from DLQ
        correlation_id: Correlation ID for tracing
    Returns:
        Dict containing notification status
    """
    log_and_monitor(
        "dlq_handler_started",
        level="WARNING",
        correlation_id=correlation_id,
    )
    try:
        # Extract ticket information from message
        ticket_id = message_data.get("ticket_id")
        repo_name = message_data.get("repo_name")
        github_org = message_data.get("github_org")
        log_and_monitor(
            "processing_dlq_message",
            level="WARNING",
            correlation_id=correlation_id,
            ticket_id=ticket_id,
            repo_name=repo_name
        )
        # Build error summary
        error_summary = (
            "❌ *Repository Creation Failed After Multiple Retry Attempts*\n\n"
            f"*Repository:* {repo_name}\n"
            f"*Organization:* {github_org}\n"
            f"*Ticket:* {ticket_id}\n\n"
            "*Reason:* The repository creation process failed after 3 retry attempts. "
            "This message was moved to the Dead Letter Queue for manual review.\n\n"
        )
        # Add generic troubleshooting steps
        error_details = (
            "*Troubleshooting Steps:*\n"
            "# Check GitHub organization access and permissions\n"
            "# Verify all required fields in the JIRA ticket\n"
            "# Check GitHub and JIRA service status\n"
            "# Review CloudWatch logs for detailed error messages\n"
            "# Contact Platform Team if issue persists\n\n"
            "*Need Help?*\n"
            "• Slack: #platform-support\n"
        )
        # Update JIRA with final failure message
        try:
            update_jira_failure(
                ticket_id=ticket_id,
                error_message=error_summary + error_details,
                correlation_id=correlation_id,
            )
            log_and_monitor(
                "dlq_jira_update_success",
                level="INFO",
                correlation_id=correlation_id,
                ticket_id=ticket_id
            )

            # Send CRITICAL alert to platform team
            notify_dlq_alert(
                ticket_id=ticket_id,
                repo_name=message_data.get("repo_name", "unknown"),
                error_type=message_data.get("error_type", "unknown"),
                retry_count=message_data.get("retry_count", 3),
                correlation_id=correlation_id
            )

        except Exception as e:
            # Best effort - log if JIRA update fails
            log_and_monitor(
                "dlq_jira_update_failed",
                level="ERROR",
                correlation_id=correlation_id,
                ticket_id=ticket_id,
                error=str(e)
            )
        log_and_monitor(
            "dlq_handler_completed",
            level="WARNING",
            correlation_id=correlation_id,
            ticket_id=ticket_id
        )
        return {
            "status": "notified",
            "ticket_id": ticket_id,
            "correlation_id": correlation_id
        }
    except Exception as e:
        log_and_monitor(
            "dlq_handler_error",
            level="CRITICAL",
            correlation_id=correlation_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        # Don't raise - DLQ handler should not fail
        return {
            "status": "error",
            "error": str(e),
            "correlation_id": correlation_id,
        }