#!/bin/bash
# One-time setup script for Munich Transit Reachability Map on GCP
# This script sets up the entire infrastructure and deploys the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Munich Transit Reachability Map - GCP Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}✗ gcloud CLI not found${NC}"
    echo "  Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo -e "${GREEN}✓ gcloud CLI installed${NC}"

# Check terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}✗ Terraform not found${NC}"
    echo "  Install from: https://www.terraform.io/downloads"
    exit 1
fi
echo -e "${GREEN}✓ Terraform installed${NC}"

# Check docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "  Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

echo ""

# Get project ID
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${YELLOW}Enter your GCP Project ID:${NC}"
    read -r GCP_PROJECT_ID
fi

if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    exit 1
fi

echo -e "${GREEN}Using Project ID: ${GCP_PROJECT_ID}${NC}"
echo ""

# Set gcloud project
echo -e "${YELLOW}Setting gcloud project...${NC}"
gcloud config set project "$GCP_PROJECT_ID"

# Authenticate
echo -e "${YELLOW}Checking authentication...${NC}"
if ! gcloud auth application-default print-access-token &> /dev/null; then
    echo -e "${YELLOW}Setting up application default credentials...${NC}"
    gcloud auth application-default login
fi
echo -e "${GREEN}✓ Authenticated${NC}"
echo ""

# Configure Docker for Artifact Registry
echo -e "${YELLOW}Configuring Docker for Artifact Registry...${NC}"
gcloud auth configure-docker europe-west3-docker.pkg.dev --quiet
echo -e "${GREEN}✓ Docker configured${NC}"
echo ""

# Check if terraform.tfvars exists
if [ ! -f "terraform/terraform.tfvars" ]; then
    echo -e "${YELLOW}Creating terraform.tfvars...${NC}"

    # Generate admin token
    ADMIN_TOKEN=$(openssl rand -base64 32 | tr -d '\n')

    cat > terraform/terraform.tfvars <<EOF
# Terraform Variables for Munich Transit Map
project_id = "$GCP_PROJECT_ID"
region = "europe-west3"
admin_token = "$ADMIN_TOKEN"

# Optional customizations
# cloud_run_memory = "2Gi"
# cloud_run_cpu = "2"
# update_schedule = "0 6 * * *"
EOF

    echo -e "${GREEN}✓ Created terraform.tfvars${NC}"
    echo -e "${YELLOW}Admin token: ${ADMIN_TOKEN}${NC}"
    echo -e "${YELLOW}(Saved to terraform/terraform.tfvars)${NC}"
    echo ""
else
    echo -e "${GREEN}✓ terraform.tfvars already exists${NC}"
    echo ""
fi

# Initialize Terraform
echo -e "${YELLOW}Initializing Terraform...${NC}"
cd terraform
terraform init
echo -e "${GREEN}✓ Terraform initialized${NC}"
echo ""

# Terraform plan
echo -e "${YELLOW}Creating Terraform plan...${NC}"
terraform plan -out=tfplan
echo ""

# Ask for confirmation
echo -e "${YELLOW}Review the plan above.${NC}"
echo -e "${YELLOW}Deploy infrastructure? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

# Apply Terraform
echo ""
echo -e "${YELLOW}Deploying infrastructure...${NC}"
terraform apply tfplan
echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# Get outputs
CLOUD_RUN_URL=$(terraform output -raw cloud_run_url)
ADMIN_TOKEN=$(terraform output -raw admin_token 2>/dev/null || grep admin_token terraform.tfvars | cut -d'"' -f2)

cd ..

# Build and deploy application
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Building and Deploying Application${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

./scripts/deploy.sh

# Initialize GTFS data
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Initializing GTFS Data${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Downloading and processing GTFS data...${NC}"
echo -e "${YELLOW}This may take several minutes...${NC}"

HTTP_CODE=$(curl -s -o /tmp/update_response.json -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "${CLOUD_RUN_URL}/api/admin/update-gtfs")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ GTFS data initialized${NC}"
    cat /tmp/update_response.json | python3 -m json.tool 2>/dev/null || cat /tmp/update_response.json
else
    echo -e "${RED}✗ Failed to initialize GTFS data (HTTP $HTTP_CODE)${NC}"
    cat /tmp/update_response.json
    echo ""
    echo -e "${YELLOW}You can retry manually:${NC}"
    echo -e "curl -X POST -H \"Authorization: Bearer ${ADMIN_TOKEN}\" \\"
    echo -e "  ${CLOUD_RUN_URL}/api/admin/update-gtfs"
fi

# Final summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Setup Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Application URL:${NC}"
echo -e "  ${CLOUD_RUN_URL}"
echo ""
echo -e "${GREEN}Admin Token:${NC}"
echo -e "  ${ADMIN_TOKEN}"
echo ""
echo -e "${YELLOW}Save this token securely - you'll need it for manual updates${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Open the application in your browser"
echo "  2. Select a starting stop (e.g., Marienplatz)"
echo "  3. Click 'Calculate Reachability'"
echo "  4. Press 'Play' to watch the animation"
echo ""
echo -e "${GREEN}Monitoring:${NC}"
echo "  Cloud Run: https://console.cloud.google.com/run?project=${GCP_PROJECT_ID}"
echo "  Scheduler: https://console.cloud.google.com/cloudscheduler?project=${GCP_PROJECT_ID}"
echo ""
echo -e "${GREEN}Daily updates:${NC}"
echo "  Automatic at 6:00 AM CET via Cloud Scheduler"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
