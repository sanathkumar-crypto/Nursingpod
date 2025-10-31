# Google OAuth Authentication Setup

This application uses Google OAuth2 for authentication and restricts access to email addresses ending with `@cloudphysician.net`.

## Setup Instructions

### 1. Create Google OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. Choose **Web application** as the application type
6. Configure:
   - **Name**: Nursing Pod Dashboard (or any name)
   - **Authorized JavaScript origins**: 
     - `http://localhost:5000` (for development)
     - `https://yourdomain.com` (for production - **ADD BOTH**)
   - **Authorized redirect URIs**:
     - `http://localhost:5000/callback` (for development)
     - `https://yourdomain.com/callback` (for production - **ADD BOTH**)
   - **Important**: You can add multiple URIs - add both development and production URLs
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

### 2. Set Environment Variables

#### For Development

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
REDIRECT_URI=http://localhost:5000/callback
```

#### For Production

Update your `.env` file (or use environment variables on your server):

```env
SECRET_KEY=your-strong-random-secret-key-here
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
REDIRECT_URI=https://yourdomain.com/callback
```

**Important for Production:**
1. Generate a strong random `SECRET_KEY`:
   ```python
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **Update `REDIRECT_URI`** to match your production domain (e.g., `https://dashboard.cloudphysician.net/callback`)
3. **The same OAuth Client ID can be used for both development and production** - just ensure both URIs are added in Google Cloud Console

### Deployment Checklist

When deploying to production, ensure:

- ✅ Add production URL to **Authorized JavaScript origins** in Google Cloud Console
- ✅ Add production callback URL to **Authorized redirect URIs** in Google Cloud Console  
- ✅ Update `REDIRECT_URI` in `.env` to your production URL
- ✅ Update `SECRET_KEY` to a strong random key
- ✅ Use HTTPS (Google OAuth requires HTTPS for production)
- ✅ Keep credentials secure (use environment variables, not hardcoded values)

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

### 5. Access the Dashboard

1. Navigate to `http://localhost:5000`
2. You will be redirected to Google login
3. Sign in with a `@cloudphysician.net` email address
4. If successful, you'll be redirected back to the dashboard

## Access Control

- **Allowed**: Users with email addresses ending in `@cloudphysician.net`
- **Blocked**: Users with any other email domain will see an "Access Denied" error

## Security Notes

- The application verifies the OAuth state parameter to prevent CSRF attacks
- Session data is stored server-side
- Use HTTPS in production
- Keep your `SECRET_KEY` and `GOOGLE_CLIENT_SECRET` secure and never commit them to version control

## Troubleshooting

### Verify OAuth Configuration

Run the verification script to check your configuration:

```bash
python verify_oauth.py
```

### Common OAuth 400 Errors

#### "Redirect URI Mismatch" (Most Common)

**Symptom**: Error 400 with message about redirect_uri_mismatch

**Cause**: The redirect URI in your code doesn't exactly match what's in Google Cloud Console.

**Solution**:
1. Run `python verify_oauth.py` to see your configured redirect URI
2. Go to [Google Cloud Console > Credentials](https://console.cloud.google.com/apis/credentials)
3. Edit your OAuth 2.0 Client ID
4. Under "Authorized redirect URIs", ensure **EXACTLY** this is listed:
   - For development: `http://localhost:5000/callback`
   - For production: `https://yourdomain.com/callback`
5. **Critical checks**:
   - ✅ No trailing slash (`/callback` NOT `/callback/`)
   - ✅ Protocol matches (`http://` for localhost, `https://` for production)
   - ✅ Port matches (5000 for development)
   - ✅ Case sensitive (all lowercase)
   - ✅ No spaces or extra characters
6. Save and wait 1-2 minutes for changes to propagate
7. Try logging in again

**Common Mistakes**:
- ❌ `http://localhost:5000/callback/` (trailing slash)
- ❌ `http://127.0.0.1:5000/callback` (different hostname)
- ❌ `https://localhost:5000/callback` (wrong protocol for localhost)
- ❌ `HTTP://localhost:5000/callback` (wrong case)

#### "Access Denied" or "App Not Verified"

**Symptom**: Error 400 about access_denied or unverified app

**Cause**: Your app is in "Testing" status and your email isn't added as a test user.

**Solution**:
1. Go to [Google Cloud Console > OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. Check "User Type" - if it says "Testing", continue:
3. Scroll to "Test users" section
4. Click "+ ADD USERS"
5. Add your `@cloudphysician.net` email address
6. Save and try logging in again

**Alternative**: Publish your app to "In production" (requires app verification for sensitive scopes)

#### "Invalid Request" or Missing Parameters

**Symptom**: Generic 400 error without specific details

**Causes & Solutions**:
1. **Missing Client ID/Secret**: Check your `.env` file has both values set
2. **Missing redirect_uri parameter**: Should be handled automatically by the code
3. **Invalid scope**: Ensure scopes are properly configured (code handles this)
4. **Cookie/Session issues**: Clear browser cookies and try again
5. **Browser security settings**: Disable strict popup blockers temporarily

#### "Invalid state parameter"

**Symptom**: Error about state parameter mismatch

**Cause**: Session expired or CSRF protection triggered

**Solution**:
1. Clear browser cookies for localhost
2. Try logging in again immediately (don't wait)
3. Ensure cookies are enabled in your browser
4. If using incognito/private mode, make sure it allows cookies

### Diagnostic Steps

1. **Check Server Logs**: When you attempt login, check the Flask console output. You'll see:
   - The redirect URI being used
   - OAuth callback details
   - Specific error messages from Google

2. **Test in Browser Console**: Open browser DevTools (F12) and check:
   - Network tab for the callback request
   - Any error responses from Google
   - The exact redirect URL being used

3. **Verify Google Cloud Console**:
   - Client ID format: Should end with `.apps.googleusercontent.com`
   - OAuth consent screen status: Testing vs Published
   - Test users list: Must include your email if in Testing mode

### Quick Fix Checklist

- [ ] Redirect URI matches exactly (no trailing slash, correct protocol)
- [ ] Email added as test user (if app is in Testing mode)
- [ ] `.env` file has all required variables
- [ ] Client ID and Secret are correct (not placeholder values)
- [ ] Browser cookies enabled
- [ ] Wait 1-2 minutes after changing Google Cloud Console settings
- [ ] Check server logs for detailed error messages

### Getting More Help

If errors persist:
1. Run `python verify_oauth.py` and share the output
2. Check Flask server console logs during login attempt
3. Look at browser console/network tab for specific error messages
4. Verify Google Cloud Console settings match the diagnostic output

