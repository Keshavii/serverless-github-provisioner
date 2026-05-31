# ============================================================================
# SNS TOPIC FOR NOTIFICATIONS
# Used for email and Slack notifications
# ============================================================================

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-alerts"
    }
  )
}

# ============================================================================
# SNS TOPIC POLICY
# Allow Lambda functions to publish to this topic
# ============================================================================

resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaPublish"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}

# ============================================================================
# HTTPS SUBSCRIPTION FOR SLACK 
# Direct SNS to Slack webhook integration
# ============================================================================

resource "aws_sns_topic_subscription" "slack_https" {
  count     = var.slack_webhook_url != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = var.slack_webhook_url
}
