# Fix Google Cloud Authentication Issue

## Problem
You're authenticated as a service account (`daily-notifications-sa@sanaths-projects.iam.gserviceaccount.com`) which doesn't have permissions to enable APIs.

## Solution

You need to authenticate with your **personal Google Cloud account** (not a service account) that has Owner/Editor permissions on the project.

### Option 1: Switch to Your User Account (Recommended)

```bash
# List all authenticated accounts
gcloud auth list

# Login with your personal Google account
gcloud auth login

# Set your user account as the active account
gcloud config set account YOUR_EMAIL@gmail.com

# Verify the active account
gcloud config get-value account

# Now try enabling APIs again
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Option 2: If You Don't Have a User Account

If you only have a service account and can't enable APIs:
1. **Ask a project owner/admin** to enable the APIs for you
2. Or use the **Google Cloud Console** web UI:
   - Go to: https://console.cloud.google.com/
   - Navigate to: **APIs & Services** → **Library**
   - Search and enable:
     - Cloud Run API
     - Container Registry API
     - Secret Manager API

### Option 3: Use Application Default Credentials

For running the application, you can keep using service account, but for managing infrastructure, you need a user account:

```bash
# For application runtime (BigQuery access)
gcloud auth application-default login

# For managing APIs/services (requires user account)
gcloud auth login
```

## Verify Fix

After switching accounts:
```bash
gcloud config get-value account
# Should show: your-email@gmail.com (not a service account)
```

## Quick Fix Command

```bash
# Logout from service account
gcloud auth revoke daily-notifications-sa@sanaths-projects.iam.gserviceaccount.com

# Login with your personal account
gcloud auth login

# Set as default
gcloud config set account $(gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -v "@.*\.iam\.gserviceaccount\.com" | head -1)

# Now enable APIs
gcloud services enable run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com
```



