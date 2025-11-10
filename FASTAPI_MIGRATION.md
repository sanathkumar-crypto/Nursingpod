# FastAPI Migration Guide

This document explains the FastAPI migration and how to use it.

## What Changed

The application has been migrated from Flask to FastAPI. The new FastAPI version is in `app_fastapi.py`.

## Key Benefits

1. **Automatic API Documentation**: Visit `/docs` for Swagger UI or `/redoc` for ReDoc
2. **Better Performance**: Async support and better concurrency handling
3. **Type Safety**: Pydantic models for request/response validation
4. **Modern Stack**: FastAPI is built on modern Python async/await

## Files Changed

- `app_fastapi.py` - New FastAPI application
- `requirements.txt` - Added FastAPI and Uvicorn dependencies
- `Dockerfile` - Updated to use Uvicorn instead of Gunicorn
- `start_fastapi.sh` - New startup script for FastAPI

## Running Locally

### Option 1: Using the startup script
```bash
./start_fastapi.sh
```

### Option 2: Using uvicorn directly
```bash
uvicorn app_fastapi:app --host 0.0.0.0 --port 5000 --reload
```

### Option 3: Using Python
```bash
python app_fastapi.py
```

## Access Points

- **Dashboard**: http://localhost:5000/
- **API Documentation (Swagger)**: http://localhost:5000/docs
- **API Documentation (ReDoc)**: http://localhost:5000/redoc
- **API Filter Endpoint**: http://localhost:5000/api/filter
- **API Charts Endpoint**: http://localhost:5000/api/charts

## API Endpoints

All endpoints work the same as the Flask version:

### GET /
Main dashboard page (HTML)

### GET /api/filter
Filter data endpoint
- Query parameters: `escalation`, `email`, `hospital`, `date`, `exclude_camera`
- Returns: JSON with `table_html`, `row_count`, `columns`

### GET /api/charts
Chart data endpoint
- Query parameters: `escalation`, `email`, `hospital`, `date`, `exclude_camera`
- Returns: JSON with `monthly_trend`, `escalation_dist`, `nurse_wise_trend`

## Deployment

The Dockerfile has been updated to use Uvicorn. Deploy as usual:

```bash
docker build -t nursingpod-app .
docker run -p 8080:8080 nursingpod-app
```

For Cloud Run, the deployment process remains the same - the Dockerfile will automatically use FastAPI.

## Migration Notes

- The FastAPI app imports helper functions from `app.py` to avoid code duplication
- All business logic remains the same
- Templates work the same way (using Jinja2Templates)
- Authentication is still disabled (same as Flask version)

## Performance Improvements

- Better async support for BigQuery queries (can be added later)
- Higher concurrency with Uvicorn workers
- Automatic request validation
- Better error handling

## Testing

Test the API endpoints using the interactive docs at `/docs` or use curl:

```bash
# Test filter endpoint
curl "http://localhost:5000/api/filter?escalation=all&email=all&hospital=all&date=all"

# Test charts endpoint
curl "http://localhost:5000/api/charts?escalation=all&email=all&hospital=all&date=all"
```

## Rollback

If you need to rollback to Flask:
1. Update Dockerfile CMD to use `gunicorn app:app`
2. Use `start_server.sh` instead of `start_fastapi.sh`
3. The original `app.py` still works

## Next Steps

1. Test all endpoints
2. Monitor performance
3. Consider adding async BigQuery queries for better performance
4. Add Pydantic models for request/response validation
5. Remove Flask dependencies once fully migrated

