# ============================================================================
# NOTIFICATIONS MODULE VARIABLES
# ============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  default     = ""
  sensitive   = true
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
