"""
Messaging Platform Integrations

Adapters for messaging and notification platforms including Slack.
Future: Email, SMS, Microsoft Teams, etc.
"""

from .notifications import (
    notify_success,
    notify_validation_error,
    notify_permission_error,
    notify_github_error,
    notify_jira_error,
)

__all__ = [
    'notify_success',
    'notify_validation_error',
    'notify_permission_error',
    'notify_github_error',
    'notify_jira_error',
]
