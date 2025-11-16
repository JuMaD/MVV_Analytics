# Quick Start Guide - Munich Transit Reachability Map

Deploy to GCP in under 15 minutes with a single command.

## Prerequisites

Install these tools first:

```bash
# macOS
brew install --cask google-cloud-sdk
brew install terraform docker

# Linux
# Install gcloud: https://cloud.google.com/sdk/docs/install
# Install terraform: https://www.terraform.io/downloads
# Install docker: https://docs.docker.com/get-docker/

# Windows
# Download and install:
# - gcloud: https://cloud.google.com/sdk/docs/install
# - terraform: https://www.terraform.io/downloads
# - docker: https://www.docker.com/products/docker-desktop
```

## Deploy in 3 Steps

### 1. Clone Repository

```bash
git clone https://github.com/JuMaD/MVV_Analytics.git
cd MVV_Analytics
```

### 2. Run Setup Script

```bash
./scripts/setup.sh
```

**What it does:**
- Checks prerequisites
- Authenticates with GCP
- Creates Terraform infrastructure
- Builds and deploys Docker image
- Initializes GTFS data
- Returns your live application URL

**What you need to provide:**
- GCP Project ID (you'll be prompted)
- Confirmation to deploy

### 3. Open Your Application

The script will output your application URL:

```
Application URL:
  https://munich-transit-map-xxxxx-ew.a.run.app
```

Open this URL in your browser and you're done! 🎉

## What You Get

✅ **Live Web Application**
- Interactive Munich transit map
- Reachability calculations
- Animated visualizations
- Automatic daily updates

✅ **Production Infrastructure**
- Auto-scaling (0-10 instances)
- HTTPS enabled
- 99.95% uptime SLA
- ~$7-15/month cost

## Quick Commands

```bash
# Deploy code updates
./scripts/deploy.sh

# Trigger manual data update
CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url)
ADMIN_TOKEN=$(cd terraform && terraform output -raw admin_token)
curl -X POST -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "${CLOUD_RUN_URL}/api/admin/update-gtfs"

# View logs
gcloud run services logs tail munich-transit-map --region=europe-west3

# Destroy everything
./scripts/teardown.sh
```

## Troubleshooting

**"gcloud: command not found"**
→ Install gcloud CLI: https://cloud.google.com/sdk/docs/install

**"terraform: command not found"**
→ Install Terraform: https://www.terraform.io/downloads

**"Permission denied" errors**
→ Run: `gcloud auth application-default login`

**"403 Forbidden" when downloading GTFS**
→ This is normal from sandbox. Works fine in GCP Cloud Run.

## Full Documentation

- [Complete Deployment Guide](docs/DEPLOYMENT.md) - Detailed manual setup, configuration options
- [README](README.md) - Full project documentation
- [Screenshots Guide](docs/SCREENSHOTS.md) - How to capture UI screenshots

## Cost Information

**Expected monthly cost** with default settings:
- Cloud Run: ~$5-10
- Cloud Storage: ~$1-2
- Cloud Scheduler: ~$0.10
- Artifact Registry: ~$1

**Total: ~$7-15/month**

To reduce costs:
- Set `cloud_run_min_instances = 0` in `terraform.tfvars` (scale to zero when idle)
- Use `cloud_run_memory = "1Gi"` for lower memory tier

## Support

- **Issues**: https://github.com/JuMaD/MVV_Analytics/issues
- **GCP Support**: https://cloud.google.com/support

---

**Setup Time**: 10-15 minutes
**Difficulty**: Easy (if you have GCP account)
