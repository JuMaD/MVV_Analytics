#!/bin/bash
# Teardown script - destroy all GCP resources
# WARNING: This will delete everything!

set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo -e "${RED}  WARNING: This will destroy ALL infrastructure${NC}"
echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "This will delete:"
echo "  - Cloud Run service"
echo "  - Cloud Scheduler job"
echo "  - Storage buckets (including all GTFS data)"
echo "  - Artifact Registry repository (including all Docker images)"
echo "  - Service accounts"
echo ""
echo -e "${YELLOW}Are you SURE you want to continue? (type 'yes' to confirm)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Teardown cancelled"
    exit 0
fi

echo ""
echo -e "${YELLOW}Running terraform destroy...${NC}"
cd terraform
terraform destroy
cd ..

echo ""
echo -e "${RED}All resources have been destroyed${NC}"
