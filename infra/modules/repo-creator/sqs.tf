# ============================================================================
# SQS QUEUES
# Main queue and Dead Letter Queue for failed messages
# ============================================================================

# Dead Letter Queue (DLQ)
resource "aws_sqs_queue" "dlq" {
  name = "${var.project_name}-dlq"
  
  visibility_timeout_seconds = var.sqs_visibility_timeout
  message_retention_seconds  = var.dlq_message_retention
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-dlq"
    }
  )
}

# Main Queue
resource "aws_sqs_queue" "main" {
  name = "${var.project_name}-queue"
  
  visibility_timeout_seconds = var.sqs_visibility_timeout
  message_retention_seconds  = var.sqs_message_retention
  
  # Redrive policy - send to DLQ after max retries
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })
  
  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-main-queue"
    }
  )
}

