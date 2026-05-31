"""
Error Handling and User Messaging

Provides centralized error categorization and actionable user messaging for GitHub
API errors and exceptions. Transforms technical errors into user-friendly JIRA
comments with specific remediation steps.
"""

from .exceptions import GitHubAPIError


def categorize_github_error(error: GitHubAPIError) -> str:
    """
    Categorize GitHub API error to determine appropriate handling strategy.

    Classifies errors into categories that inform retry logic and user notification
    requirements. Permission and transient errors may warrant automatic retry, while
    business rule violations require user intervention.

    Args:
        error: GitHubAPIError exception containing status code and response details

    Returns:
        Error category string indicating the error class:
            - "permission": Authentication or authorization failures (401, 403)
            - "transient": Temporary failures that may succeed on retry (408, 429, 5xx)
            - "business_rule": Validation failures or constraint violations (422)
    """
    status_code = error.status_code

    if status_code in [401, 403]:
        return "permission"

    if status_code in [408, 429, 500, 502, 503, 504]:
        return "transient"

    if status_code == 422 and "already exists" in str(error).lower():
        return "business_rule"

    return "business_rule"


def should_retry_error(error_category: str) -> bool:
    """
    Determine whether an error warrants automatic retry.

    Transient errors such as rate limiting, timeouts, and server errors are
    candidates for retry. Permission and business rule violations require
    user intervention and should not be retried automatically.

    Args:
        error_category: Error category from categorize_github_error()

    Returns:
        True if the error is transient and should be retried, False otherwise
    """
    return error_category == "transient"


def format_error_message_for_jira(error: GitHubAPIError, error_category: str) -> str:
    """
    Format GitHub API error as actionable JIRA comment with troubleshooting steps.

    Transforms technical GitHub API errors into user-friendly markdown messages
    with specific remediation guidance. Provides context-specific troubleshooting
    based on error type, status code, and error category.

    Args:
        error: GitHubAPIError exception containing status code and response details
        error_category: Error classification from categorize_github_error()
            (permission, transient, or business_rule)

    Returns:
        Markdown-formatted error message suitable for JIRA comment, including:
            - Error summary with HTTP status code
            - Root cause explanation
            - Specific remediation steps
            - Support contact information
    """
    status_code = error.status_code

    error_msg = "❌ *GitHub Repository Creation Failed*\n\n"
    error_msg += f"*Error Category:* {error_category.title()}\n"
    error_msg += f"*Status Code:* {status_code}\n\n"

    if status_code == 401:
        error_msg += "*Reason:* GitHub authentication failed. The token is invalid, expired, or revoked.\n\n"
        error_msg += "*Action Required:*\n"
        error_msg += "# Contact DevOps team to refresh the GitHub token\n"
        error_msg += "# Verify token is active at: https://github.com/settings/tokens\n"
        error_msg += "# Ensure token has not expired\n"
        error_msg += "# Update the Lambda environment variable after token refresh\n"

    elif status_code == 403:
        error_msg += "*Reason:* Permission denied. GitHub token lacks required permissions.\n\n"
        error_msg += "*Action Required:*\n"
        error_msg += "# Verify token has the following scopes:\n"
        error_msg += "  - `repo` (Full control of private repositories)\n"
        error_msg += "  - `admin:org` (Full control of orgs and teams)\n"
        error_msg += "# Contact GitHub organization admin to update permissions\n"
        error_msg += "# Regenerate token with correct scopes if needed\n"

    elif status_code == 404:
        error_msg += "*Reason:* GitHub organization or resource not found.\n\n"
        error_msg += "*Action Required:*\n"
        error_msg += "# Verify the organization name is correct\n"
        error_msg += "# Ensure the GitHub token has access to the organization\n"
        error_msg += "# Check if organization exists: https://github.com/[org-name]\n"

    elif status_code == 422:
        if "already exists" in str(error).lower():
            error_msg += "*Reason:* Repository with this name already exists.\n\n"
            error_msg += "*Action Required:*\n"
            error_msg += "# Check if repository already exists in the organization\n"
            error_msg += "# Use a different repository name if needed\n"
            error_msg += "# Or use the existing repository\n"
        else:
            error_msg += "*Reason:* Validation failed. Repository name or configuration is invalid.\n\n"
            error_msg += "*Action Required:*\n"
            error_msg += "# Verify repository name follows GitHub naming rules:\n"
            error_msg += "  - Only lowercase letters, numbers, hyphens, underscores\n"
            error_msg += "  - No spaces or special characters\n"
            error_msg += "# Check all required fields in the JIRA ticket\n"
    else:
        error_msg += f"*Reason:* {str(error)}\n\n"
        error_msg += "*Action Required:*\n"
        error_msg += "# Review the error details above\n"
        error_msg += "# Check GitHub service status: https://www.githubstatus.com/\n"
        error_msg += "# Contact Platform Team if issue persists\n"

    error_msg += "\n*Need Help?*\n"
    error_msg += "• Review CloudWatch logs for detailed error information\n"
    error_msg += "• Contact Platform Team: hiya.modi.here@gmail.com\n"
    error_msg += "• Slack: #platform-support\n"

    return error_msg
