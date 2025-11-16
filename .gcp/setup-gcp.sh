#!/bin/bash
# Setup script for GCP infrastructure

set -e

# Configuration
PROJECT_ID=${1:-"your-project-id"}
REGION="europe-west3"
BUCKET_NAME="munich-transit-data-${PROJECT_ID}"
SERVICE_NAME="munich-transit-map"
UPDATE_JOB_NAME="munich-transit-update"

echo "================================================"
echo "Setting up GCP infrastructure"
echo "================================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo ""

# Set project
echo "Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    storage.googleapis.com

# Create GCS bucket
echo "Creating Cloud Storage bucket..."
gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${BUCKET_NAME}/ || echo "Bucket already exists"

# Set bucket permissions
echo "Setting bucket permissions..."
gsutil iam ch allUsers:objectViewer gs://${BUCKET_NAME}

# Create bucket structure
echo "Creating bucket structure..."
gsutil mkdir gs://${BUCKET_NAME}/gtfs_data/ || true
gsutil mkdir gs://${BUCKET_NAME}/graphs/ || true

# Build and deploy
echo "Building and deploying application..."
gcloud builds submit --config=.gcp/cloudbuild.yaml

# Create Cloud Scheduler job for daily updates
echo "Creating Cloud Scheduler job..."
gcloud scheduler jobs create http ${UPDATE_JOB_NAME} \
    --location=${REGION} \
    --schedule="0 6 * * *" \
    --uri="https://$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')/api/admin/update-gtfs" \
    --http-method=POST \
    --headers="Authorization=Bearer YOUR_ADMIN_TOKEN_HERE" \
    --time-zone="Europe/Berlin" \
    || echo "Scheduler job already exists"

echo ""
echo "================================================"
echo "Setup complete!"
echo "================================================"
echo ""
echo "Application URL:"
gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)'
echo ""
echo "Next steps:"
echo "1. Update the ADMIN_TOKEN in Cloud Scheduler job"
echo "2. Initialize data by calling the update endpoint manually"
echo "3. Test the application"
echo ""
