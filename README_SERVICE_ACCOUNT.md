# Google Cloud Service Account Key Setup

## Files Created

1. **gcloud-key.json** - Template with your project ID filled in
2. **gcloud-key-template.json** - Template with placeholders for all values

## How to Get the Service Account Key

### Option 1: Create New Service Account (Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select project: `sanaths-projects`
3. Navigate to **IAM & Admin** → **Service Accounts**
4. Click **Create Service Account**
5. Fill in:
   - **Name**: `nursingpod-sa`
   - **Description**: `Service account for Nursingpod application with BigQuery access`
6. Click **Create and Continue**
7. Add roles:
   - `BigQuery User`
   - `BigQuery Job User`
8. Click **Continue** → **Done**
9. Click on the created service account
10. Go to **Keys** tab
11. Click **Add Key** → **Create new key**
12. Choose **JSON** format
13. Download the key file
14. Replace the content of `gcloud-key.json` with the downloaded file

### Option 2: Use Existing Service Account

If you already have a service account:
1. Go to **IAM & Admin** → **Service Accounts**
2. Find your service account
3. Click on it → **Keys** tab
4. Click **Add Key** → **Create new key**
5. Choose **JSON** format
6. Download and replace `gcloud-key.json`

## Required Permissions

The service account needs these roles:
- `BigQuery User` - to query BigQuery datasets
- `BigQuery Job User` - to create and manage BigQuery jobs

## Security Notes

⚠️ **Important Security Guidelines:**

1. **Never commit this file to version control**
2. **Keep it secure** - anyone with this file can access your Google Cloud resources
3. **Use environment variables** in production instead of the file
4. **Rotate keys regularly**
5. **Delete unused keys**

## Using the Key

### For Local Development

```bash
# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcloud-key.json

# Or use with docker-compose
# The docker-compose.yml already references this file
```

### For Production

Instead of using the key file, use:
- **Cloud Run**: Workload Identity (recommended)
- **Kubernetes**: Workload Identity or mounted secrets
- **Compute Engine**: Default service account or attached service account

## File Structure

The JSON file should contain:
- `type`: "service_account"
- `project_id`: "sanaths-projects"
- `private_key_id`: Unique identifier for the key
- `private_key`: The actual private key (PEM format)
- `client_email`: Service account email
- `client_id`: OAuth2 client ID
- Various OAuth2 URLs (usually don't need to change)

## Troubleshooting

If you get authentication errors:
1. Verify the service account has the required permissions
2. Check that the JSON file is valid JSON
3. Ensure the file path is correct
4. Verify the project ID matches your actual project


