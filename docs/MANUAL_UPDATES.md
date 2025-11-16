# Manual Data Updates Guide

Complete guide for manually updating GTFS data and graphs, and disabling automatic updates.

## Option 1: Manual Updates via API (Keep Scheduler, Update on Demand)

### Remote (GCP Deployment)

Trigger a manual update anytime:

```bash
# Get your Cloud Run URL and admin token
CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url)
ADMIN_TOKEN=$(cd terraform && terraform output -raw admin_token)

# Trigger update
curl -X POST \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  "${CLOUD_RUN_URL}/api/admin/update-gtfs"
```

Expected response (takes 5-10 minutes):
```json
{
  "updated": true,
  "message": "GTFS data updated and graphs rebuilt",
  "metadata": {
    "source": "Münchner Verkehrs- und Tarifverbund GmbH (MVV)",
    "download_date": "2025-11-16",
    "feed_version": "2025.11",
    "last_updated": "2025-11-16T10:30:00Z"
  }
}
```

### Local Development

```bash
# From project root
python scripts/init_data.py

# Or via the API if server is running
curl -X POST \
  -H "Authorization: Bearer your-admin-token" \
  http://localhost:8000/api/admin/update-gtfs
```

---

## Option 2: Disable Automatic Updates (Manual Only)

If you want to **completely disable** the Cloud Scheduler and only update manually:

### Method A: Pause the Scheduler (Recommended)

Keep the scheduler but pause it:

```bash
gcloud scheduler jobs pause munich-transit-map-update \
  --location=europe-west3
```

Resume later:
```bash
gcloud scheduler jobs resume munich-transit-map-update \
  --location=europe-west3
```

### Method B: Delete the Scheduler

Remove automatic updates completely:

**Option 1: Via Terraform**

Edit `terraform/variables.tf` or create a new variable:

```hcl
# Add to terraform/variables.tf
variable "enable_scheduler" {
  description = "Enable automatic GTFS updates via Cloud Scheduler"
  type        = bool
  default     = true
}
```

Then edit `terraform/main.tf` to conditionally create the scheduler:

```hcl
# Wrap the scheduler resource in a count
resource "google_cloud_scheduler_job" "gtfs_update" {
  count = var.enable_scheduler ? 1 : 0

  # ... rest of configuration
}
```

Set in `terraform/terraform.tfvars`:
```hcl
enable_scheduler = false
```

Apply changes:
```bash
cd terraform
terraform apply
```

**Option 2: Via gcloud**

Delete the scheduler job directly:

```bash
gcloud scheduler jobs delete munich-transit-map-update \
  --location=europe-west3 \
  --quiet
```

### Method C: Change Schedule to Never Run

Edit `terraform/terraform.tfvars`:

```hcl
# Run on February 30th (never)
update_schedule = "0 0 30 2 *"
```

Apply:
```bash
cd terraform
terraform apply
```

---

## Option 3: Local Data Management (Upload to GCS)

Manually download and process data locally, then upload to GCS:

### Step 1: Process Data Locally

```bash
# Download and build graphs locally
python scripts/init_data.py
```

This creates:
- `static/data/gtfs.zip` - Downloaded GTFS data
- `static/data/gtfs/` - Extracted GTFS files
- `static/data/graphs/` - Built NetworkX graphs
- `static/data/metadata.json` - Metadata

### Step 2: Upload to GCS

```bash
# Get bucket name
BUCKET_NAME=$(cd terraform && terraform output -raw gtfs_bucket_name)

# Upload GTFS data
gsutil cp static/data/gtfs.zip gs://${BUCKET_NAME}/current.zip
gsutil cp static/data/metadata.json gs://${BUCKET_NAME}/metadata.json

# Upload extracted GTFS files
gsutil -m rsync -r static/data/gtfs/ gs://${BUCKET_NAME}/current/

# Upload graphs
gsutil -m rsync -r static/data/graphs/ gs://${BUCKET_NAME}/graphs/
```

### Step 3: Restart Cloud Run

Cloud Run instances will pick up the new data on next restart:

