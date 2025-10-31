# Deployment Checklist

## Pre-Deployment

### ✅ Completed
- [x] Project ID configured: `sanaths-projects`
- [x] Environment variables set in `.env`
- [x] Docker configuration created
- [x] Kubernetes manifests created
- [x] Cloud Run deployment scripts created
- [x] Production secret key generated: `d1403ef0dff81f586e62d21981ed08c1aead3171101b4869897c6874d7cafd51`

### 📋 Before Deploying

1. **Update Secret Key (if desired)**
   - Current key is in `PRODUCTION_SECRET_KEY.txt`
   - Update `.env` if you want to use it locally
   - Add to Secret Manager during Cloud Run setup

2. **Verify OAuth Settings**
   - Your current redirect URI: `http://localhost:5000/callback`
   - After Cloud Run deployment, add production URL to Google Cloud Console
   - Format: `https://YOUR_SERVICE_URL/callback`

3. **Create Service Account** (for BigQuery access)
   ```bash
   gcloud iam service-accounts create nursingpod-sa \
     --display-name="Nursingpod Service Account"
   
   gcloud projects add-iam-policy-binding sanaths-projects \
     --member="serviceAccount:nursingpod-sa@sanaths-projects.iam.gserviceaccount.com" \
     --role="roles/bigquery.user"
   
   gcloud projects add-iam-policy-binding sanaths-projects \
     --member="serviceAccount:nursingpod-sa@sanaths-projects.iam.gserviceaccount.com" \
     --role="roles/bigquery.jobUser"
   ```

## Deployment Steps

### Option 1: Cloud Run (Recommended)

```bash
# 1. Enable required APIs
make setup-project

# 2. Set up secrets
cd cloudrun
./setup-secrets.sh
# When prompted, enter:
# - Google Client ID: 1032805148357-ud0632ctk62nul4tdhcfhdckm2ib5s3k.apps.googleusercontent.com
# - Google Client Secret: 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
# - Secret Key: d1403ef0dff81f586e62d21981ed08c1aead3171101b4869897c6874d7cafd51

# 3. Deploy
cd ..
make deploy-cloudrun

# 4. Get service URL
gcloud run services describe nursingpod-app \
  --region us-central1 \
  --format 'value(status.url)'

# 5. Update OAuth redirect URI in Google Cloud Console:
#    https://console.cloud.google.com/apis/credentials
#    Add: https://YOUR_SERVICE_URL/callback
```

### Option 2: Kubernetes (GKE)

```bash
# 1. Create cluster (if needed)
gcloud container clusters create nursingpod-cluster \
  --num-nodes=3 \
  --region=us-central1

# 2. Get credentials
gcloud container clusters get-credentials nursingpod-cluster --region=us-central1

# 3. Create secrets
kubectl create secret generic nursingpod-secrets \
  --from-literal=google-client-id='1032805148357-ud0632ctk62nul4tdhcfhdckm2ib5s3k.apps.googleusercontent.com' \
  --from-literal=google-client-secret='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' \
  --from-literal=secret-key='d1403ef0dff81f586e62d21981ed08c1aead3171101b4869897c6874d7cafd51'

# 4. Update configmap with your domain
# Edit k8s/configmap.yaml - update redirect-uri

# 5. Build and push image
make build push

# 6. Deploy
kubectl apply -f k8s/
```

### Option 3: Docker (Local/Testing)

```bash
# 1. Update .env with production secret key (optional)
# Edit .env and update SECRET_KEY

# 2. Build and run
docker-compose up -d

# Or manually:
docker build -t nursingpod-app .
docker run -p 8080:8080 \
  -e GOOGLE_CLIENT_ID=1032805148357-ud0632ctk62nul4tdhcfhdckm2ib5s3k.apps.googleusercontent.com \
  -e GOOGLE_CLIENT_SECRET=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 \
  -e REDIRECT_URI=http://localhost:8080/callback \
  -e SECRET_KEY=d1403ef0dff81f586e62d21981ed08c1aead3171101b4869897c6874d7cafd51 \
  nursingpod-app
```

## Post-Deployment

- [ ] Verify application is accessible
- [ ] Test OAuth login
- [ ] Update OAuth redirect URI in Google Cloud Console
- [ ] Verify BigQuery connection
- [ ] Check logs for any errors
- [ ] Set up monitoring/alerting (optional)
- [ ] Configure custom domain (optional)

## Current Configuration

- **Project ID:** `sanaths-projects`
- **Google Client ID:** `1032805148357-ud0632ctk62nul4tdhcfhdckm2ib5s3k.apps.googleusercontent.com`
- **Secret Key:** `d1403ef0dff81f586e62d21981ed08c1aead3171101b4869897c6874d7cafd51`
- **Allowed Domain:** `@cloudphysician.net`
- **Default Port:** `8080` (production), `5000` (local dev)

## Troubleshooting

If you encounter issues:
1. Check logs: `gcloud run services logs read nursingpod-app --region us-central1`
2. Verify secrets are set correctly
3. Check OAuth redirect URI matches exactly
4. Verify service account has BigQuery permissions
5. Check network/firewall rules (for Kubernetes)




