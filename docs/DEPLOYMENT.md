# Deployment Guide - Munich Transit Reachability Map

Complete guide for deploying to Google Cloud Platform using Infrastructure as Code (Terraform).

## Prerequisites

Before you begin, ensure you have:

1. **Google Cloud Platform Account**
   - Active GCP account with billing enabled
   - A GCP project created
   - Owner or Editor permissions on the project

2. **Local Tools Installed**
   - [gcloud CLI](https://cloud.google.com/sdk/docs/install) - Google Cloud command-line tool
   - [Terraform](https://www.terraform.io/downloads) - Infrastructure as Code tool (v1.0+)
   - [Docker](https://docs.docker.com/get-docker/) - For building container images
   - Git - For cloning the repository

3. **Verify Installations**
   ```bash
   gcloud --version
   terraform --version
   docker --version
   ```

## Quick Start (Automated Setup)

The easiest way to deploy is using the automated setup script:

```bash
# 1. Clone the repository
git clone https://github.com/JuMaD/MVV_Analytics.git
cd MVV_Analytics

# 2. Run the setup script (this does EVERYTHING)
./scripts/setup.sh
```

The setup script will:
1. Check prerequisites
2. Authenticate with GCP
3. Create infrastructure with Terraform
4. Build and deploy the Docker image
5. Initialize GTFS data
6. Provide you with the application URL

**That's it!** The application will be live at the provided URL.

## What Gets Created

The Terraform configuration creates:

### 1. Cloud Storage Buckets
- **GTFS Data Bucket**: Stores downloaded GTFS files and metadata
- **Graph Data Bucket**: Stores pre-computed transit network graphs
- Automatic lifecycle policies (90-day retention)

### 2. Cloud Run Service
- **App Name**: `munich-transit-map`
- **Memory**: 2GB (configurable)
- **CPU**: 2 cores (configurable)
- **Auto-scaling**: 0-10 instances (configurable)
- **Timeout**: 5 minutes
- **Public Access**: Enabled (unauthenticated)

### 3. Cloud Scheduler Job
- **Schedule**: Daily at 6:00 AM CET
- **Action**: Triggers GTFS data update endpoint
- **Retries**: 3 attempts on failure

### 4. Artifact Registry
- **Repository**: Docker images for the application
- **Location**: Same region as Cloud Run

### 5. Service Accounts
- **Cloud Run SA**: For accessing storage buckets
- **Scheduler SA**: For invoking Cloud Run endpoints

### 6. IAM Permissions
- Appropriate roles for each service account
- Public access for Cloud Run service

## Manual Setup (Step-by-Step)

If you prefer manual control over the process:

### Step 1: Authenticate

```bash
# Login to GCP
gcloud auth login

# Set your project
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# Setup application default credentials
gcloud auth application-default login

# Configure Docker for Artifact Registry
gcloud auth configure-docker europe-west3-docker.pkg.dev
```

### Step 2: Configure Terraform Variables

```bash
# Copy example file
cp terraform/terraform.tfvars.example terraform/terraform.tfvars

# Generate a secure admin token
openssl rand -base64 32

# Edit terraform.tfvars
nano terraform/terraform.tfvars
```

Set these required variables:
```hcl
project_id = "your-project-id"
admin_token = "your-secure-token-from-above"
```

Optional customizations:
```hcl
region = "europe-west3"  # Default: Frankfurt
cloud_run_memory = "2Gi"
cloud_run_cpu = "2"
cloud_run_max_instances = 10
update_schedule = "0 6 * * *"  # Daily at 6 AM CET
```

### Step 3: Deploy Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

Terraform will show you all resources to be created. Type `yes` to confirm.

### Step 4: Build and Deploy Application

```bash
# Return to project root
cd ..

# Run deploy script
./scripts/deploy.sh
```

This will:
- Build the Docker image
- Push to Artifact Registry
- Deploy to Cloud Run

### Step 5: Initialize GTFS Data

```bash
# Get the Cloud Run URL from Terraform output
CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url)
ADMIN_TOKEN=$(cd terraform && terraform output -raw admin_token)

# Trigger initial data download
curl -X POST \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "${CLOUD_RUN_URL}/api/admin/update-gtfs"
```

This will download GTFS data from MVV and build the transit graphs (~5-10 minutes).

## Verify Deployment

### Check Application Health

```bash
CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url)

# Health check
curl "${CLOUD_RUN_URL}/health"

# Expected response:
# {"status":"healthy","calculator_loaded":true}
```

### Test the API

```bash
# Get metadata
curl "${CLOUD_RUN_URL}/api/metadata"

# Get all stops
curl "${CLOUD_RUN_URL}/api/stops" | head -100
```

### Open in Browser

```bash
# Get the URL
cd terraform
terraform output cloud_run_url

# Open in browser (macOS)
open $(terraform output -raw cloud_run_url)

# Or manually copy the URL and paste in browser
```

## Configuration Options

### Terraform Variables

All configurable options in `terraform/variables.tf`:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `project_id` | GCP Project ID | - | ✅ Yes |
| `admin_token` | Admin API token | - | ✅ Yes |
| `region` | GCP region | `europe-west3` | No |
| `app_name` | Application name | `munich-transit-map` | No |
| `cloud_run_memory` | Memory allocation | `2Gi` | No |
| `cloud_run_cpu` | CPU allocation | `2` | No |
| `cloud_run_max_instances` | Max instances | `10` | No |
| `cloud_run_min_instances` | Min instances | `0` | No |
| `update_schedule` | Cron schedule | `0 6 * * *` | No |

### Regions

Available regions (choose closest to your users):

- `europe-west3` - Frankfurt, Germany (default)
- `europe-west1` - Belgium
- `europe-west4` - Netherlands
- `us-central1` - Iowa, USA
- `asia-northeast1` - Tokyo, Japan

Update in `terraform.tfvars`:
```hcl
region = "europe-west1"
```

### Scaling Configuration

For higher traffic:

```hcl
cloud_run_memory = "4Gi"
cloud_run_cpu = "4"
cloud_run_max_instances = 50
cloud_run_min_instances = 1  # Keep 1 instance warm
```

For lower costs:
```hcl
cloud_run_memory = "1Gi"
cloud_run_cpu = "1"
cloud_run_max_instances = 5
cloud_run_min_instances = 0  # Scale to zero when idle
```

## Updating the Application

### Deploy Code Changes

```bash
# Make your code changes
git add .
git commit -m "Your changes"

# Deploy updated application
./scripts/deploy.sh
```

### Update Infrastructure

```bash
# Modify terraform/*.tf files or terraform.tfvars

# Apply changes
cd terraform
terraform plan
terraform apply
cd ..
```

### Manual GTFS Update

```bash
# Trigger data update manually
CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url)
ADMIN_TOKEN=$(cd terraform && terraform output -raw admin_token)

curl -X POST \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "${CLOUD_RUN_URL}/api/admin/update-gtfs"
```

## Monitoring & Logs

### Cloud Run Logs

```bash
# View recent logs
gcloud run services logs read munich-transit-map \
  --region=europe-west3 \
  --limit=50

# Stream logs in real-time
gcloud run services logs tail munich-transit-map \
  --region=europe-west3
```

### Cloud Scheduler Logs

```bash
# View scheduler execution history
gcloud scheduler jobs describe munich-transit-map-update \
  --location=europe-west3

# View logs
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=munich-transit-map-update" \
  --limit=10 \
  --format=json
```

### GCP Console

- **Cloud Run**: https://console.cloud.google.com/run
- **Cloud Scheduler**: https://console.cloud.google.com/cloudscheduler
- **Storage**: https://console.cloud.google.com/storage
- **Logs**: https://console.cloud.google.com/logs

## Cost Estimation

### Expected Monthly Costs (Light Usage)

With default settings and ~1,000 requests/day:

- **Cloud Run**: ~$5-10/month
  - CPU/Memory usage
  - Request handling
- **Cloud Storage**: ~$1-2/month
  - GTFS data (~200MB)
  - Graph data (~5MB)
- **Cloud Scheduler**: ~$0.10/month
  - 1 job, daily execution
- **Artifact Registry**: ~$1/month
  - Docker image storage

**Total**: ~$7-15/month

### Cost Optimization

1. **Scale to Zero**: Set `cloud_run_min_instances = 0`
2. **Reduce Memory**: Use `1Gi` if traffic is low
3. **Storage Lifecycle**: Auto-delete old versions (already configured)

## Troubleshooting

### "Permission Denied" errors

```bash
# Ensure you have correct permissions
gcloud projects get-iam-policy $GCP_PROJECT_ID

# Grant yourself necessary roles
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="user:your-email@example.com" \
  --role="roles/editor"
```

### Terraform state issues

```bash
# If state is corrupted
cd terraform
terraform state list  # View current state
terraform refresh     # Sync with actual resources

# If all else fails, import existing resources
terraform import google_cloud_run_service.app munich-transit-map
```

### Docker push fails

```bash
# Re-authenticate Docker
gcloud auth configure-docker europe-west3-docker.pkg.dev

# Verify permissions
gcloud artifacts repositories list --location=europe-west3
```

### Application not responding

```bash
# Check Cloud Run status
gcloud run services describe munich-transit-map --region=europe-west3

# View recent errors
gcloud run services logs read munich-transit-map --region=europe-west3 --limit=100

# Check if graphs are initialized
CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url)
curl "${CLOUD_RUN_URL}/health"
```

## Cleanup / Teardown

To delete all resources and stop billing:

```bash
# WARNING: This deletes EVERYTHING
./scripts/teardown.sh
```

Or manually:

```bash
cd terraform
terraform destroy
cd ..
```

This will remove:
- Cloud Run service
- Cloud Scheduler job
- Storage buckets (and all data)
- Artifact Registry repository
- Service accounts
- IAM bindings

## Security Best Practices

1. **Admin Token**: Store securely, don't commit to git
2. **Service Accounts**: Use principle of least privilege
3. **API Access**: Consider adding authentication for production
4. **HTTPS**: Always enabled by default on Cloud Run
5. **Secrets**: Use Secret Manager for sensitive data (optional upgrade)

## Next Steps

After deployment:

1. **Custom Domain**: [Configure custom domain](https://cloud.google.com/run/docs/mapping-custom-domains)
2. **SSL Certificate**: Automatically provisioned by Cloud Run
3. **Monitoring**: Set up [Cloud Monitoring alerts](https://cloud.google.com/monitoring/alerts)
4. **CI/CD**: Integrate with [Cloud Build triggers](https://cloud.google.com/build/docs/automating-builds/create-manage-triggers)

## Support

- **Issues**: https://github.com/JuMaD/MVV_Analytics/issues
- **GCP Documentation**: https://cloud.google.com/docs
- **Terraform Documentation**: https://www.terraform.io/docs

---

**Estimated Setup Time**: 10-15 minutes (automated) or 30-45 minutes (manual)