```bash
# Force new revision deployment (same image, new data)
gcloud run services update munich-transit-map \
  --region=europe-west3 \
  --set-env-vars="LAST_UPDATED=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

---

## Option 4: Custom Update Schedule

Change the update frequency:

### Weekly Updates (Sunday 3 AM)

```hcl
# terraform/terraform.tfvars
update_schedule = "0 3 * * 0"
```

### Monthly Updates (1st of month, 2 AM)

```hcl
update_schedule = "0 2 1 * *"
```

### Twice Daily (6 AM and 6 PM)

Create a second scheduler job or use:
```hcl
update_schedule = "0 6,18 * * *"
```

### Custom Cron Expression

Cron format: `minute hour day month day-of-week`

Examples:
- `0 6 * * *` - Daily at 6 AM
- `0 6 * * 1-5` - Weekdays at 6 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 1,15 * *` - 1st and 15th of month

Apply changes:
```bash
cd terraform
terraform apply
```

---

## Manual Update Scripts

### Quick Update Script

Create `scripts/manual_update.sh`:

```bash
#!/bin/bash
# Quick manual GTFS update

set -e

CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url 2>/dev/null)
ADMIN_TOKEN=$(cd terraform && terraform output -raw admin_token 2>/dev/null)

if [ -z "$CLOUD_RUN_URL" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo "Error: Could not get Cloud Run URL or admin token"
    echo "Make sure you've deployed with Terraform first"
    exit 1
fi

echo "Triggering manual GTFS update..."
echo "URL: $CLOUD_RUN_URL"
echo ""

HTTP_CODE=$(curl -s -o /tmp/update_response.json -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  "${CLOUD_RUN_URL}/api/admin/update-gtfs")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Update successful!"
    cat /tmp/update_response.json | python3 -m json.tool
else
    echo "✗ Update failed (HTTP $HTTP_CODE)"
    cat /tmp/update_response.json
    exit 1
fi
```

Make executable:
```bash
chmod +x scripts/manual_update.sh
```

Usage:
```bash
./scripts/manual_update.sh
```

### Check Update Status

Create `scripts/check_data.sh`:

```bash
#!/bin/bash
# Check current GTFS data status

CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url 2>/dev/null)

if [ -z "$CLOUD_RUN_URL" ]; then
    CLOUD_RUN_URL="http://localhost:8000"
fi

echo "Checking GTFS metadata..."
curl -s "${CLOUD_RUN_URL}/api/metadata" | python3 -m json.tool

echo ""
echo "Checking health..."
curl -s "${CLOUD_RUN_URL}/health" | python3 -m json.tool
```

---

## Monitoring Manual Updates

### View Update Logs

```bash
# Real-time logs
gcloud run services logs tail munich-transit-map \
  --region=europe-west3

# Filter for update-related logs
gcloud run services logs read munich-transit-map \
  --region=europe-west3 \
  --limit=100 | grep -i "update\|gtfs"
```

### Check Storage Metadata

```bash
BUCKET_NAME=$(cd terraform && terraform output -raw gtfs_bucket_name)

# View metadata file
gsutil cat gs://${BUCKET_NAME}/metadata.json | python3 -m json.tool

# List all files
gsutil ls -lh gs://${BUCKET_NAME}/
```

---

## Best Practices for Manual Updates

### 1. Update During Low Traffic

Schedule manual updates during off-peak hours:
- Late night (2-4 AM)
- Weekend mornings

### 2. Verify Before Update

Check if new data is actually available:

```bash
# Download current GTFS
curl -I https://www.mvv-muenchen.de/fileadmin/mediapool/02-Fahrplanauskunft/03-Downloads/openData/gesamt_gtfs.zip

# Check Last-Modified header
```

### 3. Test Locally First

```bash
# Test update locally before triggering on production
python scripts/init_data.py

# Verify graphs were built successfully
ls -lh static/data/graphs/
```

### 4. Monitor After Update

```bash
# Check application health after update
CLOUD_RUN_URL=$(cd terraform && terraform output -raw cloud_run_url)
curl "${CLOUD_RUN_URL}/health"

# Verify new metadata
curl "${CLOUD_RUN_URL}/api/metadata"
```

