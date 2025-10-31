# Why It Works Locally But Not in Production

## The Difference: Authentication Method

### Localhost (Development) ✅
```
Your Computer → bigquery.Client() → Uses YOUR user credentials
                                  → sanath.kumar@cloudphysician.net
                                  → Has access to prod-tech-project amojects tables
                                  → ✅ WORKS
```

**What credentials are used:**
- Application Default Credentials (ADC)
- Your user account: `sanath.kumar@cloudphysician.net`
- Authenticated via: `gcloud auth application-default login`
- Your user account has access to BigQuery tables in `prod-tech-project1-bv479-zo027`

### Production (Cloud Run) ❌
```
Cloud Run → bigquery.Client() → Uses SERVICE ACCOUNT credentials
                              → sanaths-projects@sanaths-projects.iam.gserviceaccount.com
                              → Does NOT have access to other project's tables
                              → ❌ FAILS
```

**What credentials are used:**
- Service Account: `sanaths-projects@sanaths-projects.iam.gserviceaccount.com`
- Cloud Run automatically uses the service account assigned to the service
- This service account only has permissions in `sanaths-projects`, not in `prod-tech-project1-bv479-zo027`

## Why This Happens

When you call `bigquery.Client()` without explicit credentials:

```python
client = bigquery.Client()  # Uses default credentials
```

The BigQuery client library follows this order:
1. **Check for explicit credentials** (not provided)
2. **Check for GOOGLE_APPLICATION_CREDENTIALS** (environment variable pointing to key file)
3. **Use Application Default Credentials** (ADC):
   - **Local machine**: Uses your user credentials from `gcloud auth application-default login`
   - **Cloud Run/GCE/GKE**: Uses the service account attached to the compute resource

## Solution

Grant the service account access to the other project:

```bash
# Grant access to query tables in the other project
gcloud projects add-iam-policy-binding prod-tech-project1-bv479-zo027 \
  --member="serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding prod-tech-project1-bv479-zo027 \
  --member="serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

Or use Google Cloud Console:
https://console.cloud.google.com/iam-admin/iam?project=prod-tech-project1-bv479-zo027

## Summary

| Environment | Credentials Used | Has Access? |
|------------|------------------|-------------|
| **Localhost** | `sanath.kumar@cloudphysician.net` (your user) | ✅ Yes |
| **Cloud Run** | `sanaths-projects@sanaths-projects.iam.gserviceaccount.com` | ❌ No (needs grant) |

Once you grant the service account access, it will work the same in production as it does locally!



