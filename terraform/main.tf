# Main Terraform Configuration for Munich Transit Reachability Map

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Optional: Configure remote state in GCS
  # backend "gcs" {
  #   bucket = "YOUR_TERRAFORM_STATE_BUCKET"
  #   prefix = "terraform/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "cloudscheduler.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# Cloud Storage bucket for GTFS data
resource "google_storage_bucket" "gtfs_data" {
  name          = "${var.project_id}-${var.app_name}-data"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = false
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

# Cloud Storage bucket for graph data
resource "google_storage_bucket" "graph_data" {
  name          = "${var.project_id}-${var.app_name}-graphs"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = false
  }

  depends_on = [google_project_service.apis]
}

# Service account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "${var.app_name}-run-sa"
  display_name = "Service Account for Munich Transit Map Cloud Run"

  depends_on = [google_project_service.apis]
}

# Grant Cloud Run service account access to Storage buckets
resource "google_storage_bucket_iam_member" "gtfs_data_access" {
  bucket = google_storage_bucket.gtfs_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_storage_bucket_iam_member" "graph_data_access" {
  bucket = google_storage_bucket.graph_data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.app_name
  description   = "Docker repository for Munich Transit Map"
  format        = "DOCKER"

  depends_on = [google_project_service.apis]
}

# Cloud Run service
resource "google_cloud_run_service" "app" {
  name     = var.app_name
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.cloud_run.email

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}/${var.app_name}:latest"

        resources {
          limits = {
            memory = var.cloud_run_memory
            cpu    = var.cloud_run_cpu
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "GCS_BUCKET_NAME"
          value = google_storage_bucket.gtfs_data.name
        }

        env {
          name  = "ADMIN_TOKEN"
          value = var.admin_token
        }

        ports {
          container_port = 8000
        }
      }

      container_concurrency = 80
      timeout_seconds      = 300
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = var.cloud_run_max_instances
        "autoscaling.knative.dev/minScale" = var.cloud_run_min_instances
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  autogenerate_revision_name = true

  depends_on = [
    google_project_service.apis,
    google_storage_bucket.gtfs_data,
    google_service_account.cloud_run,
  ]

  lifecycle {
    ignore_changes = [
      template[0].spec[0].containers[0].image,
    ]
  }
}

# Allow unauthenticated access to Cloud Run service
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.app.name
  location = google_cloud_run_service.app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Service account for Cloud Scheduler
resource "google_service_account" "scheduler" {
  account_id   = "${var.app_name}-scheduler-sa"
  display_name = "Service Account for Munich Transit Map Cloud Scheduler"

  depends_on = [google_project_service.apis]
}

# Grant scheduler permission to invoke Cloud Run
resource "google_cloud_run_service_iam_member" "scheduler_invoker" {
  service  = google_cloud_run_service.app.name
  location = google_cloud_run_service.app.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

# Cloud Scheduler job for daily GTFS updates
resource "google_cloud_scheduler_job" "gtfs_update" {
  name             = "${var.app_name}-update"
  description      = "Daily GTFS data update check"
  schedule         = var.update_schedule
  time_zone        = "Europe/Berlin"
  attempt_deadline = "320s"
  region           = var.region

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_service.app.status[0].url}/api/admin/update-gtfs"

    headers = {
      "Authorization" = "Bearer ${var.admin_token}"
      "Content-Type"  = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  retry_config {
    retry_count = 3
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_service.app,
  ]
}
