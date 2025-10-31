# Quick Start Deployment Guide

Quick reference for deploying Nursingpod application.

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set up Google Cloud SDK
gcloud auth login
gcloud config set project sanaths-projects
```

## Option 1: Docker (Local Testing)

```bash
# Build image
docker build -t nursingpod-app .

# Run container
docker run -p 8080:8080 \
  -e GOOGLE_CLIENT_ID=your-id \
  -e GOOGLE_CLIENT_SECRET=your-secret \
  -e REDIRECT_URI=http://localhost:8080/callback \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  nursingpod-app
```

Or use docker-compose:

```bash
# Create .env file with your variables
docker-compose up
```

## Option 2: Google Cloud Run (Recommended for Production)

### One-Command Deploy (Using Makefile)

```bash
# PROJECT_ID is already set in Makefile to sanaths-projects
export PROJECT_ID=sanaths-projects  # Optional: override if needed
make setup-project
make deploy-cloudrun
```

### Manual Deploy

```bash
# 1. Set up secrets
cd cloudrun
./setup-secrets.sh

# 2. Build and deploy
cd ..
docker build -t gcr.io/sanaths-projects/nursingpod-app .
docker push gcr.io/sanaths-projects/nursingpod-app
./cloudrun/deploy.sh
```

### Get Service URL

```bash
gcloud run services describe nursingpod-app \
  --region us-central1 \
  --format 'value(status.url)'
```

**Important:** Update OAuth redirect URI in Google Cloud Console to:
`https://YOUR_SERVICE_URL/callback`

## Option 3: Kubernetes (GKE)

```bash
# 1. Create cluster
gcloud container clusters create nursingpod-cluster \
  --num-nodes=3 \
  --region=us-central1

# 2. Get credentials
gcloud container clusters get-credentials nursingpod-cluster --region=us-central1

# 3. Create secrets
kubectl create secret generic nursingpod-secrets \
  --from-literal=google-client-id='YOUR_ID' \
  --from-literal=google-client-secret='YOUR_SECRET' \
  --from-literal=secret-key='YOUR_SECRET_KEY'

# 4. k8s/*.yaml files are already configured with project ID
# 5. Deploy
kubectl apply -f k8s/
```

## Environment Variables Quick Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | Required |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | Required |
| `REDIRECT_URI` | OAuth callback URL | `https://your-domain.com/callback` |
| `SECRET_KEY` | Flask session secret | Generate with `openssl rand -hex 32` |
| `ALLOWED_DOMAIN` | Allowed email domain | `@cloudphysician.net` |
| `PORT` | Server port | `8080` (default) |
| `FLASK_ENV` | Environment mode | `production` or `development` |

## Common Commands

### Docker
```bash
docker build -t nursingpod-app .
docker run -p 8080:8080 nursingpod-app
docker-compose up -d
```

### Cloud Run
```bash
gcloud run deploy nursingpod-app --image gcr.io/sanaths-projects/nursingpod-app
gcloud run services logs read nursingpod-app --region us-central1
```

### Kubernetes
```bash
kubectl get pods
kubectl logs <pod-name>
kubectl rollout restart deployment/nursingpod-app
```

## Troubleshooting

1. **OAuth errors**: Check redirect URI matches in Google Cloud Console
2. **BigQuery errors**: Verify service account has BigQuery permissions
3. **Image pull errors**: Run `gcloud auth configure-docker`
4. **Port conflicts**: Change PORT environment variable

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

