"""
GitHub Repository Operations

Provides repository existence checks and organization validation to support
idempotent repository creation workflows. Ensures repositories are not
duplicated and validates organization access before creation attempts.
"""

import time
from typing import Dict, Optional, Tuple

from github import UnknownObjectException

from ...shared import BaseAutomationError, GitHubAPIError, OrganizationNotFoundError
from ...observability import log_and_monitor, log_execution_time, emit_latency_metric
from .auth import get_client_manager


def check_repository_exists(
    org: str,
    repo_name: str,
    correlation_id: Optional[str] = None
) -> Tuple[bool, Optional[Dict]]:
    """
    Check if a repository exists in the specified GitHub organization.

    Performs idempotency check by validating organization access and querying
    for repository existence. Returns repository metadata if found, enabling
    callers to avoid duplicate creation attempts.

    Workflow:
        1. Validate organization exists and is accessible
        2. Query for repository in organization
        3. Return existence flag and repository data if found

    Args:
        org: GitHub organization name (e.g., "hiyamodi-org")
        repo_name: Repository name to check (e.g., "my-service")
        correlation_id: Optional request identifier for distributed tracing

    Returns:
        Tuple[bool, Optional[Dict]]:
            - (True, repo_data) if repository exists
            - (False, None) if repository doesn't exist

        repo_data contains:
            - name: Repository name
            - full_name: Full repo name (org/repo)
            - html_url: Repository web URL
            - clone_url: HTTPS clone URL
            - ssh_url: SSH clone URL
            - id: Repository ID
            - visibility: Repository visibility (private, internal, or public)
            - description: Repository description
            - created_at: Creation timestamp (ISO format)
            - updated_at: Last update timestamp (ISO format)
            - owner: Organization name

    Raises:
        GitHubAPIError: If GitHub App is not installed in the organization,
                       or if GitHub API call fails (authentication, network, etc.)
        OrganizationNotFoundError: If the organization doesn't exist
        BaseAutomationError: If repo_name is not provided

    Note:
        Organization must be explicitly provided to prevent accidental checks
        in the wrong organization. NO DEFAULT FALLBACK for safety.
    """
    with log_execution_time(
        "check_repository_exists",
        correlation_id=correlation_id,
        repo_name=repo_name,
        github_org=org
    ):
    
        if not repo_name:
            raise BaseAutomationError(
                message="Repository name parameter is required for check_repository_exists()",
                details={"error": "missing_repo_name"}
            )

        try:
         
            client = get_client_manager().get_client(org)

            try:
    
                api_start_time = time.time()
                repo = client.get_repo(f"{org}/{repo_name}")
                api_duration = (time.time() - api_start_time) * 1000

                emit_latency_metric(
                    'GitHubAPI',
                    api_duration,
                    dimensions={'Operation': 'check_repo_exists', 'Org': org}
                )

                repo_data = {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "id": repo.id,
                    "visibility": repo.visibility,
                    "description": repo.description or "",
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    "owner": org
                }

                log_and_monitor(
                    "repository_exists",
                    level="INFO",
                    correlation_id=correlation_id,
                    repo_name=repo_name,
                    github_org=org,
                    repo_id=repo.id,
                    repo_url=repo.html_url,
                    message=f"Repository {org}/{repo_name} exists"
                )

                return (True, repo_data)

            except UnknownObjectException:

                log_and_monitor(
                    "repository_does_not_exist",
                    level="INFO",
                    correlation_id=correlation_id,
                    repo_name=repo_name,
                    github_org=org,
                    message=f"Repository {org}/{repo_name} does not exist"
                )

                return (False, None)

            except Exception as e:

                log_and_monitor(
                    "repository_check_error",
                    level="ERROR",
                    correlation_id=correlation_id,
                    repo_name=repo_name,
                    github_org=org,
                    error=str(e),
                    error_type=type(e).__name__
                )

                raise GitHubAPIError(
                    message=f"Failed to check if repository exists: {str(e)}",
                    status_code=getattr(e, 'status', None),
                    response_body={"error": str(e), "repo": f"{org}/{repo_name}"}
                )

        except GitHubAPIError:
   
            raise
        except Exception as e:
   
            log_and_monitor(
                "check_repository_exists_error",
                level="ERROR",
                correlation_id=correlation_id,
                repo_name=repo_name,
                github_org=org,
                error=str(e),
                error_type=type(e).__name__
            )

            raise GitHubAPIError(
                message=f"Failed to check repository existence: {str(e)}",
                status_code=None,
                response_body={"error": str(e)}
            )
