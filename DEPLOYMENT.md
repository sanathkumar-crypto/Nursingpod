# Deployment Guide

This guide explains how to deploy the Nursingpod Flask application using Docker, Kubernetes, and Google Cloud Run.

## Prerequisites

- Docker installed and running
- Google Cloud SDK (gcloud) installed and configured
- kubectl installed (for Kubernetes deployment)
- Access to Google Cloud Platform with appropriate permissions
- BigQuery access configured

## Environment Variables

The application requires the following environment variables:

- `GOOGLE_CLIENT_ID`: Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth Client Secret
- `REDIRECT_URI`: OAuth redirect URI (must match Google Cloud Console configuration)
- `SECRET_KEY`: Flask secret key for session encryption
- `ALLOWED_DOMAIN`: Allowed email domain (default: `@cloudphysician.net`)
- `PORT`: Server port (default: 8080)
- `FLASK_ENV`: Environment mode (`development` or `production`)

## 1. Docker Deployment

### Build the Docker Image

```bash
# Use --network=host to work around DNS issues
docker build --network=host -t nursingpod-app:latest .
```

### Run Locally with Docker

```bash
docker run -p 8080:8080 \
  -e GOOGLE_CLIENT_ID=your-client-id \
  -e GOOGLE_CLIENT_SECRET=your-client-secret \
  -e REDIRECT_URI=http://localhost:8080/callback \
  -e SECRET_KEY=your-secret-key \
  -e GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json \
  -v /path/to/key.json:/app/gcloud-key.json:ro \
  nursingpod-app:latest
```

### Using Docker Compose

1. Create a `.env` file with your environment variables:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
REDIRECT_URI=http://localhost:8080/callback
SECRET_KEY=your-secret-key
GOOGLE_APPLICATION_CREDENTIALS=./gcloud-key.json
```

2. Run with docker-compose:

```bash
docker-compose up -d
```

The application will be available at `http://localhost:8080`.

## 2. Google Cloud Run Deployment

Cloud Run is a fully managed serverless platform that automatically scales your application.

### Step 1: Set Up Google Cloud Project

```bash
# Set your project ID
export PROJECT_ID=sanaths-projects
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Step 2: Create Service Account

```bash
# Create service account for the application
gcloud iam service-accounts create nursingpod-sa \
  --display-name="Nursingpod Service Account"

# Grant BigQuery access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:nursingpod-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:nursingpod-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### Step 3: Set Up Secrets

Run the setup script:

```bash
cd cloudrun
export PROJECT_ID=your-gcp-project-id
./setup-secrets.sh
```

Or manually create secrets:

```bash
# Create secrets in Secret Manager
echo -n "your-google-client-id" | gcloud secrets create google-client-id \
  --data-file=- --replication-policy="automatic"

echo -n "your-google-client-secret" | gcloud secrets create google-client-secret \
  --data-file=- --replication-policy="automatic"

echo -n "$(openssl rand -hex 32)" | gcloud secrets create secret-key \
  --data-file=- --replication-policy="automatic"
```

### Step 4: Build and Push Image

```bash
# Build the image
docker build -t gcr.io/${PROJECT_ID}/nursingpod-app:latest .

# Push to Google Container Registry
docker push gcr.io/${PROJECT_ID}/nursingpod-app:latest
```

### Step 5: Deploy to Cloud Run

Using the deployment script:

```bash
cd cloudrun
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
./deploy.sh
```

Or manually deploy:

```bash
gcloud run deploy nursingpod-app \
  --image gcr.io/${PROJECT_ID}/nursingpod-app:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars FLASK_ENV=production,PORT=8080,ALLOWED_DOMAIN=@cloudphysician.net \
  --set-secrets GOOGLE_CLIENT_ID=google-client-id:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,SECRET_KEY=secret-key:latest \
  --service-account nursingpod-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

### Step 6: Update OAuth Redirect URI

After deployment, get your service URL:

```bash
gcloud run services describe nursingpod-app \
  --region us-central1 \
  --format 'value(status.url)'
```

Update the OAuth redirect URI in Google Cloud Console to:
`https://your-service-url.run.app/callback`

## 3. Kubernetes Deployment (GKE)

### Step 1: Create GKE Cluster

```bash
gcloud container clusters create nursingpod-cluster \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --region=us-central1

# Get credentials
gcloud container clusters get-credentials nursingpod-cluster --region=us-central1
```

### Step 2: Enable Workload Identity

