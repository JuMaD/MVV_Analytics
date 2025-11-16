#!/bin/bash
# Manual GTFS data update script
# Triggers the update endpoint on your deployed Cloud Run service

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Munich Transit Map - Manual GTFS Update${NC}"
echo ""

# Get Cloud Run URL and admin token from Terraform
if [ -f "terraform/terraform.tfstate" ]; then
    cd terraform
    CLOUD_RUN_URL=$(terraform output -raw cloud_run_url 2>/dev/null)
    ADMIN_TOKEN=$(terraform output -raw admin_token 2>/dev/null)
    cd ..
else
    echo -e "${RED}Error: terraform.tfstate not found${NC}"
    echo "Have you deployed with ./scripts/setup.sh yet?"
    exit 1
fi

if [ -z "$CLOUD_RUN_URL" ] || [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}Error: Could not get Cloud Run URL or admin token${NC}"
    echo "Make sure you've deployed with Terraform first"
    exit 1
fi

echo -e "${GREEN}Cloud Run URL:${NC} $CLOUD_RUN_URL"
echo ""

# Trigger update
echo -e "${YELLOW}Triggering GTFS data update...${NC}"
echo "This may take 5-10 minutes..."
echo ""

HTTP_CODE=$(curl -s -o /tmp/update_response.json -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  "${CLOUD_RUN_URL}/api/admin/update-gtfs")

echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Update successful!${NC}"
    echo ""
    cat /tmp/update_response.json | python3 -m json.tool 2>/dev/null || cat /tmp/update_response.json
    echo ""
    echo -e "${GREEN}GTFS data has been updated${NC}"
else
    echo -e "${RED}✗ Update failed (HTTP $HTTP_CODE)${NC}"
    echo ""
    cat /tmp/update_response.json
    exit 1
fi
