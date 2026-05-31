# ============================================================================
# LAMBDA LAYER - VARIABLES
# ============================================================================

variable "project_name" {
  description = "Project name prefix"
  type        = string
}

variable "requirements_path" {
  description = "Path to the directory containing requirements.txt"
  type        = string
}

variable "lambda_runtime" {
  description = "Lambda runtime version (e.g., 3.9, 3.11)"
  type        = string
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
