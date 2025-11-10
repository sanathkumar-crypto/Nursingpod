#!/bin/bash
# Start script for FastAPI application

PORT=${PORT:-5000}

echo "Starting FastAPI server on port $PORT..."
echo "Server will be available at: http://localhost:$PORT"
echo "API documentation will be available at: http://localhost:$PORT/docs"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run FastAPI with uvicorn
uvicorn app_fastapi:app --host 0.0.0.0 --port $PORT --reload

