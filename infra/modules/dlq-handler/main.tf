# ============================================================================
# DLQ HANDLER MODULE
# Lambda function to process messages from Dead Letter Queue
# ============================================================================

# Lambda IAM Role
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-dlq-handler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-dlq-handler-role"
    }
  )
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy for SQS and Secrets Manager
resource "aws_iam_policy" "lambda_custom" {
  name        = "${var.project_name}-dlq-handler-policy"
  description = "Custom policy for DLQ handler Lambda"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "SQSPermissions"
          Effect = "Allow"
          Action = [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes"
          ]
          Resource = var.dlq_arn
        },
        {
          Sid    = "SecretsManagerPermissions"
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Resource = var.jira_secret_arn
        },
        {
          Sid      = "CloudWatchMetrics"
          Effect   = "Allow"
          Action   = ["cloudwatch:PutMetricData"]
          Resource = "*"
        }
      ],
      # Conditionally add SNS publish permission if topic ARN is provided
      var.sns_alert_topic_arn != "" ? [
        {
          Sid      = "SNSPublishPermissions"
          Effect   = "Allow"
          Action   = ["sns:Publish"]
          Resource = var.sns_alert_topic_arn
        }
      ] : []
    )
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda_custom" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda_custom.arn
}

