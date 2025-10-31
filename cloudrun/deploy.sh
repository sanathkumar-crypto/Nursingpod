#!/bin/bash
# Cloud Run deployment script for Nursingpod application

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"sanaths-projects"}
SERVICE_NAME=${SERVICE_NAME:-"nursingpod-app"}
REGION=${REGION:-"us-central1"}
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Docker image...${NC}"
# Build from parent directory where Dockerfile is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"
docker build --network=host -t ${IMAGE_NAME}:latest .

echo -e "${GREEN}Pushing image to Google Container Registry...${NC}"
docker push ${IMAGE_NAME}:latest

echo -e "${GREEN}Deploying to Cloud Run...${NC}"
# Return to cloudrun directory for consistency
cd "$(dirname "$0")" || exit 1
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME}:latest \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-secrets GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,SECRET_KEY=secret-key:latest \
  --service-account sanaths-projects@sanaths-projects.iam.gserviceaccount.com

# Get the service URL and update REDIRECT_URI
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo -e "${GREEN}Updating REDIRECT_URI to: ${SERVICE_URL}/callback${NC}"
gcloud run services update ${SERVICE_NAME} \
  --region ${REGION} \
  --update-env-vars REDIRECT_URI=${SERVICE_URL}/callback,FLASK_ENV=production,ALLOWED_DOMAIN=@cloudphysician.net

echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${YELLOW}Service URL: ${SERVICE_URL}${NC}"
echo -e "${YELLOW}⚠️  IMPORTANT: Add this redirect URI to Google Cloud Console OAuth credentials:${NC}"
echo -e "${YELLOW}   ${SERVICE_URL}/callback${NC}"
echo ""
echo "Visit: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"

