# Minimum Requirements for Nursingpod Deployment

## Core Application Requirements

### 1. **Runtime Environment**
- **Python**: 3.12+ (required for dependencies)
- **Memory**: 512MB minimum, 1GB recommended
- **CPU**: 1 vCPU minimum
- **Storage**: 1GB for application + dependencies
- **Network**: Internet access for Google APIs

### 2. **External Dependencies**
- **Google Cloud BigQuery**: Data source (required)
- **Google OAuth2**: Authentication (required)
- **Internet connectivity**: For Google APIs

### 3. **Environment Variables** (Required)
```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SECRET_KEY=your-flask-secret-key
REDIRECT_URI=https://your-domain.com/callback
```

### 4. **Google Cloud Services**
- **BigQuery**: Dataset with nursing data
- **OAuth2 Credentials**: Web application type
- **Service Account**: For BigQuery access (optional if using default credentials)

## Deployment Method Requirements

### Option 1: Docker (Easiest)
**Minimum Requirements:**
- Docker installed
- 2GB RAM
- 5GB disk space
- Internet access

**Commands:**
```bash
docker build -t nursingpod-app .
docker run -p 8080:8080 \
  -e GOOGLE_CLIENT_ID=your-id \
  -e GOOGLE_CLIENT_SECRET=your-secret \
  -e SECRET_KEY=your-key \
  -e REDIRECT_URI=http://localhost:8080/callback \
  nursingpod-app
```

### Option 2: Cloud Run (Recommended)
**Minimum Requirements:**
- Google Cloud account
- gcloud CLI installed
- 1GB memory allocation
- 1 vCPU

**Commands:**
```bash
# Enable APIs
gcloud services enable run.googleapis.com containerregistry.googleapis.com

# Build and deploy
docker build -t gcr.io/sanaths-projects/nursingpod-app .
docker push gcr.io/sanaths-projects/nursingpod-app
gcloud run deploy nursingpod-app \
  --image gcr.io/sanaths-projects/nursingpod-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLIENT_ID=your-id,GOOGLE_CLIENT_SECRET=your-secret,SECRET_KEY=your-key
```

### Option 3: Kubernetes (GKE)
**Minimum Requirements:**
- Google Cloud account
- gcloud CLI + kubectl
- GKE cluster (3 nodes minimum)
- 2GB RAM per node
- 10GB disk per node

**Commands:**
```bash
# Create cluster
gcloud container clusters create nursingpod-cluster \
  --num-nodes=3 --region=us-central1

# Deploy
kubectl apply -f k8s/
```

### Option 4: Traditional VPS/Server
**Minimum Requirements:**
- Ubuntu 20.04+ or similar
- 2GB RAM
- 10GB disk
- Python 3.12+
- Nginx (for reverse proxy)

**Setup:**
```bash
# Install Python and dependencies
sudo apt update
sudo apt install python3.12 python3.12-venv nginx

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with gunicorn
gunicorn --bind 0.0.0.0:8080 app:app
```

## Resource Requirements by Scale

### Small (1-10 users)
- **Memory**: 512MB
- **CPU**: 0.5 vCPU
- **Storage**: 1GB
- **Cost**: ~$5-10/month

### Medium (10-100 users)
- **Memory**: 1GB
- **CPU**: 1 vCPU
- **Storage**: 5GB
- **Cost**: ~$20-50/month

### Large (100+ users)
- **Memory**: 2GB
- **CPU**: 2 vCPU
- **Storage**: 10GB
- **Cost**: ~$50-100/month

## Google Cloud Permissions Required

### Service Account Permissions
- `BigQuery User` - Query datasets
- `BigQuery Job User` - Create/manage jobs

### OAuth2 Setup
- Web application type
- Authorized redirect URIs configured
- Client ID and secret generated

## Network Requirements

### Inbound
- **Port 80/443**: HTTP/HTTPS traffic
- **Port 8080**: Application port (if not behind proxy)

### Outbound
- **HTTPS to Google APIs**: OAuth2, BigQuery
- **DNS resolution**: For external services

## Security Requirements

### SSL/TLS
- **Production**: HTTPS required
- **Development**: HTTP acceptable

### Authentication
- **Google OAuth2**: Required
- **Domain restriction**: `@cloudphysician.net`

### Secrets Management
- **Environment variables**: For sensitive data
- **Secret Manager**: For production (Cloud Run)
- **Kubernetes secrets**: For GKE

## Quick Start (Absolute Minimum)

**For immediate testing:**
```bash
# 1. Install Python 3.12
# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export GOOGLE_CLIENT_ID=your-id
export GOOGLE_CLIENT_SECRET=your-secret
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 4. Run
python app.py
```

**For production deployment:**
```bash
# Use Cloud Run (easiest)
make setup-project
make deploy-cloudrun
```

## Cost Estimates

### Cloud Run (Recommended)
- **Free tier**: 2 million requests/month
- **Paid**: $0.40 per million requests + $0.00002400 per vCPU-second
- **Estimated cost**: $5-20/month for typical usage

### GKE
- **Cluster**: $0.10/hour per cluster
- **Nodes**: $0.033/hour per vCPU + $0.004/hour per GB RAM
- **Estimated cost**: $30-100/month

### Traditional VPS
- **DigitalOcean**: $12-24/month
- **AWS EC2**: $10-50/month
- **Google Compute**: $10-50/month

## Troubleshooting Common Issues

### 1. BigQuery Access Denied
- Verify service account has BigQuery permissions
- Check GOOGLE_APPLICATION_CREDENTIALS path
- Ensure project ID is correct

### 2. OAuth2 Errors
- Verify redirect URI matches exactly
- Check client ID/secret are correct
- Ensure domain is in allowed domains

### 3. Memory Issues
- Increase memory allocation
- Check for memory leaks in application
- Monitor resource usage

### 4. Network Issues
- Verify internet connectivity
- Check firewall rules
- Ensure DNS resolution works

## Recommended Architecture

**For Production:**
```
Internet → Load Balancer → Cloud Run → BigQuery
                ↓
            Google OAuth2
```

**For Development:**
```
Local Machine → Docker → BigQuery
                    ↓
                Google OAuth2
```

This provides the most cost-effective, scalable, and maintainable solution.


