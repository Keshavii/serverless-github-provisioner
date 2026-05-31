variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "source_code_root" {
  description = "Path to repository root (contains src/ folder)"
  type        = string
}

variable "lambda_layer_arn" {
  description = "ARN of the Lambda layer containing Python dependencies"
  type        = string
}

variable "dlq_arn" {
  description = "ARN of Dead Letter Queue"
  type        = string
}

variable "jira_secret_arn" {
  description = "ARN of JIRA credentials secret"
  type        = string
}

variable "jira_secret_name" {
  description = "Name of JIRA credentials secret"
  type        = string
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
}

variable "sns_alert_topic_arn" {
  description = "SNS topic ARN for alerting (optional)"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for direct notifications (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "dlq_batch_size" {
  description = "Number of DLQ messages to process in one batch"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