```bash
# Enable Workload Identity
gcloud container clusters update nursingpod-cluster \
  --workload-pool=${PROJECT_ID}.svc.id.goog \
  --region=us-central1

# Create Kubernetes service account
kubectl create serviceaccount nursingpod-sa --namespace default

# Bind to Google service account
gcloud iam service-accounts add-iam-policy-binding \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/nursingpod-sa]" \
  nursingpod-sa@${PROJECT_ID}.iam.gserviceaccount.com

kubectl annotate serviceaccount nursingpod-sa \
  iam.gke.io/gcp-service-account=nursingpod-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

### Step 3: Configure Secrets

```bash
# Create Kubernetes secrets
kubectl create secret generic nursingpod-secrets \
  --from-literal=google-client-id='your-client-id' \
  --from-literal=google-client-secret='your-client-secret' \
  --from-literal=secret-key='your-secret-key'
```

### Step 4: Update Configuration

Edit `k8s/configmap.yaml` and `k8s/deployment.yaml`:

- Replace `PROJECT_ID` with your actual GCP project ID
- Update `redirect-uri` in configmap with your domain
- Update image name in deployment

### Step 5: Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Optional: Set up ingress
kubectl apply -f k8s/ingress.yaml
```

### Step 6: Verify Deployment

```bash
# Check pods
kubectl get pods

# Check services
kubectl get services

# Get external IP
kubectl get ingress nursingpod-ingress
```

## Building Images for Different Platforms

### Build for Cloud Run / GKE

```bash
docker build -t gcr.io/${PROJECT_ID}/nursingpod-app:latest .
docker push gcr.io/${PROJECT_ID}/nursingpod-app:latest
```

### Using Cloud Build

```bash
gcloud builds submit --tag gcr.io/${PROJECT_ID}/nursingpod-app:latest
```

## Updating the Deployment

### Update Docker Image

1. Rebuild and push the new image:

```bash
docker build -t gcr.io/${PROJECT_ID}/nursingpod-app:latest .
docker push gcr.io/${PROJECT_ID}/nursingpod-app:latest
```

2. For Cloud Run, redeploy (it will pull the latest image):

```bash
gcloud run deploy nursingpod-app \
  --image gcr.io/${PROJECT_ID}/nursingpod-app:latest \
  --region us-central1
```

3. For Kubernetes, update the deployment:

```bash
kubectl rollout restart deployment/nursingpod-app
```

## Monitoring and Logs

### Cloud Run Logs

```bash
gcloud run services logs read nursingpod-app --region us-central1
```

### Kubernetes Logs

```bash
# Get pod name
kubectl get pods

# View logs
kubectl logs <pod-name>
```

## Troubleshooting

### Common Issues

1. **OAuth redirect URI mismatch**
   - Ensure the redirect URI in Google Cloud Console matches your deployment URL
   - Format: `https://your-domain.com/callback`

2. **BigQuery access denied**
   - Verify service account has BigQuery permissions
   - Check workload identity binding (for Kubernetes)

3. **Session cookies not working**
   - Ensure `SESSION_COOKIE_SECURE` is set correctly for HTTPS
   - Verify cookie domain settings

4. **Image pull errors**
   - Verify image exists in GCR: `gcloud container images list`
   - Check service account permissions

5. **Memory/CPU limits**
   - Adjust resource limits in deployment files if application is being killed

## Security Best Practices

1. **Never commit secrets** - Use Secret Manager or Kubernetes secrets
2. **Use HTTPS** - Always use HTTPS in production
3. **Regular updates** - Keep dependencies updated
4. **Service accounts** - Use least privilege principle
5. **Network policies** - Implement network policies in Kubernetes if needed

## Cost Optimization

### Cloud Run
- Set `--min-instances 0` to scale to zero when not in use
- Adjust `--max-instances` based on expected load
- Use appropriate memory allocation

### Kubernetes
- Use node autoscaling
- Right-size resource requests and limits
- Consider spot instances for non-critical workloads

## Production Checklist

- [ ] Environment variables configured
- [ ] Secrets stored securely (Secret Manager/Kubernetes secrets)
- [ ] HTTPS enabled
- [ ] OAuth redirect URI updated in Google Cloud Console
- [ ] Service account permissions configured
- [ ] BigQuery access verified
- [ ] Monitoring and logging set up
- [ ] Resource limits configured appropriately
- [ ] Health checks configured
- [ ] Backup and disaster recovery plan
- [ ] Domain/DNS configured
- [ ] SSL certificate configured (for custom domain)

## Support

For issues or questions, please refer to:
- Google Cloud Run documentation: https://cloud.google.com/run/docs
- Kubernetes documentation: https://kubernetes.io/docs/
- Flask documentation: https://flask.palletsprojects.com/

