"""
AWS Secrets Manager Integration

Provides secure credential management by loading secrets from AWS Secrets Manager
into runtime environment variables. Handles both GitHub App authentication credentials
and JIRA API tokens required for repository automation workflows.
"""

import json
import os
import boto3

from ...observability import log_and_monitor


secretsmanager = boto3.client('secretsmanager')


def load_secrets_to_env():
    """
    Load application secrets from AWS Secrets Manager into environment variables.

    Populates runtime environment with credentials required for GitHub and JIRA
    API operations. Should be called once during Lambda cold start to ensure
    credentials are available throughout the execution context lifetime.

    Environment Variables Set:
        GITHUB_APP_ID: GitHub App identifier for authentication
        GITHUB_APP_PRIVATE_KEY: RSA private key for GitHub App JWT signing
        JIRA_URL: JIRA instance base URL
        JIRA_EMAIL: JIRA account email for API authentication
        JIRA_API_TOKEN: JIRA API token for authenticated requests

    Raises:
        Exception: If secrets cannot be retrieved from AWS Secrets Manager,
                  typically due to missing secrets, IAM permission issues,
                  or network connectivity problems
    """
    try:
        _load_github_secrets()
        _load_jira_secrets()
        
    except Exception as e:
        log_and_monitor(
            "secrets_loading_error",
            level="ERROR",
            error=str(e),
            error_type=type(e).__name__,
            message="Failed to load secrets from AWS Secrets Manager. "
                    "Ensure secrets are created: github-repo-automation/github and github-repo-automation/jira"
        )
        raise


def _load_github_secrets():
    """
    Load GitHub App credentials from AWS Secrets Manager.

    Retrieves GitHub App authentication credentials from the designated secret
    and populates environment variables for use by the GitHub client.

    Environment Variables Set:
        GITHUB_APP_ID: GitHub App identifier
        GITHUB_APP_PRIVATE_KEY: RSA private key in PEM format

    Secret Location:
        Secret Name: github-repo-automation/github
        Expected Format: {"GITHUB_APP_ID": "...", "GITHUB_APP_PRIVATE_KEY": "..."}
    """
    github_secret = secretsmanager.get_secret_value(
        SecretId='github-repo-automation/github'
    )
    github_data = json.loads(github_secret['SecretString'])

    os.environ['GITHUB_APP_ID'] = github_data['GITHUB_APP_ID']
    os.environ['GITHUB_APP_PRIVATE_KEY'] = github_data['GITHUB_APP_PRIVATE_KEY']
    
    log_and_monitor(
        "github_secrets_loaded",
        level="INFO",
        message="GitHub App credentials loaded from AWS Secrets Manager"
    )


def _load_jira_secrets():
    """
    Load JIRA API credentials from AWS Secrets Manager.

    Retrieves JIRA authentication credentials from the designated secret
    and populates environment variables for use by the JIRA client.

    Environment Variables Set:
        JIRA_URL: JIRA instance base URL (e.g., https://hiyamodi.atlassian.net)
        JIRA_EMAIL: JIRA account email address
        JIRA_API_TOKEN: JIRA API token for authentication

    Secret Location:
        Secret Name: github-repo-automation/jira
        Expected Format: {"JIRA_URL": "...", "JIRA_EMAIL": "...", "JIRA_API_TOKEN": "..."}
    """
    jira_secret = secretsmanager.get_secret_value(
        SecretId='github-repo-automation/jira'
    )
    jira_data = json.loads(jira_secret['SecretString'])
    
    os.environ['JIRA_URL'] = jira_data['JIRA_URL']
    os.environ['JIRA_EMAIL'] = jira_data['JIRA_EMAIL']
    os.environ['JIRA_API_TOKEN'] = jira_data['JIRA_API_TOKEN']

    log_and_monitor(
        "jira_secrets_loaded",
        level="INFO",
        message="JIRA credentials loaded from AWS Secrets Manager"
    )
