#!/bin/bash
# Script to grant BigQuery permissions to service account
# Run this if you have Owner/Editor access to prod-tech-project1-bv479-zo027

PROJECT_ID="prod-tech-project1-bv479-zo027"
SERVICE_ACCOUNT="sanaths-projects@sanaths-projects.iam.gserviceaccount.com"

echo "Granting BigQuery permissions to service account..."
echo "Project: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT"
echo ""

# Grant BigQuery Data Viewer role
echo "Granting BigQuery Data Viewer role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/bigquery.dataViewer"

# Grant BigQuery Job User role
echo ""
echo "Granting BigQuery Job User role..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/bigquery.jobUser"

echo ""
echo "✅ Permissions granted!"
echo ""
echo "The service account can now query BigQuery tables in project: $PROJECT_ID"



