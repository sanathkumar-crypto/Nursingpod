#!/bin/bash
# Script to create secrets in Google Cloud Secret Manager for Cloud Run

set -e

PROJECT_ID=${PROJECT_ID:-"sanaths-projects"}

echo "Setting up secrets in Google Cloud Secret Manager..."
echo "Make sure you have the required values ready."
echo ""

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=${PROJECT_ID}

# Create secrets
echo ""
echo "Creating secrets (you will be prompted to enter values)..."
echo ""

echo "Creating google-client-id secret..."
echo -n "Enter Google Client ID: "
read CLIENT_ID
echo -n "${CLIENT_ID}" | gcloud secrets create google-client-id \
  --data-file=- \
  --project=${PROJECT_ID} \
  --replication-policy="automatic" || \
echo -n "${CLIENT_ID}" | gcloud secrets versions add google-client-id \
  --data-file=- \
  --project=${PROJECT_ID}

echo ""
echo "Creating google-client-secret secret..."
echo -n "Enter Google Client Secret: "
read CLIENT_SECRET
echo -n "${CLIENT_SECRET}" | gcloud secrets create google-client-secret \
  --data-file=- \
  --project=${PROJECT_ID} \
  --replication-policy="automatic" || \
echo -n "${CLIENT_SECRET}" | gcloud secrets versions add google-client-secret \
  --data-file=- \
  --project=${PROJECT_ID}

echo ""
echo "Creating secret-key secret..."
echo -n "Enter Secret Key (or press Enter to generate): "
read SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
  SECRET_KEY=$(openssl rand -hex 32)
  echo "Generated Secret Key: ${SECRET_KEY}"
fi
echo -n "${SECRET_KEY}" | gcloud secrets create secret-key \
  --data-file=- \
  --project=${PROJECT_ID} \
  --replication-policy="automatic" || \
echo -n "${SECRET_KEY}" | gcloud secrets versions add secret-key \
  --data-file=- \
  --project=${PROJECT_ID}

echo ""
echo "Granting Cloud Run service account access to secrets..."
SERVICE_ACCOUNT="sanaths-projects@sanaths-projects.iam.gserviceaccount.com"

gcloud secrets add-iam-policy-binding google-client-id \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=${PROJECT_ID}

gcloud secrets add-iam-policy-binding google-client-secret \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=${PROJECT_ID}

gcloud secrets add-iam-policy-binding secret-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=${PROJECT_ID}

echo ""
echo "✅ Secrets setup complete!"
echo ""
echo "Created secrets:"
echo "  - google-client-id"
echo "  - google-client-secret"
echo "  - secret-key"

