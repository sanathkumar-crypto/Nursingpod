# BigQuery Cross-Project Permissions Setup

## Issue
Your application queries BigQuery tables in project: `prod-tech-project1-bv479-zo027`
But your Cloud Run service account is in project: `sanaths-projects`

The service account needs access to the datasets in the other project.

## Service Account That Needs Access
```
sanaths-projects@sanaths-projects.iam.gserviceaccount.com
```

## Required Permissions

The service account needs these roles on project `prod-tech-project1-bv479-zo027`:

### Option 1: Project-Level Permissions (Easiest)
```bash
# Grant BigQuery Data Viewer (to query tables)
gcloud projects add-iam-policy-binding prod-tech-project1-bv479-zo027 \
  --member="serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# Grant BigQuery Job User (to create query jobs)
gcloud projects add-iam-policy-binding prod-tech-project1-bv479-zo027 \
  --member="serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### Option 2: Dataset-Level Permissions (More Secure)
If you prefer to grant access only to specific datasets:

```bash
# Grant access to gsheet_data dataset
bq add-iam-policy-binding prod-tech-project1-bv479-zo027:gsheet_data \
  --member="serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# Grant access to mongodb dataset
bq add-iam-policy-binding prod-tech-project1-bv479-zo027:mongodb \
  --member="serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# Grant job user permission at project level (required for all queries)
gcloud projects add-iam-policy-binding prod-tech-project1-bv479-zo027 \
  --member="serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

## Datasets and Tables Required

Your application queries these datasets:

### gsheet_data dataset:
- `nursing_pod_quality_data`
- `impact_cases`

### mongodb dataset:
- `camera_annotation_events`

## Who Can Grant These Permissions?

- Project Owner or Editor of `prod-tech-project1-bv479-zo027`
- Or BigQuery Admin with permission to manage IAM

## Quick Test

After granting permissions, test with:

```bash
# Test query access (run from a machine with gcloud auth)
bq query --use_legacy_sql=false \
  --project_id=prod-tech-project1-bv479-zo027 \
  "SELECT COUNT(*) as count FROM \`prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data\` LIMIT 1"
```

## Alternative Solution

If you cannot grant cross-project access, you could:
1. Copy the data to your project (`sanaths-projects`)
2. Create a dataset in your project and sync the data
3. Update the application to query from your project instead

But the easiest solution is to grant the service account access to the source project.

