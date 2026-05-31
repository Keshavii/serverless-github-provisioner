# ============================================================================
# TEST ENVIRONMENT VARIABLES
# ============================================================================

# Project Configuration
variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "github-repo-automation"
}

variable "environment" {
  description = "Environment name (test, staging, prod)"
  type        = string
  default     = "test"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# GitHub App Configuration
# NOTE: The GitHub App must be installed on all organizations where you want to create repos
# The code automatically detects the installation ID for each organization at runtime
variable "github_app_id" {
  description = "GitHub App ID (from GitHub App settings)"
  type        = string
  sensitive   = true
}

variable "github_app_private_key" {
  description = "GitHub App Private Key (PEM format, can be base64 encoded)"
  type        = string
  sensitive   = true
}

# JIRA Configuration (Optional for testing)
variable "jira_url" {
  description = "JIRA URL"
  type        = string
  default     = "https://placeholder.atlassian.net"
}

variable "jira_email" {
  description = "JIRA email for API authentication"
  type        = string
  default     = "placeholder@example.com"
}

variable "jira_token" {
  description = "JIRA API token"
  type        = string
  sensitive   = true
  default     = "placeholder-token"
}

# Lambda Configuration
variable "lambda_runtime" {
  description = "Lambda runtime version (e.g., 3.9, 3.11)"
  type        = string
  default     = "3.9"
}

variable "lambda_timeout" {
  description = "Lambda function timeout for repo creator (seconds)"
  type        = number
  default     = 300
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

# SQS Configuration
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
  description = "SQS visibility timeout (should be >= 6x lambda_timeout)"
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

# Secrets Configuration
variable "recovery_window_in_days" {
  description = "Number of days to retain secret after deletion"
  type        = number
  default     = 7
}

# GitHub/JIRA Secret Names
variable "github_secret_name" {
  description = "Name of GitHub credentials secret"
  type        = string
  default     = "github-repo-automation/github"
}

variable "jira_secret_name" {
  description = "Name of JIRA credentials secret"
  type        = string
  default     = "github-repo-automation/jira"
}

# JIRA Transition Configuration - Success
variable "auto_transition_on_success" {
  description = "Auto-transition JIRA ticket on success"
  type        = string
  default     = "false"
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

# DLQ Configuration
variable "dlq_batch_size" {
  description = "Number of DLQ messages to process in one batch"
  type        = number
  default     = 1
}

# Notification Configuration
variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications (optional, store in Secrets Manager for production)"
  type        = string
  default     = ""
  sensitive   = true
}

# Tags
variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Product        = "REL"
    SubProduct     = "githubautomation"
    EngineeringEnv = "Prod"
    SubEnv         = "PODG"
    OwnerTeam      = "cloudautomation"
    Layer          = "Compute"
    Tenancy        = "Shared"
  }
}