### 5. Rollback Plan

If update fails, you can:

**Option A: Keep old data**
- Cloud Run will continue using existing data
- Graphs already in memory stay valid

**Option B: Re-deploy previous version**
```bash
# List previous images
gcloud container images list-tags \
  europe-west3-docker.pkg.dev/PROJECT_ID/munich-transit-map/munich-transit-map

# Deploy specific version
gcloud run deploy munich-transit-map \
  --image=europe-west3-docker.pkg.dev/PROJECT_ID/munich-transit-map/munich-transit-map:COMMIT_SHA \
  --region=europe-west3
```

---

## Notification Setup (Optional)

Get notified when updates complete:

### Email Notification

Add to your update script:

```bash
# After update completes
if [ "$HTTP_CODE" = "200" ]; then
    echo "GTFS update completed at $(date)" | \
      mail -s "Munich Transit Map - Data Updated" your-email@example.com
fi
```

### Slack Notification

```bash
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

if [ "$HTTP_CODE" = "200" ]; then
    curl -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"✓ Munich Transit Map: GTFS data updated successfully\"}" \
      $SLACK_WEBHOOK
fi
```

### Cloud Monitoring Alert

Set up alert in GCP Console:
1. Go to Cloud Monitoring
2. Create alert policy
3. Condition: Cloud Run instance starts (indicates update restart)
4. Notification: Email or Slack

---

## Troubleshooting Manual Updates

### "403 Forbidden" Error

MVV server may block automated downloads. Solutions:

1. **Download manually** via browser:
   - Visit: https://www.mvv-muenchen.de/fahrplanauskunft/fuer-entwickler/opendata/
   - Download GTFS zip
   - Upload to GCS or local directory

2. **Use different User-Agent**:
   Edit `backend/data/gtfs_downloader.py`:
   ```python
   headers = {
       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
   }
   response = requests.get(url, headers=headers, stream=True)
   ```

### Update Takes Too Long

If update exceeds Cloud Run timeout (5 min):

1. **Increase timeout**:
   ```bash
   gcloud run services update munich-transit-map \
     --timeout=600 \
     --region=europe-west3
   ```

2. **Process locally and upload**:
   Use Option 3 above (local processing → GCS upload)

### Out of Memory

Increase memory allocation:

```hcl
# terraform/terraform.tfvars
cloud_run_memory = "4Gi"
```

Apply:
```bash
cd terraform && terraform apply
```

---

## Summary: Manual Update Workflows

### Workflow 1: On-Demand Updates (Keep Automation)

```bash
# Keep scheduler running, but trigger updates when you want
./scripts/manual_update.sh
```

**Use case**: Want daily automation but also update when new data available

### Workflow 2: Manual-Only Updates

```bash
# Disable scheduler
gcloud scheduler jobs pause munich-transit-map-update --location=europe-west3

# Update when needed
./scripts/manual_update.sh
```

**Use case**: Full control, no automatic updates

### Workflow 3: Local Processing

```bash
# Process locally
python scripts/init_data.py

# Upload to GCS
gsutil rsync -r static/data/ gs://YOUR_BUCKET/

# Restart Cloud Run
gcloud run services update munich-transit-map --region=europe-west3
```

**Use case**: Complex processing, slow Cloud Run, or testing

---

## Quick Reference

| Task | Command |
|------|---------|
| Manual update (GCP) | `./scripts/manual_update.sh` |
| Manual update (local) | `python scripts/init_data.py` |
| Pause scheduler | `gcloud scheduler jobs pause munich-transit-map-update --location=europe-west3` |
| Resume scheduler | `gcloud scheduler jobs resume munich-transit-map-update --location=europe-west3` |
| Delete scheduler | `gcloud scheduler jobs delete munich-transit-map-update --location=europe-west3` |
| Check data status | `curl ${CLOUD_RUN_URL}/api/metadata` |
| View update logs | `gcloud run services logs tail munich-transit-map --region=europe-west3` |

---

**Need help?** Open an issue: https://github.com/JuMaD/MVV_Analytics/issues
