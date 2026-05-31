"""
AWS Lambda Entry Point for GitHub Repository Creation

Processes SQS messages from JIRA Automation to create GitHub repositories.
Implements a thin adapter layer that delegates business logic to the workflow processor.

Responsibilities:
- Load credentials from AWS Secrets Manager on cold start
- Process SQS message batches
- Parse and validate incoming messages
- Orchestrate repository creation workflow
- Return partial batch failures for retry handling
"""

import json
from typing import Dict, Any

from ..observability import log_and_monitor
from ..integrations.aws.secrets_manager import load_secrets_to_env
from ..business.message_parser import parse_sqs_message
from ..business.workflow_processor import process_repository_request


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process SQS messages to create GitHub repositories.

    Orchestrates the repository creation workflow by loading credentials,
    parsing messages, and delegating to the workflow processor. Implements
    SQS partial batch failure response for reliable message processing.

    Args:
        event: SQS event containing Records array with JIRA automation messages
        context: AWS Lambda context with request metadata and runtime information

    Returns:
        Dictionary containing batchItemFailures array for SQS retry handling.
        Failed messages will be returned to the queue for reprocessing.

    Example:
        {
            "batchItemFailures": [
                {"itemIdentifier": "message-id-1"},
                {"itemIdentifier": "message-id-2"}
            ]
        }
    """
    print(f"🚀 Lambda Handler Started - Request ID: {context.aws_request_id}")
    print(f"📦 Event: {json.dumps(event)}")

    correlation_id = context.aws_request_id

    log_and_monitor(
        "lambda_invocation_started",
        level="INFO",
        correlation_id=correlation_id,
        function_name=context.function_name,
        records_count=len(event.get('Records', []))
    )

    load_secrets_to_env()

    batch_item_failures = []

    for record in event.get('Records', []):
        message_id = record['messageId']

        try:
            message_body = parse_sqs_message(record, correlation_id)
            ticket_id = message_body.get('ticket_id')

            log_and_monitor(
                "processing_sqs_message",
                level="INFO",
                correlation_id=correlation_id,
                message_id=message_id,
                ticket_id=ticket_id
            )

            success = process_repository_request(message_body, correlation_id)

            if success:
                log_and_monitor(
                    "sqs_message_processed_successfully",
                    level="INFO",
                    correlation_id=correlation_id,
                    message_id=message_id,
                    ticket_id=ticket_id
                )
            else:
                batch_item_failures.append({
                    "itemIdentifier": message_id
                })

        except Exception as e:
            log_and_monitor(
                "sqs_message_processing_error",
                level="ERROR",
                correlation_id=correlation_id,
                message_id=message_id,
                error=str(e),
                error_type=type(e).__name__
            )

            batch_item_failures.append({
                "itemIdentifier": message_id
            })

    log_and_monitor(
        "lambda_invocation_completed",
        level="INFO",
        correlation_id=correlation_id,
        total_records=len(event.get('Records', [])),
        failed_records=len(batch_item_failures)
    )

    return {
        "batchItemFailures": batch_item_failures
    }
