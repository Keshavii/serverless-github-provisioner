# ============================================================================
# TEST ENVIRONMENT - MAIN CONFIGURATION
# Orchestrates all modules for GitHub repository automation
# ============================================================================

locals {
  project_name     = "${var.project_name}-${var.environment}"
  # Point to repository root so we can zip with src/ folder structure
  source_code_root = "${path.module}/../../.."
}

# ============================================================================
# LAMBDA LAYER MODULE
# Python dependencies for all Lambda functions
# ============================================================================
module "lambda_layer" {
  source = "../../modules/lambda-layer"

  project_name      = local.project_name
  requirements_path = "${path.module}/../../.."
  lambda_runtime    = var.lambda_runtime

  tags = var.tags
}

# ============================================================================
# SECRETS MODULE
# Manages GitHub App and JIRA credentials
# ============================================================================
module "secrets" {
  source = "../../modules/secrets"

  project_name = local.project_name

  # GitHub App Configuration
  # The app must be installed on all orgs where you want to create repos
  # Installation ID is detected automatically by the code at runtime
  github_app_id          = var.github_app_id
  github_app_private_key = var.github_app_private_key

  # JIRA Configuration (optional for testing)
  jira_url   = var.jira_url
  jira_email = var.jira_email
  jira_token = var.jira_token

  recovery_window_in_days = var.recovery_window_in_days

  tags = var.tags
}

# ============================================================================
# NOTIFICATIONS MODULE
# SNS topic for alerts and notifications
# ============================================================================
module "notifications" {
  source = "../../modules/notifications"

  project_name = local.project_name

  slack_webhook_url = var.slack_webhook_url

  tags = var.tags
}

# ============================================================================
# REPO CREATOR MODULE
# SQS queues + Lambda function for repository creation
# ============================================================================
module "repo_creator" {
  source = "../../modules/repo-creator"

  project_name     = local.project_name
  source_code_root = local.source_code_root

  # Lambda Layer ARN from lambda_layer module
  lambda_layer_arn = module.lambda_layer.layer_arn

  # Secret ARNs from secrets module
  github_secret_arn  = module.secrets.github_secret_arn
  github_secret_name = var.github_secret_name
  jira_secret_arn    = module.secrets.jira_secret_arn
  jira_secret_name   = var.jira_secret_name

  # Credentials (passed as environment variables)
  github_app_id          = var.github_app_id
  github_app_private_key = var.github_app_private_key
  jira_url               = var.jira_url
  jira_email             = var.jira_email
  jira_token             = var.jira_token

  # Lambda Configuration
  lambda_runtime     = var.lambda_runtime
  lambda_timeout     = var.lambda_timeout
  lambda_memory_size = var.lambda_memory_size
  environment        = var.environment

  # SNS topic ARN from notifications module
  sns_alert_topic_arn = module.notifications.sns_topic_arn

  # Slack webhook URL for direct notifications
  slack_webhook_url = var.slack_webhook_url

  # JIRA Transition Configuration
  auto_transition_on_success = var.auto_transition_on_success
  success_transition_name    = var.success_transition_name
  success_resolution         = var.success_resolution
  auto_transition_on_failure = var.auto_transition_on_failure
  failure_transition_name    = var.failure_transition_name
  failure_resolution         = var.failure_resolution

  # Logging Configuration
  log_level      = var.log_level
  log_format     = var.log_format
  enable_metrics = var.enable_metrics

  # SQS Configuration
  batch_size              = var.batch_size
  batching_window         = var.batching_window
  sqs_visibility_timeout  = var.sqs_visibility_timeout
  sqs_message_retention   = var.sqs_message_retention
  dlq_message_retention   = var.dlq_message_retention
  sqs_max_receive_count   = var.sqs_max_receive_count

  tags = var.tags
}

# ============================================================================
# DLQ HANDLER MODULE
# Lambda function to process failed messages
# ============================================================================
module "dlq_handler" {
  source = "../../modules/dlq-handler"

  project_name     = local.project_name
  source_code_root = local.source_code_root

  # Lambda Layer ARN from lambda_layer module
  lambda_layer_arn = module.lambda_layer.layer_arn

  # DLQ from repo_creator module
  dlq_arn = module.repo_creator.dlq_arn

  # JIRA secret from secrets module
  jira_secret_arn  = module.secrets.jira_secret_arn
  jira_secret_name = var.jira_secret_name

  # SNS topic ARN from notifications module
  sns_alert_topic_arn = module.notifications.sns_topic_arn

  # Slack webhook URL for direct notifications
  slack_webhook_url = var.slack_webhook_url

  # Lambda Configuration
  lambda_runtime     = var.lambda_runtime
  lambda_timeout     = 60
  lambda_memory_size = var.lambda_memory_size

  # DLQ Configuration
  dlq_batch_size = var.dlq_batch_size

  tags = var.tags
}

