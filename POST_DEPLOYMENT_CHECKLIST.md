# Post-Deployment Checklist

## ✅ Completed Steps
- [x] Docker image built
- [x] Image pushed to Google Container Registry
- [x] Cloud Run service deployed
- [x] Service account configured

## 🔍 Verification Steps

### 1. Verify Service is Running

```bash
# Get service URL
gcloud run services describe nursingpod-app \
  --region us-central1 \
  --format 'value(status.url)'

# Check service status
gcloud run services list --region us-central1
```

### 2. Test the Application

```bash
# Get the service URL first
SERVICE_URL=$(gcloud run services describe nursingpod-app --region us-central1 --format 'value(status.url)')

# Test if it's accessible
curl -I $SERVICE_URL/login-page

# Or open in browser
echo "Visit: $SERVICE_URL"
```

### 3. Verify Secrets are Configured

```bash
# List all secrets
gcloud secrets list

# Verify secrets exist:
# - google-client-id
# - google-client-secret  
# - secret-key
```

### 4. ⚠️ IMPORTANT: Update OAuth Redirect URI

**This is critical for authentication to work!**

1. Get your Cloud Run service URL:
   ```bash
   gcloud run services describe nursingpod-app --region us-central1 --format 'value(status.url)'
   ```

2. Go to [Google Cloud Console - OAuth Credentials](https://console.cloud.google.com/apis/credentials)

3. Click on your OAuth 2.0 Client ID

4. Add the redirect URI:
   ```
   https://YOUR_SERVICE_URL/callback
   ```
   
   Example: `https://nursingpod-app-xxxxxxxxx-uc.a.run.app/callback`

5. Click **Save**

### 5. Test OAuth Login

1. Visit your service URL: `https://YOUR_SERVICE_URL`
2. Try logging in with Google OAuth
3. Verify it redirects correctly
4. Check that `@cloudphysician.net` email restriction works

### 6. Verify BigQuery Access

The application should be able to query BigQuery using the service account:
- Service account: `sanaths-projects@sanaths-projects.iam.gserviceaccount.com`
- Verify it has BigQuery User and Job User roles

```bash
# Check service account permissions
gcloud projects get-iam-policy sanaths-projects \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:sanaths-projects@sanaths-projects.iam.gserviceaccount.com"
```

### 7. Monitor Logs

```bash
# View recent logs
gcloud run services logs read nursingpod-app \
  --region us-central1 \
  --limit 50

# Follow logs in real-time
gcloud run services logs tail nursingpod-app \
  --region us-central1
```

### 8. Check Service Health

```bash
# Get service details
gcloud run services describe nursingpod-app \
  --region us-central1 \
  --format yaml

# Check if it's ready
gcloud run services describe nursingpod-app \
  --region us-central1 \
  --format 'value(status.conditions[0].status)'
```

## Common Issues & Fixes

### Issue: OAuth redirect URI mismatch
**Solution**: Update redirect URI in Google Cloud Console (see step 4 above)

### Issue: 403 Forbidden / Permission denied
**Solution**: Check service account has BigQuery permissions

### Issue: Secrets not found
**Solution**: Run `./setup-secrets.sh` to create secrets

### Issue: Service not responding
**Solution**: Check logs for errors

## Production Recommendations

### Security
- [ ] Review service account permissions
- [ ] Enable Cloud Armor if needed
- [ ] Set up custom domain (optional)
- [ ] Enable Cloud CDN (optional)

### Monitoring
- [ ] Set up Cloud Monitoring alerts
- [ ] Configure error reporting
- [ ] Set up uptime checks

### Scaling
- [ ] Adjust `--min-instances` if you need always-on
- [ ] Adjust `--max-instances` based on expected load
- [ ] Monitor costs

### Backup
- [ ] Document configuration
- [ ] Save service account keys securely
- [ ] Document secret values (securely)

## Quick Commands Reference

```bash
# Get service URL
gcloud run services describe nursingpod-app --region us-central1 --format 'value(status.url)'

# View logs
gcloud run services logs read nursingpod-app --region us-central1

# Update service
gcloud run services update nursingpod-app --region us-central1

# Delete service (if needed)
gcloud run services delete nursingpod-app --region us-central1
```

## Success Criteria

✅ Service is accessible via HTTPS URL  
✅ OAuth login works  
✅ Can access dashboard after login  
✅ BigQuery data loads correctly  
✅ No errors in logs  

If all these work, your deployment is complete! 🎉



