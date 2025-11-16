#!/bin/bash
# Deploy script for Munich Transit Reachability Map
# Use this script to deploy updates to the application

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Munich Transit Map - Deployment${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Get project ID from terraform or environment
if [ -f "terraform/terraform.tfvars" ]; then
    PROJECT_ID=$(grep project_id terraform/terraform.tfvars | cut -d'"' -f2)
else
    PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Could not determine project ID${NC}"
    echo "Set GCP_PROJECT_ID environment variable or run setup.sh first"
    exit 1
fi

REGION=${GCP_REGION:-"europe-west3"}
APP_NAME=${APP_NAME:-"munich-transit-map"}
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}/${APP_NAME}"

echo -e "${GREEN}Project ID:${NC} $PROJECT_ID"
echo -e "${GREEN}Region:${NC} $REGION"
echo -e "${GREEN}App Name:${NC} $APP_NAME"
echo ""

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t "${IMAGE_NAME}:latest" -t "${IMAGE_NAME}:$(git rev-parse --short HEAD)" .
echo -e "${GREEN}✓ Docker image built${NC}"
echo ""

# Push to Artifact Registry
echo -e "${YELLOW}Pushing to Artifact Registry...${NC}"
docker push "${IMAGE_NAME}:latest"
docker push "${IMAGE_NAME}:$(git rev-parse --short HEAD)"
echo -e "${GREEN}✓ Image pushed${NC}"
echo ""

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy "${APP_NAME}" \
  --image="${IMAGE_NAME}:latest" \
  --platform=managed \
  --region="${REGION}" \
  --quiet

echo -e "${GREEN}✓ Deployed to Cloud Run${NC}"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe "${APP_NAME}" \
  --region="${REGION}" \
  --format='value(status.url)')

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Deployment Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Application URL:${NC}"
echo -e "  ${SERVICE_URL}"
echo ""
echo -e "${GREEN}Health Check:${NC}"
curl -s "${SERVICE_URL}/health" | python3 -m json.tool 2>/dev/null || curl -s "${SERVICE_URL}/health"
echo ""
echo ""
