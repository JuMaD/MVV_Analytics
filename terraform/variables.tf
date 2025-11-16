# Terraform Variables for Munich Transit Reachability Map

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west3"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "europe-west3-a"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "munich-transit-map"
}

variable "admin_token" {
  description = "Admin token for update endpoint"
  type        = string
  sensitive   = true
}

variable "cloud_run_memory" {
  description = "Memory allocation for Cloud Run"
  type        = string
  default     = "2Gi"
}

variable "cloud_run_cpu" {
  description = "CPU allocation for Cloud Run"
  type        = string
  default     = "2"
}

variable "cloud_run_max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cloud_run_min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 0
}

variable "update_schedule" {
  description = "Cron schedule for GTFS updates (default: daily at 6 AM CET)"
  type        = string
  default     = "0 6 * * *"
}

variable "enable_scheduler" {
  description = "Enable automatic GTFS updates via Cloud Scheduler (set to false for manual-only updates)"
  type        = bool
  default     = true
}

variable "initial_image" {
  description = "Initial placeholder image for first deployment (use empty string to skip)"
  type        = string
  default     = "gcr.io/cloudrun/hello"
}
