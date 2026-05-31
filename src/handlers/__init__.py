"""
Lambda Handler Functions

Entry points for AWS Lambda functions that process repository creation
and dead letter queue events.
"""

from .github_handler import lambda_handler as github_lambda_handler
from .dlq_handler import lambda_handler as dlq_lambda_handler

__all__ = [
    'github_lambda_handler',
    'dlq_lambda_handler',
]
