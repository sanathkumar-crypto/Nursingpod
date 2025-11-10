"""
FastAPI version of the Nursingpod application
Full migration from Flask to FastAPI
"""
import os
from urllib.parse import unquote
from datetime import datetime, timedelta
from typing import Optional
import json

# Set OAUTHLIB_INSECURE_TRANSPORT for local development
if os.getenv('FLASK_ENV') == 'development' or os.getenv('ENVIRONMENT') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from fastapi import FastAPI, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from google.cloud import bigquery
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.utils
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Nursingpod Dashboard",
    description="Dashboard for nursing pod quality data analysis",
    version="1.0.0"
)

# Trust proxy headers (similar to Flask's ProxyFix)
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Add url_for function to templates for Flask compatibility
def url_for_static(request: Request, filename: str):
    """Helper function to generate static file URLs (Flask-compatible)"""
    return f"/static/{filename}"

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add url_for to template globals for Flask compatibility
templates.env.globals['url_for'] = lambda endpoint, **values: (
    f"/static/{values.get('filename', '')}" if endpoint == 'static' 
    else f"/{endpoint}" if values else f"/{endpoint}"
)

# Initialize BigQuery client
client = bigquery.Client()

# DISABLE LOGIN FOR DIRECT ACCESS (same as Flask version)
LOGIN_DISABLED = True

# Helper functions (same as Flask version)
def escape_sql_string(value):
    """Escape single quotes for SQL strings"""
    if not value:
        return ''
    return str(value).replace("'", "''")

def build_hospital_condition(hospital_param):
    """Build SQL condition for hospital filter, handling multiple values"""
    if hospital_param == 'all' or not hospital_param:
        return None
    
    hospital_param = unquote(str(hospital_param))
    
    if ',' in hospital_param:
        hospitals = [h.strip() for h in hospital_param.split(',') if h.strip()]
        if not hospitals or len(hospitals) > 100:
            return None
        escaped_hospitals = [f"'{escape_sql_string(h)}'" for h in hospitals]
        return f"hospital_name IN ({', '.join(escaped_hospitals)})"
    else:
        escaped_hospital = escape_sql_string(hospital_param)
        return f"hospital_name = '{escaped_hospital}'"

# Define column mappings for each escalation type (same as Flask)
ESCALATION_COLUMNS = {
    'Camera Annotation Events': [
        'event_id', 'camera_ip', 'event_name', 'comment', 'user_email', 
        'user_role', 'timestamp', 'hospital_name', 'hospital_id', 
        'unit_name', 'unit_id'
    ],
    'Impact Cases': [
        'email_address', 'hospital_name', 'impact_type', 'impact_score',
        'impact_rating', 'bed_name_score', 'eagle_score', 'patient_link'
    ],
    'Lab abnormality': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Vitals abnormality': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'who_recommended_icu_move', 'patient_moved_to_icu', 'reason_not_moved',
        'workspace_moved_to', 'patient_handover_completed', 'concerns_feedback',
        'comments', 'patient_link'
    ],
    'Nursing care': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Lines and infusion syringes not labelled': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Medication error': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Ventilator Alarm - Suctioning': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Glycemic abnormality': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Drop in GCS': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Gasping': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Jerky movement': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Position not changed': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'patient_moved_to_icu', 'reason_not_moved', 'patient_handover_completed',
        'comments', 'patient_link'
    ],
    'Educating nurses': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'training_session_image',
        'issue_details', 'session_attendees', 'teaching_session_screenshot',
        'session_topic', 'score', 'issues', 'patient_link'
    ],
    'Issues': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'issue_details',
        'issues', 'comments', 'patient_link'
    ],
    'Level 4 patients moved to ICU services': [
        'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
        'escalation_observation', 'bedside_staff_name', 'intervention_advised',
        'communication_method', 'intervention_status', 'recommend_icu_move',
        'who_recommended_icu_move', 'patient_moved_to_icu', 'reason_not_moved',
        'workspace_moved_to', 'patient_handover_completed', 'concerns_feedback',
        'comments', 'patient_link'
    ]
}

# Import helper functions from Flask app
# We import them directly - Flask app won't initialize routes if we import selectively
# To avoid Flask initialization, we'll import the module but skip route registration
import sys
import importlib.util

