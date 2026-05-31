"""
In-Memory Metrics Collection

Provides process-local metrics storage for testing, debugging, and development
environments. Production deployments emit metrics to CloudWatch via the
cloudwatch_metrics module while this collector maintains counters and histograms
in process memory for synchronous inspection.
"""

from typing import Any, Dict


_metrics: Dict[str, Any] = {
    "counters": {},
    "histograms": {},
}


def emit_metrics_internal(event: str, context: Dict[str, Any]) -> None:
    """
    Update in-memory metrics based on logged events.

    Internal callback invoked by log_and_monitor when metrics collection is enabled.
    Analyzes event names and context fields to increment counters and record duration
    histograms for local metrics tracking.

    Args:
        event: Event name from log_and_monitor call
        context: Log context dictionary with metadata fields

    Metrics Tracked:
        Counters (cumulative totals):
            repository_creation_success - Successful repository creations
            repository_creation_failure - Failed creation attempts
            validation_failure - Input validation errors
            repository_already_exists - Duplicate creation requests

        Histograms (value distributions):
            processing_duration_ms - Overall operation latencies
            {function_name}_duration_ms - Per-function execution times

    Integration:
        Called automatically by logging_core.log_and_monitor when
        enable_metrics=True in configuration. Production environments
        also emit to CloudWatch via cloudwatch_metrics module.
    """
    if "success" in event.lower():
        _increment_counter("repository_creation_success")
    elif "failed" in event.lower() or "error" in event.lower():
        _increment_counter("repository_creation_failure")
    elif "validation_failed" in event:
        _increment_counter("validation_failure")
    elif "repository_already_exists" in event:
        _increment_counter("repository_already_exists")

    if context.get("duration_ms") is not None:
        _record_histogram("processing_duration_ms", context["duration_ms"])

    if context.get("function_name"):
        function_duration_key = f"{context['function_name']}_duration_ms"
        if context.get("duration_ms") is not None:
            _record_histogram(function_duration_key, context["duration_ms"])


def _increment_counter(name: str, value: int = 1) -> None:
    """
    Increment counter metric by specified amount.

    Creates counter if it does not exist, otherwise adds to existing value.

    Args:
        name: Counter metric identifier
        value: Increment amount (default: 1)
    """
    if name not in _metrics["counters"]:
        _metrics["counters"][name] = 0
    _metrics["counters"][name] += value


def _record_histogram(name: str, value: float) -> None:
    """
    Append value to histogram for distribution analysis.

    Maintains list of observed values for statistical aggregation. Supports
    calculation of min, max, average, and percentiles (p50, p99) in test analysis.

    Args:
        name: Histogram metric identifier
        value: Observed numeric measurement
    """
    if name not in _metrics["histograms"]:
        _metrics["histograms"][name] = []
    _metrics["histograms"][name].append(value)


def get_metrics() -> Dict[str, Any]:
    """
    Retrieve current metrics snapshot for inspection.

    Returns deep copy of metrics dictionary to prevent external modification
    of live metrics state. Primarily used in testing and development environments.

    Returns:
        Dictionary with two keys:
            counters: Mapping of counter names to cumulative integer values
            histograms: Mapping of histogram names to lists of observed values

    Usage:
        metrics = get_metrics()
        success_count = metrics['counters']['repository_creation_success']
        durations = metrics['histograms']['processing_duration_ms']
        avg_duration = sum(durations) / len(durations)
    """
    return _metrics.copy()


def reset_metrics() -> None:
    """
    Clear all metrics to initial empty state.

    Resets counters to zero and empties histogram value lists. Essential for
    test isolation to prevent metrics contamination between test cases.

    Warning:
        Modifies global module state. Only use in test environments or during
        explicit application reinitialization. Do not call in production code.
    """
    global _metrics
    _metrics = {"counters": {}, "histograms": {}}
