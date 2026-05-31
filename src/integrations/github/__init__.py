"""
GitHub Integration

Adapters for GitHub API operations including authentication, repository
creation, and repository management.
"""

from .auth import get_client_manager
from .repository_creator import create_github_repository
from .repository_operations import check_repository_exists

__all__ = [
    'get_client_manager',
    'create_github_repository',
    'check_repository_exists',
]
