# Terraform Outputs

output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.app.status[0].url
}

output "gtfs_bucket_name" {
  description = "Name of the GTFS data bucket"
  value       = google_storage_bucket.gtfs_data.name
}

output "graph_bucket_name" {
  description = "Name of the graph data bucket"
  value       = google_storage_bucket.graph_data.name
}

output "docker_repository" {
  description = "Artifact Registry repository for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "scheduler_job_name" {
  description = "Name of the Cloud Scheduler job"
  value       = var.enable_scheduler ? google_cloud_scheduler_job.gtfs_update[0].name : "disabled"
}

output "service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloud_run.email
}

output "scheduler_enabled" {
  description = "Whether automatic updates via Cloud Scheduler are enabled"
  value       = var.enable_scheduler
}

output "next_steps" {
  description = "Next steps after infrastructure deployment"
  value = <<-EOT

    ✅ Infrastructure deployed successfully!

    📍 Application URL: ${google_cloud_run_service.app.status[0].url}

    🚀 Next steps:
    1. Build and deploy the application:
       ./scripts/deploy.sh

    2. Initialize GTFS data (first time only):
       curl -X POST -H "Authorization: Bearer ${nonsensitive(var.admin_token)}" \
         ${google_cloud_run_service.app.status[0].url}/api/admin/update-gtfs

    3. Open the application:
       ${google_cloud_run_service.app.status[0].url}

    📊 Monitoring:
    - Cloud Run: https://console.cloud.google.com/run/detail/${var.region}/${google_cloud_run_service.app.name}/metrics
    ${var.enable_scheduler ? "- Scheduler: https://console.cloud.google.com/cloudscheduler?project=${var.project_id}" : "- Scheduler: DISABLED (manual updates only)"}
    - Storage: https://console.cloud.google.com/storage/browser/${google_storage_bucket.gtfs_data.name}

    ${var.enable_scheduler ? "⏰ Automatic updates: Enabled (${var.update_schedule})" : "⚠️  Automatic updates: DISABLED - Use ./scripts/manual_update.sh to update data"}
  EOT
}
