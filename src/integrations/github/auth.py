"""
GitHub App Authentication and Client Management

Provides GitHub App authentication using JWT and Installation Access Tokens.
Manages GitHub API clients with automatic token handling and caching for
improved performance across multiple API requests.

Components:
    GitHubClientManager: Factory for creating and caching authenticated GitHub clients
    get_client_manager: Accessor for global singleton manager instance

Authentication Flow:
    1. Reads GitHub App credentials from environment variables
    2. Generates JWT token signed with private key
    3. Exchanges JWT for Installation Access Token
    4. Creates authenticated PyGithub client instance
"""

from typing import Optional
from github import Github, GithubIntegration

from ...config import get_settings
from ...shared import GitHubAPIError
from ...observability import log_and_monitor


class GitHubClientManager:
    """
    Factory and manager for authenticated GitHub API clients.

    Manages GitHub App authentication across multiple organizations using
    installation access tokens. Creates fresh clients for each request to
    ensure token validity and avoid stale credentials.

    The manager handles:
        - GitHub App integration initialization
        - Installation ID resolution per organization
        - Access token generation and management
        - Client instantiation with proper authentication

    Usage:
        manager = GitHubClientManager()
        client = manager.get_client("your-org-name")
        repo = client.get_repo("your-org-name/repo-name")
    """

    def __init__(self):
        """Initialize the client manager."""
        self._integration: Optional[GithubIntegration] = None

    def get_client(self, org: str) -> Github:
        """
        Get GitHub client for the specified organization.

        Creates a fresh client for each request.

        Args:
            org: GitHub organization name (REQUIRED)

        Returns:
            Github: Authenticated PyGithub client instance

        Raises:
            GitHubAPIError: If GitHub App is not installed in the organization,
                           or if authentication fails
        """

        client = self._create_client(org)

        log_and_monitor(
            "github_client_created",
            level="info",
            org=org
        )

        return client

    def _get_integration(self) -> GithubIntegration:
        """
        Get or create GithubIntegration instance.

        Supports both local development and AWS Lambda:
        - Local: Reads from .env file via config.py (GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY)
        - Lambda: Reads from environment variables (loaded by lambda_handler from AWS Secrets Manager)

        Returns:
            GithubIntegration: Authenticated integration instance

        Raises:
            GitHubAPIError: If credentials not configured
        """
        if self._integration:
            return self._integration

        settings = get_settings()
        app_id = settings.github_app_id
        private_key = settings.github_app_private_key

        if not app_id or not private_key:
            log_and_monitor(
                "github_app_credentials_missing",
                level="ERROR",
                message="GitHub App credentials not found in environment variables. "
                        "For local testing: Add to .env file. "
                        "For Lambda: Ensure AWS Secrets Manager is configured."
            )
            raise GitHubAPIError(
                message="GitHub App credentials not configured. "
                        "Required environment variables: GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY. "
                        "For local testing, add these to your .env file. "
                        "For AWS Lambda, ensure secrets are stored in AWS Secrets Manager.",
                status_code=None,
                response_body={"error": "missing_credentials", "missing": ["GITHUB_APP_ID", "GITHUB_APP_PRIVATE_KEY"]}
            )

        log_and_monitor(
            "github_app_credentials_loaded",
            level="DEBUG",
            app_id=app_id,
            private_key_length=len(private_key),
            message="GitHub App credentials successfully loaded from config"
        )

        self._integration = GithubIntegration(app_id, private_key)
        return self._integration

    def _get_installation_id(self, org: str) -> int:
        """
        Get installation ID for the specified organization.

        Args:
            org: GitHub organization name

        Returns:
            int: Installation ID for the organization

        Raises:
            GitHubAPIError: If app not installed in organization
        """

        try:
            integration = self._get_integration()

            log_and_monitor(
                "fetching_installation_id",
                level="INFO",
                org=org,
                message=f"Fetching installation ID for organization '{org}'"
            )

            installations = integration.get_installations()

            installed_orgs = []

            for installation in installations:
       
                org_login = installation.raw_data.get("account", {}).get("login")

                if org_login:
                    installed_orgs.append(org_login)

                if org_login and org_login.lower() == org.lower():
                    installation_id = installation.id

                    log_and_monitor(
                        "installation_id_found",
                        level="INFO",
                        org=org,
                        installation_id=installation_id,
                        account_login=org_login,
                        message=f"Found installation ID {installation_id} for org '{org}'"
                    )

                    return installation_id

            log_and_monitor(
                "installation_not_found",
                level="ERROR",
                org=org,
                message=f"GitHub App is not installed in organization '{org}'. "
                        f"Please install the app in this organization first."
            )

            raise GitHubAPIError(
                message=f"GitHub App is not installed in organization '{org}'. "
                        f"Install the app at: https://github.com/organizations/{org}/settings/installations",
                status_code=404,
                response_body={
                    "error": "app_not_installed",
                    "organization": org,
                    "message": "GitHub App must be installed in the organization"
                }
            )

        except GitHubAPIError:

            raise

        except Exception as e:
            log_and_monitor(
                "installation_id_lookup_error",
                level="ERROR",
                org=org,
                error=str(e),
                error_type=type(e).__name__,
                message=f"Failed to lookup installation ID for org '{org}'"
            )

            raise GitHubAPIError(
                message=f"Failed to lookup installation ID for organization '{org}': {str(e)}",
                status_code=getattr(e, 'status', None),
                response_body={"error": "installation_lookup_failed", "details": str(e)}
            )

    def _create_client(self, org: str) -> Github:
        """
        Create a new GitHub client for the specified organization.

        Args:
            org: GitHub organization name

        Returns:
            Github: New authenticated client instance

        Raises:
            GitHubAPIError: If authentication fails
        """
        try:

            integration = self._get_integration()

            installation_id = self._get_installation_id(org)

            auth = integration.get_access_token(installation_id)

            settings = get_settings()
            client = Github(auth.token, timeout=settings.github_api_timeout)

            return client

        except GitHubAPIError:
            raise
        except Exception as e:
            raise GitHubAPIError(
                message=f"Failed to create GitHub client for {org}: {str(e)}",
                status_code=None,
                response_body={"error": str(e), "org": org}
            )

_client_manager = GitHubClientManager()


def get_client_manager() -> GitHubClientManager:
    """
    Get the global GitHubClientManager instance.

    Returns:
        GitHubClientManager: The singleton manager instance
    """
    return _client_manager
