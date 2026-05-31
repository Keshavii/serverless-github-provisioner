"""
Configuration management for the GitHub repository creation system.
Handles environment variables, secrets, and settings validation.
"""


from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from .shared.exceptions import ConfigurationError


class Settings(BaseSettings):
    """
    Application settings with validation.

    Manages all configuration parameters for the GitHub repository creation system.
    Settings are loaded from environment variables with defaults for local development.
    All validators enforce format and value constraints to prevent configuration errors.

    Configuration Categories:
        - GitHub: Authentication via GitHub App 
        - JIRA: API credentials and custom field mappings
        - Logging: Log level, format, and metrics emission
        - API Timeouts: Request timeout values for external services
        - Retry Logic: Backoff strategy for transient failures
        - Ticket Transitions: Automatic JIRA status updates on success/failure
        - AWS: SQS queue URL and SNS topic ARN for event processing
    """

    github_token: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token (deprecated, not used). All environments use GitHub App authentication."
    )

    github_app_id: Optional[str] = Field(
        None, description="GitHub App ID for App-based authentication (required for all environments including local testing)"
    )
    github_app_installation_id: Optional[str] = Field(
        None, description="GitHub App Installation ID for organization-level access (required for all environments including local testing)"
    )
    github_app_private_key: Optional[str] = Field(
        None, description="GitHub App Private Key in PEM format for JWT generation (required for all environments including local testing)"
    )

    jira_url: str = Field(
        default="https://test.atlassian.net",
        description="JIRA instance base URL (must use HTTPS)"
    )
    jira_email: str = Field(
        default="hiya.modi.here@gmail.com",
        description="JIRA user email for API authentication"
    )
    jira_api_token: str = Field(
        default="test_jira_token",
        description="JIRA API token for authentication"
    )

    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    log_format: str = Field(default="json", description="Log output format: json (structured) or text (human-readable)")
    enable_metrics: bool = Field(default=True, description="Enable CloudWatch metrics emission for monitoring")

    environment: str = Field(default="development", description="Deployment environment name (development, staging, production)")

    github_api_timeout: int = Field(default=30, description="GitHub API request timeout in seconds")
    jira_api_timeout: int = Field(default=30, description="JIRA API request timeout in seconds")

    max_retries: int = Field(
        default=3, description="Maximum retry attempts for transient API failures"
    )
    retry_backoff_factor: float = Field(
        default=2.0, description="Exponential backoff multiplier between retry attempts"
    )

    auto_transition_on_success: bool = Field(
        default=True,
        description="Enable automatic JIRA ticket transition to Done status upon successful repository creation"
    )
    success_transition_name: str = Field(
        default="Done",
        description="Target JIRA status name for successfully completed tickets"
    )
    success_resolution: Optional[str] = Field(
        default="Done",
        description="Resolution value to set on successful tickets (if required by JIRA workflow schema)"
    )

    auto_transition_on_failure: bool = Field(
        default=False,
        description="Enable automatic JIRA ticket transition to Manual Review on repository creation failures (Lambda2 handler)"
    )
    failure_transition_name: str = Field(
        default="Manual Review",
        description="Target JIRA status name for failed repository creation attempts"
    )
    failure_resolution: Optional[str] = Field(
        default="Unresolved",
        description="Resolution value for failed tickets (if required by JIRA workflow schema)"
    )

    auto_transition_on_webhook_failure: bool = Field(
        default=False,
        description="Enable automatic JIRA ticket transition to Manual Review on webhook or validation failures (Lambda1 handler)"
    )
    webhook_failure_transition_name: str = Field(
        default="Manual Review",
        description="Target JIRA status name for webhook validation failures"
    )
    webhook_failure_resolution: Optional[str] = Field(
        default=None,
        description="Resolution value for webhook failures (if required by JIRA workflow schema)"
    )

    jira_field_repo_name: str = Field(
        default="customfield_27191",
        description="JIRA custom field ID for repository name input. Instance-specific, update if your JIRA uses different field IDs."
    )
    jira_field_github_org: str = Field(
        default="customfield_27192",
        description="JIRA custom field ID for GitHub organization selection. Instance-specific, update if your JIRA uses different field IDs."
    )
    jira_field_repo_type: str = Field(
        default="customfield_27193",
        description="JIRA custom field ID for repository visibility type (Private/Internal). Instance-specific, update if your JIRA uses different field IDs."
    )
    jira_field_code_type: str = Field(
        default="customfield_27194",
        description="JIRA custom field ID for primary code language (Java/Python/etc). Instance-specific, update if your JIRA uses different field IDs."
    )
    jira_field_vp_name: str = Field(
        default="customfield_27195",
        description="JIRA custom field ID for VP name approval. Instance-specific, update if your JIRA uses different field IDs."
    )
    jira_field_director: str = Field(
        default="customfield_27196",
        description="JIRA custom field ID for director name approval. Instance-specific, update if your JIRA uses different field IDs."
    )
    jira_field_em_name: str = Field(
        default="customfield_27197",
        description="JIRA custom field ID for engineering manager name. Instance-specific, update if your JIRA uses different field IDs."
    )
    jira_field_product_line: str = Field(
        default="customfield_14984",
        description="JIRA custom field ID for product line categorization. Instance-specific, update if your JIRA uses different field IDs."
    )

    use_custom_fields: bool = Field(
        default=True,
        description="Enable extraction from JIRA custom fields. If False, falls back to parsing JSON from ticket description."
    )

    sqs_queue_url: Optional[str] = Field(
        None,
        description="AWS SQS Queue URL for receiving JIRA webhook messages. Required for Lambda execution."
    )
    sns_alert_topic_arn: Optional[str] = Field(
        None,
        description="AWS SNS Topic ARN for publishing Dead Letter Queue alerts. Required for failure notifications."
    )

    @field_validator("jira_url")
    @classmethod
    def validate_jira_url(cls, v):
        """
        Validate JIRA URL format.

        Enforces HTTPS protocol for secure API communication and removes trailing
        slashes to ensure consistent URL formatting across the application.

        Args:
            v: JIRA URL to validate

        Returns:
            str: Validated and normalized URL without trailing slash

        Raises:
            ConfigurationError: If URL is missing or doesn't use HTTPS
        """
        if not v:
            raise ConfigurationError("JIRA_URL is required", {"field": "jira_url"})
        if not v.startswith("https://"):
            raise ConfigurationError(
                "JIRA URL must start with 'https://'", {"field": "jira_url"}
            )
        return v.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """
        Validate log level.

        Enforces that log level is one of Python's standard logging levels.
        Automatically normalizes to uppercase for consistency.

        Args:
            v: Log level string to validate

        Returns:
            str: Validated and normalized log level in uppercase

        Raises:
            ConfigurationError: If log level is not a valid Python logging level
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ConfigurationError(
                f"Invalid log level. Must be one of: {', '.join(valid_levels)}",
                {"field": "log_level", "valid_values": valid_levels},
            )
        return v_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v):
        """
        Validate log format.

        Enforces supported log output formats. JSON format enables structured logging
        for CloudWatch Logs Insights queries, while text format provides human-readable
        output for local development.

        Args:
            v: Log format string to validate

        Returns:
            str: Validated and normalized log format in lowercase

        Raises:
            ConfigurationError: If format is not 'json' or 'text'
        """
        valid_formats = ["json", "text"]
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ConfigurationError(
                f"Invalid log format. Must be one of: {', '.join(valid_formats)}",
                {"field": "log_format", "valid_values": valid_formats},
            )
        return v_lower

    class Config:
        """
        Pydantic model configuration.

        Configures environment variable loading behavior. Loads from .env file in local
        development but gracefully handles missing .env in Lambda environments where
        configuration comes from environment variables or AWS Systems Manager.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_ignore_empty = True


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create singleton settings instance.

    Lazy-loads configuration on first access and caches for subsequent calls.
    Thread-safe for Lambda execution context reuse across invocations.

    Returns:
        Settings: Singleton settings instance with validated configuration

    Raises:
        ConfigurationError: If configuration loading or validation fails
    """
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration: {str(e)}", {"original_error": str(e)}
            )
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.

    Forces re-initialization of the settings singleton. Primarily useful for unit tests
    that need to modify environment variables between test cases.

    Returns:
        Settings: Fresh settings instance with reloaded configuration

    Raises:
        ConfigurationError: If configuration loading or validation fails
    """
    global _settings
    _settings = None
    return get_settings()
