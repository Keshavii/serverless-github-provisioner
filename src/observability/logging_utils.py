"""
Logging Utilities

Provides utility functions for distributed request tracing and automatic performance
monitoring. Supports correlation ID generation for cross-service tracking and
context manager-based execution timing for Lambda function profiling.
"""

import time
import uuid
from contextlib import contextmanager
from typing import Optional

from .logging_core import log_and_monitor


def generate_correlation_id() -> str:
    """
    Generate unique correlation identifier for distributed request tracing.

    Creates UUID v4 identifier for tracking requests across service boundaries,
    Lambda invocations, and SQS message processing. Enables correlation of logs
    and metrics throughout asynchronous workflow execution.

    Returns:
        Hyphenated UUID v4 string (36 characters)

    Usage:
        correlation_id = generate_correlation_id()
        log_and_monitor('request_started', correlation_id=correlation_id)
    """
    return str(uuid.uuid4())


@contextmanager
def log_execution_time(
    function_name: str,
    correlation_id: Optional[str] = None,
    **context
):
    """
    Automatically measure and log function execution duration.

    Context manager that captures function entry and exit timestamps, calculating
    elapsed time in milliseconds. Emits structured logs for performance profiling
    and latency tracking in production Lambda environments.

    Args:
        function_name: Descriptive function or operation name for log events
        correlation_id: Request correlation ID for distributed tracing
        **context: Additional context fields (ticket_id, repo_name, etc.)

    Yields:
        Control to wrapped code block

    Logging Behavior:
        Entry: Logs '{function_name}_started' event with context
        Exit: Logs '{function_name}_completed' with duration_ms rounded to 2 decimals

    Example:
        with log_execution_time('validate_input',
                               correlation_id=corr_id,
                               ticket_id='PROJ-123'):
            validate_input_data(request)

        Generates logs:
            {"event": "validate_input_started", "correlation_id": "...", "ticket_id": "PROJ-123"}
            {"event": "validate_input_completed", "duration_ms": 12.34, ...}
    """
    start_time = time.time()

    log_and_monitor(
        f"{function_name}_started",
        level="INFO",
        correlation_id=correlation_id,
        function_name=function_name,
        **context,
    )

    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        log_and_monitor(
            f"{function_name}_completed",
            level="INFO",
            correlation_id=correlation_id,
            function_name=function_name,
            duration_ms=round(duration_ms, 2),
            **context,
        )
