# Troubleshooting Google Sign-In Getting Stuck

## Quick Diagnosis

If Google sign-in is getting stuck, follow these steps in order:

### Step 1: Verify Redirect URI in Google Cloud Console

**This is the #1 cause of sign-in getting stuck!**

1. Go to: https://console.cloud.google.com/apis/credentials
2. Find your OAuth 2.0 Client ID (should match: `1032805148357-ud0632ctk62nul4tdhcfhdckm2ib5s3k`)
3. Click **Edit**
4. Under **"Authorized redirect URIs"**, ensure this EXACT URL is listed:
   ```
   http://localhost:5000/callback
   ```
5. **Critical checks:**
   - ✅ No trailing slash (`/callback` NOT `/callback/`)
   - ✅ Protocol is `http://` (not `https://` for localhost)
   - ✅ Port is `5000`
   - ✅ All lowercase
   - ✅ No spaces

6. **Save** and wait 1-2 minutes for changes to propagate

### Step 2: Check OAuth Consent Screen Status

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Check **"User Type"**:
   - If it says **"Testing"**: Continue to Step 3
   - If it says **"In production"**: Skip to Step 4

### Step 3: Add Test User (If App is in Testing Mode)

1. On the OAuth consent screen page, scroll to **"Test users"** section
2. Click **"+ ADD USERS"**
3. Add your `@cloudphysician.net` email address
4. **Save**
5. Try logging in again

### Step 4: Clear Browser Data

1. **Close ALL browser tabs** for `localhost:5000`
2. Clear cookies for `localhost`:
   - Chrome/Edge: Settings → Privacy → Clear browsing data → Cookies
   - Firefox: Settings → Privacy → Cookies and Site Data → Clear Data
3. Or use **Incognito/Private window** for testing

### Step 5: Check Network Connectivity

Test if you can reach Google OAuth servers:

```bash
# Test DNS resolution
nslookup oauth2.googleapis.com

# Test connectivity
curl -I https://oauth2.googleapis.com/token
```

If these fail, check:
- Firewall settings
- VPN/proxy configuration
- Network connectivity

### Step 6: Monitor Server Logs

While attempting to sign in, watch the server logs:

```bash
tail -f flask_output.log
```

Look for:
- `🔄 Starting token exchange with Google...` - Token exchange started
- `✅ Token exchange completed` - Success
- `❌ Token fetch error` - Error occurred
- `Redirect URI mismatch` - Configuration issue

### Step 7: Check Browser Console

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Try signing in
4. Look for:
   - Callback request to `/callback`
   - Any error responses
   - Status codes (400, 403, 500, etc.)

## Common Error Messages

### "redirect_uri_mismatch"
- **Fix**: Add `http://localhost:5000/callback` to Google Cloud Console (see Step 1)

### "access_denied" or "App Not Verified"
- **Fix**: Add your email as test user (see Step 3)

### "Invalid state parameter"
- **Fix**: Clear browser cookies and try again (see Step 4)

### Connection timeout
- **Fix**: Check network connectivity (see Step 5)

## Still Stuck?

1. **Run verification script:**
   ```bash
   python verify_oauth.py
   ```

2. **Check server logs for specific errors:**
   ```bash
   tail -50 flask_output.log | grep -i "error\|oauth\|callback"
   ```

3. **Try in incognito/private window** to rule out browser extensions

4. **Verify your email domain:**
   - Make sure you're using a `@cloudphysician.net` email
   - The app only allows this domain

## Quick Fix Checklist

- [ ] Redirect URI `http://localhost:5000/callback` added in Google Cloud Console
- [ ] No trailing slash in redirect URI
- [ ] Email added as test user (if app is in Testing mode)
- [ ] Browser cookies cleared
- [ ] Network connectivity to Google OAuth servers working
- [ ] Using `@cloudphysician.net` email address
- [ ] Waited 1-2 minutes after changing Google Cloud Console settings

