# ============================================================================
# LAMBDA FUNCTION - DLQ HANDLER
# Processes failed messages from Dead Letter Queue
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

data "archive_file" "lambda_package" {
  depends_on  = [null_resource.build_package]
  type        = "zip"
  source_dir  = "${var.source_code_root}/src"
  output_path = "${path.module}/lambda-deployment-fallback.zip"
}

resource "aws_lambda_function" "dlq_handler" {
  depends_on       = [null_resource.build_package]
  filename         = "${path.module}/lambda-deployment.zip"
  function_name    = "${var.project_name}-dlq-handler"
  role             = aws_iam_role.lambda.arn
  # Handler format: src.module.function (src/ folder preserved in zip)
  # See src/dlq_handler.py with function lambda_handler()
  handler          = "src.dlq_handler.lambda_handler"
  # Use trigger hash instead of file hash to avoid race conditions
  source_code_hash = null_resource.build_package.triggers.source_hash
  runtime          = "python${var.lambda_runtime}"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  # Attach Lambda Layer with Python dependencies
  layers = [var.lambda_layer_arn]

  environment {
    variables = {
      # Secret name to match dlq_handler.py expectations
      JIRA_SECRET_NAME = var.jira_secret_name

      # SNS topic ARN for notifications
      SNS_ALERT_TOPIC_ARN = var.sns_alert_topic_arn

      # Slack webhook URL for direct notifications
      SLACK_WEBHOOK_URL = var.slack_webhook_url

      # CloudWatch Metrics Configuration
      CLOUDWATCH_NAMESPACE = "GitHubRepoAutomation"
      ENABLE_METRICS       = "true"
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-dlq-handler"
    }
  )
}

# Explicit CloudWatch log group for the DLQ handler Lambda
resource "aws_cloudwatch_log_group" "dlq_handler" {
  name              = "/aws/lambda/${var.project_name}-dlq-handler"
  retention_in_days = 14

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-dlq-handler-logs"
    }
  )
}

# Event Source Mapping - DLQ to Lambda
resource "aws_lambda_event_source_mapping" "dlq_trigger" {
  # Ensure IAM permissions are in place before creating the trigger
  depends_on = [aws_iam_role_policy_attachment.lambda_custom]

  event_source_arn = var.dlq_arn
  function_name    = aws_lambda_function.dlq_handler.arn
  batch_size       = var.dlq_batch_size

  maximum_batching_window_in_seconds = 0

  enabled = true
}

