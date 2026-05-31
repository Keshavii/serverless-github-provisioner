"""
Shared Utilities

Common utilities used across all application layers including exceptions
and error formatting.
"""

from .exceptions import (
    BaseAutomationError,
    ValidationError,
    GitHubAPIError,
    JiraAPIError,
    ConfigurationError,
    OrganizationNotFoundError,
    RepositoryAlreadyExistsError,
    InsufficientPermissionsError,
)
from .error_formatting import (
    categorize_github_error,
    should_retry_error,
    format_error_message_for_jira,
)

__all__ = [
    'BaseAutomationError',
    'ValidationError',
    'GitHubAPIError',
    'JiraAPIError',
    'ConfigurationError',
    'OrganizationNotFoundError',
    'RepositoryAlreadyExistsError',
    'InsufficientPermissionsError',
    'categorize_github_error',
    'should_retry_error',
    'format_error_message_for_jira',
]
