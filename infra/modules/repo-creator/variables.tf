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

variable "github_secret_arn" {
  description = "ARN of GitHub credentials secret"
  type        = string
}

variable "github_secret_name" {
  description = "Name of GitHub credentials secret"
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

variable "jira_url" {
  description = "JIRA instance URL"
  type        = string
}

variable "github_app_id" {
  description = "GitHub App ID"
  type        = string
}

variable "github_app_private_key" {
  description = "GitHub App Private Key"
  type        = string
  sensitive   = true
}

variable "jira_email" {
  description = "JIRA user email"
  type        = string
}

variable "jira_token" {
  description = "JIRA API token"
  type        = string
  sensitive   = true
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "batch_size" {
  description = "Number of messages to process in one batch"
  type        = number
  default     = 5
}

variable "batching_window" {
  description = "Maximum batching window in seconds"
  type        = number
  default     = 0
}

variable "sqs_visibility_timeout" {
  description = "SQS visibility timeout in seconds"
  type        = number
  default     = 360
}

variable "sqs_message_retention" {
  description = "SQS message retention in seconds (4 days)"
  type        = number
  default     = 345600
}

variable "dlq_message_retention" {
  description = "DLQ message retention in seconds (14 days)"
  type        = number
  default     = 1209600
}

variable "sqs_max_receive_count" {
  description = "Max receive count before sending to DLQ"
  type        = number
  default     = 3
}

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
}

variable "environment" {
  description = "Environment name (test, staging, prod)"
  type        = string
}

# JIRA Transition Configuration - Success
variable "auto_transition_on_success" {
  description = "Auto-transition JIRA ticket on success"
  type        = string
  default     = "true"
}

variable "success_transition_name" {
  description = "JIRA transition name for success"
  type        = string
  default     = "Done"
}

variable "success_resolution" {
  description = "JIRA resolution for success"
  type        = string
  default     = "Done"
}

# JIRA Transition Configuration - Failure
variable "auto_transition_on_failure" {
  description = "Auto-transition JIRA ticket on failure"
  type        = string
  default     = "false"
}

variable "failure_transition_name" {
  description = "JIRA transition name for failure"
  type        = string
  default     = "Manual Review"
}

variable "failure_resolution" {
  description = "JIRA resolution for failure"
  type        = string
  default     = "Unresolved"
}

# Logging Configuration
variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
}

variable "log_format" {
  description = "Log format (json or text)"
  type        = string
  default     = "json"
}

variable "enable_metrics" {
  description = "Enable CloudWatch metrics"
  type        = string
  default     = "true"
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

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