# Temporarily disable Flask route registration by patching
original_route = None
try:
    # Import Flask but prevent route registration
    import flask
    # Create a mock Flask app context to import functions
    from app import (
        get_filter_options,
        get_filtered_data,
        get_monthly_data,
        create_camera_user_role_chart,
        create_camera_events_charts,
        create_nurse_wise_trend_chart,
        create_educating_nurses_nurse_wise_trend_chart,
        create_impact_score_chart,
        create_impact_cases_charts,
        create_monthly_trend_chart,
        create_escalation_distribution_chart
    )
except ImportError as e:
    print(f"Warning: Could not import functions from app.py: {e}")
    print("Make sure app.py is in the same directory")
    raise

# FastAPI Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page"""
    filter_options = get_filter_options()
    # Initial load with recent data only (last 3 months) for better performance
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    monthly_data = get_monthly_data('all', 'all', 'all', f'{start_date},{end_date}')
    
    # Create monthly trend chart
    monthly_trend = create_monthly_trend_chart(monthly_data)
    
    # Create escalation distribution chart
    escalation_dist = create_escalation_distribution_chart(monthly_data)
    
    # Create a mock current_user for template compatibility
    current_user = type('User', (), {
        'email': 'Guest User',
        'is_authenticated': False
    })()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "filter_options": filter_options,
        "monthly_trend": monthly_trend,
        "escalation_dist": escalation_dist,
        "current_user": current_user
    })

@app.get("/login-page")
async def login_page():
    """Show login page template - Redirects to index since OAuth is disabled"""
    return RedirectResponse(url="/")

@app.get("/logout")
async def logout():
    """Logout endpoint"""
    return RedirectResponse(url="/")

@app.get("/api/filter")
async def api_filter(
    escalation: str = Query('all', description="Escalation type filter"),
    email: str = Query('all', description="Email filter"),
    hospital: str = Query('all', description="Hospital filter"),
    date: str = Query('all', description="Date filter"),
    exclude_camera: str = Query('false', description="Exclude camera annotations")
):
    """API endpoint for filtering data"""
    try:
        exclude_camera_bool = exclude_camera.lower() == 'true'
        
        df = get_filtered_data(escalation, email, hospital, date, exclude_camera=exclude_camera_bool)
        
        # Get columns to display based on escalation type
        if escalation != 'all' and escalation in ESCALATION_COLUMNS:
            display_columns = ESCALATION_COLUMNS[escalation]
            available_columns = [col for col in display_columns if col in df.columns]
            df_filtered = df[available_columns]
        else:
            # Default columns for 'all' selection
            default_columns = [
                'timestamp', 'email_address', 'nurse_on_shift', 'hospital_name',
                'escalation_observation', 'bedside_staff_name', 'intervention_advised',
                'communication_method', 'intervention_status', 'recommend_icu_move',
                'patient_moved_to_icu', 'comments', 'patient_link'
            ]
            available_columns = [col for col in default_columns if col in df.columns]
            df_filtered = df[available_columns]
        
        # Convert to HTML table
        table_html = df_filtered.to_html(classes='table table-striped', 
                                       table_id='data-table',
                                       escape=False,
                                       index=False)
        
        return JSONResponse({
            'table_html': table_html,
            'row_count': len(df_filtered),
            'columns': available_columns
        })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error in api_filter: {error_msg}")
        print(traceback.format_exc())
        
        return JSONResponse(
            status_code=500,
            content={
                'table_html': '<tr><td colspan="10" class="text-center text-danger">Error loading data. Please try again.</td></tr>',
                'row_count': 0,
                'columns': [],
                'error': error_msg
            }
        )

