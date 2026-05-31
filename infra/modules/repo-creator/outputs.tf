output "lambda_arn" {
  description = "ARN of repo creator Lambda function"
  value       = aws_lambda_function.repo_creator.arn
}

output "lambda_name" {
  description = "Name of repo creator Lambda function"
  value       = aws_lambda_function.repo_creator.function_name
}

output "main_queue_url" {
  description = "URL of main SQS queue"
  value       = aws_sqs_queue.main.url
}

output "main_queue_arn" {
  description = "ARN of main SQS queue"
  value       = aws_sqs_queue.main.arn
}

output "dlq_url" {
  description = "URL of DLQ"
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "ARN of DLQ"
  value       = aws_sqs_queue.dlq.arn
}

output "event_source_mapping_uuid" {
  description = "UUID of SQS event source mapping"
  value       = aws_lambda_event_source_mapping.sqs_trigger.uuid
}

