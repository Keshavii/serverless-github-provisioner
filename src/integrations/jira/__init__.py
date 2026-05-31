"""
JIRA Integration

Adapter for JIRA API operations including ticket updates and transitions.
"""

from .client import (
    update_jira_success,
    update_jira_failure,
    transition_ticket_status,
)

__all__ = [
    'update_jira_success',
    'update_jira_failure',
    'transition_ticket_status',
]
