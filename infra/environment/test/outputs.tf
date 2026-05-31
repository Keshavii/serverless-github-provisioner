# ============================================================================
# TEST ENVIRONMENT OUTPUTS
# ============================================================================

# Lambda Functions
output "lambda_functions" {
	  description = "Lambda function details"
	  value = {
	    repo_creator = module.repo_creator.lambda_arn
	    dlq_handler  = module.dlq_handler.lambda_arn
	  }
	}

# SQS Queues
output "sqs_queues" {
  description = "SQS queue details"
  value = {
    main_queue_url = module.repo_creator.main_queue_url
    main_queue_arn = module.repo_creator.main_queue_arn
    dlq_url        = module.repo_creator.dlq_url
    dlq_arn        = module.repo_creator.dlq_arn
  }
}

# Secrets
output "secrets" {
  description = "Secrets Manager secret names"
  value = {
    github_secret_name = module.secrets.github_secret_name
    jira_secret_name   = module.secrets.jira_secret_name
  }
}

# Notifications
output "notifications" {
  description = "Notification configuration"
  value = {
    sns_topic_arn  = module.notifications.sns_topic_arn
    sns_topic_name = module.notifications.sns_topic_name
  }
}

# Event Source Mappings
output "event_source_mappings" {
  description = "Event source mapping UUIDs"
  value = {
    main_queue_to_repo_creator = module.repo_creator.event_source_mapping_uuid
    dlq_to_handler             = module.dlq_handler.event_source_mapping_uuid
  }
}

# Deployment Summary
output "deployment_summary" {
  description = "Complete deployment summary"
  value = {
    environment = var.environment
    region      = var.aws_region
    lambda_functions = {
	      repo_creator = module.repo_creator.lambda_name
	      dlq_handler  = module.dlq_handler.lambda_name
    }
    
    sqs_queues = {
      main_queue = module.repo_creator.main_queue_url
      dlq        = module.repo_creator.dlq_url
    }
    
    configuration = {
      batch_size         = var.batch_size
      lambda_timeout     = var.lambda_timeout
      max_receive_count  = var.sqs_max_receive_count
      visibility_timeout = var.sqs_visibility_timeout
    }
  }
}

# Next Steps
output "next_steps" {
  description = "Next steps after deployment"
	  value = <<-EOT
	  
	  ============================================================================
	  🎉 DEPLOYMENT COMPLETE!
	  ============================================================================
	  
	  📋 NEXT STEPS:
	  
	  1. Test the System:
	       
	   Send a test message to the SQS main queue
	   
	   Watch CloudWatch logs:
	   aws logs tail /aws/lambda/${module.repo_creator.lambda_name} --follow
	  
	  2. Monitor SQS Queues:
	       
	   Main Queue: ${module.repo_creator.main_queue_url}
	   DLQ: ${module.repo_creator.dlq_url}
	  
	  ============================================================================
	  📊 CONFIGURATION:
	  
	  • Environment: ${var.environment}
	  • Region: ${var.aws_region}
	  • Batch Size: ${var.batch_size} messages
	  • Retry Count: ${var.sqs_max_receive_count} times before DLQ
	  • Lambda Timeout: ${var.lambda_timeout}s
	  
	  ============================================================================
	  
	  EOT
}