@app.get("/api/charts")
async def api_charts(
    escalation: str = Query('all', description="Escalation type filter"),
    email: str = Query('all', description="Email filter"),
    hospital: str = Query('all', description="Hospital filter"),
    date: str = Query('all', description="Date filter"),
    exclude_camera: str = Query('false', description="Exclude camera annotations")
):
    """API endpoint for getting filtered chart data"""
    try:
        exclude_camera_bool = exclude_camera.lower() == 'true'
        
        # URL decode and normalize escalation
        escalation = unquote(str(escalation)).strip()
        escalation_normalized = escalation.strip()
        
        # Debug logging
        print(f"\n=== API CHARTS DEBUG ===")
        print(f"Received params - escalation: '{escalation}', email: '{email}', hospital: '{str(hospital)[:100]}...', date: '{date}', exclude_camera: {exclude_camera_bool}")
        print(f"Escalation normalized: '{escalation_normalized}'")
        
        # If exclude_camera is True and escalation is Camera Annotation Events, return empty charts
        if escalation_normalized == 'Camera Annotation Events' and exclude_camera_bool:
            print("DEBUG: Camera Annotation Events excluded - returning empty charts")
            empty_chart = json.dumps({
                'data': [],
                'layout': {
                    'title': 'No data (Camera Annotations excluded)',
                    'font': {'family': 'Source Sans Pro', 'size': 12},
                    'plot_bgcolor': 'white',
                    'paper_bgcolor': 'white'
                }
            }, cls=plotly.utils.PlotlyJSONEncoder)
            return JSONResponse({
                'monthly_trend': empty_chart,
                'escalation_dist': empty_chart,
                'nurse_wise_trend': empty_chart
            })
        
        if escalation_normalized == 'Camera Annotation Events':
            print("DEBUG: api_charts - Branch: Camera Annotation Events")
            camera_dist = create_camera_events_charts(escalation_normalized, email, hospital, date)
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera_bool)
            monthly_trend = create_monthly_trend_chart(monthly_data)
            nurse_wise_trend = create_nurse_wise_trend_chart(email, hospital, date)
            
            return JSONResponse({
                'monthly_trend': monthly_trend,
                'escalation_dist': camera_dist,
                'nurse_wise_trend': nurse_wise_trend
            })
        elif escalation_normalized == 'Educating nurses':
            print("DEBUG: api_charts - Branch: Educating nurses")
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera_bool)
            monthly_trend = create_monthly_trend_chart(monthly_data)
            escalation_dist = create_escalation_distribution_chart(monthly_data)
            nurse_wise_trend = create_educating_nurses_nurse_wise_trend_chart(email, hospital, date)
            
            return JSONResponse({
                'monthly_trend': monthly_trend,
                'escalation_dist': escalation_dist,
                'nurse_wise_trend': nurse_wise_trend
            })
        elif escalation_normalized == 'Impact Cases':
            print("DEBUG: api_charts - Branch: Impact Cases")
            impact_dist = create_impact_cases_charts(escalation_normalized, email, hospital, date)
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera_bool)
            monthly_trend = create_monthly_trend_chart(monthly_data)
            
            return JSONResponse({
                'monthly_trend': monthly_trend,
                'escalation_dist': impact_dist
            })
        else:
            print(f"DEBUG: api_charts - Branch: else (escalation='{escalation_normalized}')")
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera_bool)
            
            if not monthly_data.empty:
                unique_escalations = monthly_data['escalation_observation'].unique().tolist()
                print(f"DEBUG: Monthly data has {len(unique_escalations)} escalation types: {unique_escalations}")
            else:
                print("DEBUG: Monthly data is empty")
            
            monthly_trend = create_monthly_trend_chart(monthly_data)
            escalation_dist = create_escalation_distribution_chart(monthly_data)
            
            monthly_trend_parsed = json.loads(monthly_trend)
            if monthly_trend_parsed.get('data'):
                chart_escalations = [trace.get('name') for trace in monthly_trend_parsed['data']]
                print(f"DEBUG: Chart will display {len(chart_escalations)} escalation types: {chart_escalations}")
            
            return JSONResponse({
                'monthly_trend': monthly_trend,
                'escalation_dist': escalation_dist
            })
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Error in api_charts: {error_msg}")
        print(traceback.format_exc())
        
        empty_chart = json.dumps({
            'data': [],
            'layout': {
                'title': 'Error loading chart data',
                'font': {'family': 'Source Sans Pro', 'size': 12},
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white'
            }
        }, cls=plotly.utils.PlotlyJSONEncoder)
        
        return JSONResponse(
            status_code=500,
            content={
                'monthly_trend': empty_chart,
                'escalation_dist': empty_chart,
                'nurse_wise_trend': empty_chart,
                'error': error_msg
            }
        )

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development' or os.getenv('ENVIRONMENT') == 'development'
    uvicorn.run(app, host='0.0.0.0', port=port, reload=debug)

