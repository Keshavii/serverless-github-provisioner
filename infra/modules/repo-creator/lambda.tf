# ============================================================================
# LAMBDA FUNCTION - REPOSITORY CREATOR
# Triggered by SQS messages to create GitHub repositories
# ============================================================================

# Build Lambda package with src/ folder structure preserved
resource "null_resource" "build_package" {
  triggers = {
    # Rebuild if any Python file changes
    source_hash = sha256(join("", [for f in fileset("${var.source_code_root}/src", "**/*.py") : filesha256("${var.source_code_root}/src/${f}")]))
  }

  provisioner "local-exec" {
    command = <<-EOT
      cd ${var.source_code_root}
      rm -rf /tmp/lambda-build-${md5(path.module)}
      mkdir -p /tmp/lambda-build-${md5(path.module)}
      cp -r src /tmp/lambda-build-${md5(path.module)}/
      cd /tmp/lambda-build-${md5(path.module)}
      zip -r ${abspath(path.module)}/lambda-deployment.zip src -x "*.pyc" -x "*__pycache__*" -x "*/tests/*" -x "*.md"
    EOT
  }
}

resource "aws_lambda_function" "repo_creator" {
  depends_on       = [null_resource.build_package]
  filename         = "${path.module}/lambda-deployment.zip"
  function_name    = "${var.project_name}-repo-creator"
  role             = aws_iam_role.lambda.arn
  # Handler format: src.module.function (src/ folder preserved in zip)
  # See src/github_handler.py with function lambda_handler()
  handler          = "src.github_handler.lambda_handler"
  # Use trigger hash instead of file hash to avoid race conditions
  source_code_hash = null_resource.build_package.triggers.source_hash
  runtime          = "python${var.lambda_runtime}"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  # Attach Lambda Layer with Python dependencies
  layers = [var.lambda_layer_arn]

  environment {
    variables = {
      # Secret Names (for accessing credentials in Lambda)
      GITHUB_SECRET_NAME = var.github_secret_name
      JIRA_SECRET_NAME   = var.jira_secret_name

      # GitHub App Credentials
      GITHUB_APP_ID          = var.github_app_id
      GITHUB_APP_PRIVATE_KEY = var.github_app_private_key

      # JIRA Configuration
      JIRA_URL       = var.jira_url
      JIRA_EMAIL     = var.jira_email
      JIRA_API_TOKEN = var.jira_token

      # JIRA Transition Configuration - Success
      AUTO_TRANSITION_ON_SUCCESS = var.auto_transition_on_success
      SUCCESS_TRANSITION_NAME    = var.success_transition_name
      SUCCESS_RESOLUTION         = var.success_resolution

      # JIRA Transition Configuration - Repository Creation Failure
      AUTO_TRANSITION_ON_FAILURE = var.auto_transition_on_failure
      FAILURE_TRANSITION_NAME    = var.failure_transition_name
      FAILURE_RESOLUTION         = var.failure_resolution

      # Logging Configuration
      LOG_LEVEL      = var.log_level
      LOG_FORMAT     = var.log_format
      ENABLE_METRICS = var.enable_metrics
      ENVIRONMENT    = var.environment

      # SNS topic ARN for notifications
      SNS_ALERT_TOPIC_ARN = var.sns_alert_topic_arn

      # Slack webhook URL for direct notifications
      SLACK_WEBHOOK_URL = var.slack_webhook_url

      # CloudWatch Metrics Configuration
      CLOUDWATCH_NAMESPACE = "GitHubRepoAutomation"
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-repo-creator"
    }
  )
}

# Explicit CloudWatch log group for the repo-creator Lambda
resource "aws_cloudwatch_log_group" "repo_creator" {
  name              = "/aws/lambda/${var.project_name}-repo-creator"
  retention_in_days = 14

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-repo-creator-logs"
    }
  )
}

# Event Source Mapping - SQS to Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  # Ensure IAM permissions are in place before creating the trigger
  depends_on = [aws_iam_role_policy_attachment.lambda_custom]

  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.repo_creator.arn
  batch_size       = var.batch_size

  maximum_batching_window_in_seconds = var.batching_window

  function_response_types = ["ReportBatchItemFailures"]

  enabled = true
}

