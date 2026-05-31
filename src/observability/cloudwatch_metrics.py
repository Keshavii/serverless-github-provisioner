"""
CloudWatch Metrics Integration

Provides AWS CloudWatch custom metrics emission for production monitoring, alerting,
and dashboards. Implements lazy boto3 client initialization, graceful degradation for
local development environments, and structured metric data formatting compliant with
CloudWatch PutMetricData API specifications.
"""

import os
import time
from typing import Dict, Optional

import structlog

from ..config import get_settings


_cloudwatch_client = None


def _get_cloudwatch_client():
    """
    Initialize and cache CloudWatch client on first use.

    Implements lazy initialization pattern to defer boto3 import and client creation
    until first metric emission. Optimizes Lambda cold start performance and enables
    local development without AWS credentials.

    Returns:
        Initialized boto3 CloudWatch client, or None if unavailable

    Initialization Sequence:
        First call: Imports boto3, creates cloudwatch client, caches globally
        Subsequent calls: Returns cached client immediately
        Error scenario: Logs warning via structlog, returns None for graceful degradation

    Error Handling:
        Sets cached value to False on error to prevent repeated import attempts.
        Allows application to continue without metrics in development environments.
    """
    global _cloudwatch_client
    if _cloudwatch_client is None:
        try:
            import boto3
            _cloudwatch_client = boto3.client('cloudwatch')
        except Exception as e:
            logger = structlog.get_logger()
            logger.warning("cloudwatch_client_unavailable", error=str(e))
            _cloudwatch_client = False
    return _cloudwatch_client if _cloudwatch_client is not False else None


def emit_metric(
    metric_name: str,
    value: float = 1.0,
    unit: str = 'Count',
    dimensions: Optional[Dict[str, str]] = None,
    namespace: Optional[str] = None
) -> None:
    """
    Send custom metric to AWS CloudWatch for monitoring and alerting.

    Publishes metric data point to CloudWatch with configurable namespace, dimensions,
    and unit type. Implements graceful error handling to prevent metric emission failures
    from impacting application reliability.

    Args:
        metric_name: Metric identifier string (e.g., 'RepositoryCreated', 'GitHubAPIError')
        value: Numeric metric value (default: 1.0 for simple counters)
        unit: CloudWatch standard unit - Count, Milliseconds, Seconds, Percent, Bytes, etc.
        dimensions: Key-value pairs for metric filtering in CloudWatch dashboards
        namespace: CloudWatch namespace (default: CLOUDWATCH_NAMESPACE env or 'GitHubRepoAutomation')

    Metric Emission Logic:
        1. Check if metrics enabled in configuration (skip if disabled)
        2. Obtain CloudWatch client via lazy initialization (skip if unavailable)
        3. Resolve namespace from parameter, environment, or default
        4. Build metric data structure with name, value, unit, timestamp
        5. Append dimensions if provided (formatted as Name/Value pairs)
        6. Call CloudWatch PutMetricData API
        7. Log warning on failure, do not raise exception

    Usage Examples:
        Simple event counter:
            emit_metric('RepositoryCreated')

        Categorized counter:
            emit_metric('RepositoryCreated',
                       dimensions={'Org': 'hiyamodi-org', 'Type': 'Private'})

        Latency measurement:
            emit_metric('RepoCreationDuration',
                       value=1234.5,
                       unit='Milliseconds',
                       dimensions={'Operation': 'create_repo', 'Result': 'success'})
    """
    settings = get_settings()

    if not settings.enable_metrics:
        return

    client = _get_cloudwatch_client()
    if client is None:
        return

    if namespace is None:
        namespace = os.environ.get('CLOUDWATCH_NAMESPACE', 'GitHubRepoAutomation')

    metric_data = {
        'MetricName': metric_name,
        'Value': value,
        'Unit': unit,
        'Timestamp': time.time()
    }

    if dimensions:
        metric_data['Dimensions'] = [
            {'Name': k, 'Value': str(v)} for k, v in dimensions.items()
        ]

    try:
        client.put_metric_data(
            Namespace=namespace,
            MetricData=[metric_data]
        )
    except Exception as e:
        logger = structlog.get_logger()
        logger.warning(
            "failed_to_emit_metric",
            metric_name=metric_name,
            error=str(e)
        )


def emit_latency_metric(
    operation_name: str,
    duration_ms: float,
    dimensions: Optional[Dict[str, str]] = None
) -> None:
    """
    Emit operation latency metric to CloudWatch.

    Convenience wrapper around emit_metric for tracking API and service operation
    response times. Automatically appends 'Latency' suffix to metric name and sets
    Milliseconds unit for consistent latency metric naming.

    Args:
        operation_name: Service or API identifier (e.g., 'GitHubAPI', 'JiraAPI', 'SecretsManager')
        duration_ms: Operation duration in milliseconds (typically from time.time() delta * 1000)
        dimensions: Optional categorization fields (Operation, Org, Result, StatusCode, etc.)

    Metric Naming Convention:
        Appends 'Latency' to operation_name: GitHubAPI → GitHubAPILatency
        Always uses Milliseconds as unit for consistency
        Inherits namespace and emission logic from emit_metric

    Usage Examples:
        GitHub API request timing:
            start = time.time()
            response = github_client.create_repo(...)
            emit_latency_metric('GitHubAPI', (time.time() - start) * 1000,
                              dimensions={'Operation': 'create_repo', 'StatusCode': '201'})

        JIRA API request timing:
            emit_latency_metric('JiraAPI', 156.8,
                              dimensions={'Operation': 'transition_issue', 'Result': 'success'})

        Secrets Manager fetch:
            emit_latency_metric('SecretsManager', 89.3,
                              dimensions={'Operation': 'get_secret'})
    """
    emit_metric(
        metric_name=f"{operation_name}Latency",
        value=duration_ms,
        unit='Milliseconds',
        dimensions=dimensions
    )
