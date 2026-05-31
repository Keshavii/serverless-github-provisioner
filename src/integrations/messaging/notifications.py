"""
Notification System for GitHub Automation
Handles Slack notifications for all error scenarios.
"""
import os
import requests
from typing import Dict, Any, Optional
from ...observability import log_and_monitor, emit_metric


def send_notification(
    notification_type: str,
    title: str,
    message: str,
    severity: str = "ERROR",
    metadata: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Send notifications via Slack webhook.

    Args:
        notification_type: Type (validation_error, github_error, webhook_error, dlq_alert, etc.)
        title: Notification title
        message: Notification message
        severity: WARNING, ERROR, CRITICAL (default: ERROR)
        metadata: Additional context data (ticket_id, repo_name, error_type, etc.)
        correlation_id: Correlation ID for tracing

    Returns:
        True if notification sent successfully
    """

    if os.environ.get('SLACK_WEBHOOK_URL'):
        return _send_slack_notification(
            notification_type, title, message, severity, metadata, correlation_id
        )

    log_and_monitor(
        "slack_webhook_not_configured",
        level="WARNING",
        correlation_id=correlation_id
    )
    return False


def _send_slack_notification(
    notification_type: str,
    title: str,
    message: str,
    severity: str,
    metadata: Optional[Dict[str, Any]],
    correlation_id: Optional[str]
) -> bool:
    """Send notification to Slack using Incoming Webhook."""
    try:
        webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        
        color_map = {
            'CRITICAL': '#FF0000',
            'ERROR': '#FF6B35',
            'WARNING': '#FFA500',
        }
        color = color_map.get(severity, '#808080')

        emoji_map = {
            'validation_error': '⚠️',
            'github_error': '❌',
            'webhook_error': '🔴',
            'dlq_alert': '🚨',
            'permission_error': '🔒',
            'jira_error': '📋'
        }
        emoji = emoji_map.get(notification_type, '📢')
        
        slack_payload = {
            'username': 'GitHub Automation Bot',
            'icon_emoji': ':robot_face:',
            'attachments': [{
                'color': color,
                'title': f"{emoji} {title}",
                'text': message,
                'footer': f"GitHub Repository Automation | ID: {correlation_id or 'N/A'}",
                'fields': _build_slack_fields(metadata) if metadata else []
            }]
        }
        
        response = requests.post(webhook_url, json=slack_payload, timeout=10)
        response.raise_for_status()
        
        log_and_monitor("slack_notification_sent", level="INFO", correlation_id=correlation_id)
        emit_metric('SlackNotificationSent', dimensions={'Type': notification_type})
        return True
        
    except Exception as e:
        log_and_monitor("slack_notification_failed", level="ERROR", correlation_id=correlation_id, error=str(e))
        emit_metric('SlackNotificationFailed')
        return False


def _build_slack_fields(metadata: Dict[str, Any]) -> list:
    """Build Slack attachment fields from metadata."""
    fields = []

    if metadata.get('ticket_id'):
        fields.append({'title': 'JIRA Ticket', 'value': metadata['ticket_id'], 'short': True})

    if metadata.get('repo_name'):
        fields.append({'title': 'Repository', 'value': metadata['repo_name'], 'short': True})

    if metadata.get('github_org'):
        fields.append({'title': 'Organization', 'value': metadata['github_org'], 'short': True})

    if metadata.get('error_type'):
        fields.append({'title': 'Error Type', 'value': metadata['error_type'], 'short': True})

    if metadata.get('repo_url'):
        fields.append({
            'title': 'Repository URL',
            'value': f"<{metadata['repo_url']}|View Repository>",
            'short': False
        })

    return fields


def notify_validation_error(
    ticket_id: str,
    repo_name: str,
    github_org: str,
    error_message: str,
    correlation_id: str
) -> bool:
    """Send notification for validation errors (user input errors)."""
    return send_notification(
        notification_type='validation_error',
        title=f'Validation Error: {repo_name}',
        message=f'Invalid input for repository `{repo_name}`:\n```{error_message}```',
        severity='WARNING',
        metadata={
            'ticket_id': ticket_id,
            'repo_name': repo_name,
            'github_org': github_org,
            'error_type': 'ValidationError'
        },
        correlation_id=correlation_id
    )


def notify_github_error(
    ticket_id: str,
    repo_name: str,
    github_org: str,
    error_message: str,
    error_category: str,
    correlation_id: str
) -> bool:
    """Send notification for GitHub API errors (permanent errors only)."""
    return send_notification(
        notification_type='github_error',
        title=f'GitHub Error: {repo_name}',
        message=f'GitHub API error for `{repo_name}`:\n```{error_message}```',
        severity='ERROR',
        metadata={
            'ticket_id': ticket_id,
            'repo_name': repo_name,
            'github_org': github_org,
            'error_type': f'GitHub-{error_category}'
        },
        correlation_id=correlation_id
    )


def notify_webhook_error(
    ticket_id: str,
    error_type: str,
    error_message: str,
    correlation_id: str
) -> bool:
    """Send notification for webhook validation/processing errors."""
    return send_notification(
        notification_type='webhook_error',
        title=f'Webhook Error: {error_type}',
        message=f'Webhook processing failed for ticket `{ticket_id}`:\n```{error_message}```',
        severity='ERROR',
        metadata={
            'ticket_id': ticket_id,
            'error_type': error_type
        },
        correlation_id=correlation_id
    )


def notify_dlq_alert(
    ticket_id: str,
    repo_name: str,
    github_org: str,
    error_summary: str,
    correlation_id: str
) -> bool:
    """Send critical alert for DLQ messages (failed after all retries)."""
    return send_notification(
        notification_type='dlq_alert',
        title='🚨 DLQ Alert: Repository Creation Failed After Retries',
        message=f'*CRITICAL:* Message moved to Dead Letter Queue\n\n{error_summary}',
        severity='CRITICAL',
        metadata={
            'ticket_id': ticket_id,
            'repo_name': repo_name,
            'github_org': github_org,
            'error_type': 'DLQ-MaxRetriesExceeded'
        },
        correlation_id=correlation_id
    )


def notify_permission_error(
    ticket_id: str,
    repo_name: str,
    github_org: str,
    error_message: str,
    correlation_id: str
) -> bool:
    """Send notification for GitHub permission/authentication errors."""
    return send_notification(
        notification_type='permission_error',
        title=f'🔒 Permission Error: {repo_name}',
        message=f'GitHub authentication/permission error:\n```{error_message}```\n\n*Action Required:* Check GitHub App permissions and credentials.',
        severity='CRITICAL',
        metadata={
            'ticket_id': ticket_id,
            'repo_name': repo_name,
            'github_org': github_org,
            'error_type': 'GitHub-Permission'
        },
        correlation_id=correlation_id
    )


def notify_jira_error(
    ticket_id: str,
    repo_name: str,
    error_message: str,
    correlation_id: str
) -> bool:
    """Send notification for permanent JIRA errors."""
    return send_notification(
        notification_type='jira_error',
        title=f'📋 JIRA Error: {ticket_id}',
        message=f'JIRA API error (permanent):\n```{error_message}```',
        severity='ERROR',
        metadata={
            'ticket_id': ticket_id,
            'repo_name': repo_name,
            'error_type': 'JIRA-Permanent'
        },
        correlation_id=correlation_id
    )
