#!/bin/bash

# Navigate to project directory
cd /home/sanath/Nursingpod || exit 1

# Activate virtual environment
source venv/bin/activate || exit 1

# Set environment variables
export FLASK_ENV=development

# Kill any existing Flask processes on port 5000
echo "Checking for existing processes on port 5000..."
lsof -ti:5000 | xargs -r kill -9 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null
sleep 2

# Check if port is still in use
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "ERROR: Port 5000 is still in use. Please manually free it."
    exit 1
fi

# Start Flask server
echo "Starting Flask server on port 5000..."
nohup python app.py > flask_output.log 2>&1 &
FLASK_PID=$!

# Wait for server to start
sleep 5

# Check if process is still running (check both parent and any child processes)
if ps -p $FLASK_PID > /dev/null || pgrep -f "python.*app.py" > /dev/null; then
    ACTUAL_PID=$(pgrep -f "python.*app.py" | head -1)
    echo "Flask server started successfully (PID: $ACTUAL_PID)"
    echo "Server running at: http://localhost:5000"
    echo "View logs: tail -f flask_output.log"
    echo ""
    echo "To stop the server: pkill -f 'python.*app.py'"
else
    echo "ERROR: Flask server failed to start. Check flask_output.log for errors."
    tail -30 flask_output.log
    exit 1
fi

