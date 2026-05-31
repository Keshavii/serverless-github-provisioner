"""
External Service Integrations

Adapters for external services including GitHub, JIRA, AWS, and messaging platforms.
"""

from . import github
from . import jira
from . import aws
from . import messaging

__all__ = [
    'github',
    'jira',
    'aws',
    'messaging',
]
