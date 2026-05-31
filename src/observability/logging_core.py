"""
Core Logging Functionality

Provides centralized structured logging with JSON formatting, correlation ID tracking,
and automatic sensitive data masking. Integrates with metrics collection for
comprehensive application observability.

This module serves as the primary logging interface across all application components,
ensuring consistent log formatting and context propagation throughout the AWS Lambda
execution environment.
"""

import json
import logging
import sys
from typing import Any, Dict, Optional

import structlog

from ..config import get_settings


_logging_setup_done = False


def setup_logging() -> None:
    """
    Configure structured logging with JSON or console output.

    Initializes the structlog library with processors for production-grade logging.
    Configures standard library logging integration to ensure third-party libraries
    emit compatible log messages.

    Processing Pipeline:
        - Log level filtering by configured threshold
        - Logger name and level annotation for context
        - ISO 8601 timestamp formatting for consistency
        - Stack trace and exception information rendering
        - Unicode character handling for international support
        - JSON or console rendering based on configuration

    Configuration Source:
        Settings loaded from environment variables via get_settings()
        - log_format: 'json' for production, 'console' for development
        - log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """
    settings = get_settings()

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )


def log_and_monitor(
    event: str,
    level: str = "INFO",
    correlation_id: Optional[str] = None,
    jira_ticket_id: Optional[str] = None,
    repo_name: Optional[str] = None,
    function_name: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error: Optional[str] = None,
    error_type: Optional[str] = None,
    **kwargs,
) -> None:
    """
    Log structured event with context and automatic metrics emission.

    Primary logging interface for all application modules. Generates JSON-formatted
    log entries with automatic correlation tracking, sensitive data masking, and
    Lambda CloudWatch compatibility. Conditionally emits metrics when enabled.

    Args:
        event: Descriptive event name or message (e.g., 'repository_created')
        level: Log severity level - DEBUG, INFO, WARNING, ERROR, or CRITICAL
        correlation_id: Request tracing identifier for distributed systems
        jira_ticket_id: Associated JIRA ticket key for workflow tracking
        repo_name: GitHub repository name for context
        function_name: Executing function name for performance tracking
        duration_ms: Operation duration in milliseconds for latency monitoring
        error: Error message text for failure scenarios
        error_type: Exception class name or error category classification
        **kwargs: Additional context fields appended to log entry

    Logging Behavior:
        1. Initializes logging on first use (lazy initialization)
        2. Builds context dictionary with all provided fields
        3. Removes None values to reduce log verbosity
        4. Masks sensitive data (tokens, passwords, credentials)
        5. Emits to structlog with configured processors
        6. Prints JSON to stdout for Lambda CloudWatch ingestion
        7. Flushes stdout to ensure immediate log availability
        8. Triggers metrics collection if enable_metrics=True

    Example:
        log_and_monitor(
            'repository_created',
            level='INFO',
            correlation_id='abc-123',
            jira_ticket_id='PROJ-456',
            repo_name='example-repo',
            duration_ms=234.5
        )
    """
    print(f"🔍 log_and_monitor called: event={event}, level={level}")

    _ensure_logging_setup()
    logger = structlog.get_logger()

    context = {
        "event": event,
        "correlation_id": correlation_id,
        "jira_ticket_id": jira_ticket_id,
        "repo_name": repo_name,
        "function_name": function_name,
        "duration_ms": duration_ms,
        "error": error,
        "error_type": error_type,
        "environment": get_settings().environment,
    }

    context.update(kwargs)
    context = {k: v for k, v in context.items() if v is not None}
    context = _mask_sensitive_data(context)

    context_without_event = {k: v for k, v in context.items() if k != "event"}

    log_method = getattr(logger, level.lower(), logger.info)
    log_method(event, **context_without_event)

    print(json.dumps({
        "level": level,
        "event": event,
        **context_without_event
    }))
    sys.stdout.flush()

    if get_settings().enable_metrics:
        from .metrics_collector import emit_metrics_internal
        emit_metrics_internal(event, context)


def _mask_sensitive_data(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive credential data in log context.

    Scans log context for fields containing sensitive information and obscures
    their values to prevent credential leakage in logs. Preserves partial values
    for debugging while protecting security.

    Args:
        context: Log context dictionary with field names and values

    Returns:
        New dictionary with sensitive values masked while preserving structure

    Masking Strategy:
        - Detects sensitive fields by keyword matching (case-insensitive)
        - Preserves first 4 characters of string values for debugging
        - Replaces remainder with asterisks matching original length
        - Short values (<4 chars) fully masked as '***MASKED***'

    Protected Keywords:
        token, password, secret, api_key, credential, authorization
    """
    sensitive_keys = [
        "token",
        "password",
        "secret",
        "api_key",
        "credential",
        "authorization",
    ]

    masked_context = context.copy()

    for key, value in masked_context.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            if isinstance(value, str) and len(value) > 4:
                masked_context[key] = value[:4] + "*" * (len(value) - 4)
            else:
                masked_context[key] = "***MASKED***"

    return masked_context


def _ensure_logging_setup():
    """
    Initialize logging configuration on first use.

    Implements lazy initialization pattern to defer logging setup until the first
    log_and_monitor call. Enables test environments to mock configuration settings
    before logging processors are configured.

    Thread Safety:
        Uses module-level flag to ensure setup runs exactly once per process
    """
    global _logging_setup_done
    if not _logging_setup_done:
        setup_logging()
        _logging_setup_done = True
