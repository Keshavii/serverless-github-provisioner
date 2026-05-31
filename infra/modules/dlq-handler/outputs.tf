output "lambda_arn" {
  description = "ARN of DLQ handler Lambda function"
  value       = aws_lambda_function.dlq_handler.arn
}

output "lambda_name" {
  description = "Name of DLQ handler Lambda function"
  value       = aws_lambda_function.dlq_handler.function_name
}

output "event_source_mapping_uuid" {
  description = "UUID of DLQ event source mapping"
  value       = aws_lambda_event_source_mapping.dlq_trigger.uuid
}

