#!/bin/bash
# Check current GTFS data status

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Munich Transit Map - Data Status${NC}"
echo ""

# Try to get Cloud Run URL from Terraform
if [ -f "terraform/terraform.tfstate" ]; then
    cd terraform
    CLOUD_RUN_URL=$(terraform output -raw cloud_run_url 2>/dev/null)
    cd ..
fi

# Fallback to localhost if not deployed
if [ -z "$CLOUD_RUN_URL" ]; then
    CLOUD_RUN_URL="http://localhost:8000"
    echo -e "${YELLOW}Using local URL: $CLOUD_RUN_URL${NC}"
else
    echo -e "${GREEN}Using Cloud Run URL: $CLOUD_RUN_URL${NC}"
fi

echo ""

# Check metadata
echo -e "${YELLOW}GTFS Metadata:${NC}"
curl -s "${CLOUD_RUN_URL}/api/metadata" | python3 -m json.tool 2>/dev/null || curl -s "${CLOUD_RUN_URL}/api/metadata"

echo ""
echo ""

# Check health
echo -e "${YELLOW}Application Health:${NC}"
curl -s "${CLOUD_RUN_URL}/health" | python3 -m json.tool 2>/dev/null || curl -s "${CLOUD_RUN_URL}/health"

echo ""
