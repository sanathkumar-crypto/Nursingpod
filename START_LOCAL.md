# Starting the Application Locally

## Quick Start

### Option 1: Use the Startup Script (Recommended)

```bash
cd /home/sanath/Nursingpod
./start_server.sh
```

This script automatically:
- Cleans up any existing processes on port 5000
- Starts the Flask server in the background
- Verifies the server started successfully
- Shows you the server URL and log file location

### Option 2: Manual Start

```bash
cd /home/sanath/Nursingpod
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

**Note:** When running manually in foreground, the reloader is enabled for auto-reload on code changes. When running in background with `nohup`, the reloader is automatically disabled to prevent process management issues.

The application will be available at: **http://localhost:5000**

## Environment Setup

Make sure your `.env` file has:
```env
SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
REDIRECT_URI=http://localhost:5000/callback
```

**Note:** The `.env` file has `REDIRECT_URI=http://localhost:8080/callback`, but the app runs on port 5000 by default. Update it if needed:
```bash
sed -i 's/REDIRECT_URI=http:\/\/localhost:8080\/callback/REDIRECT_URI=http:\/\/localhost:5000\/callback/' .env
```

## Access the Application

- **Login Page**: http://localhost:5000/login-page
- **Dashboard**: http://localhost:5000/ (requires login)
- **Direct Login**: http://localhost:5000/login

## Troubleshooting

### Port Already in Use
```bash
# Kill existing process
pkill -f "python.*app.py"

# Or use a different port
export PORT=5001
python app.py
```

### BigQuery Access Issues
Make sure you're authenticated:
```bash
gcloud auth application-default login
```

### OAuth Redirect URI
Ensure Google Cloud Console has `http://localhost:5000/callback` added as an authorized redirect URI.

## Stop the Server

If running in foreground: Press `Ctrl+C` in the terminal

If running in background:
```bash
pkill -f "python.*app.py"
```

Or use the startup script:
```bash
./start_server.sh  # This will kill existing processes before starting new one
```

## Troubleshooting Server Restarts

If the server keeps stopping:
1. **Check for port conflicts:** `lsof -i :5000`
2. **Check logs:** `tail -f flask_output.log`
3. **Use the startup script:** It handles process cleanup automatically
4. **The reloader is disabled in background mode** - this prevents the process management issues that cause restarts


