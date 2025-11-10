# IMPORTANT: Set this BEFORE importing any OAuth libraries
# Allow insecure transport for localhost development (OAuth over HTTP)
# This MUST be set before oauthlib/requests_oauthlib are imported
# Safe for localhost but should NEVER be set in production
import os
# Only set OAUTHLIB_INSECURE_TRANSPORT for local development
if os.getenv('FLASK_ENV') == 'development' or os.getenv('ENVIRONMENT') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from google.cloud import bigquery
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.utils
import json
from datetime import datetime, timedelta
from urllib.parse import unquote
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production-' + os.urandom(24).hex())

# Trust proxy headers from Cloud Run / load balancers
# This ensures request.is_secure and request.scheme work correctly behind proxies
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure session settings - CRITICAL for OAuth state persistence
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cross-site redirects from Google OAuth
# Secure cookies only in production (HTTPS)
is_production = os.getenv('FLASK_ENV') != 'development' and os.getenv('ENVIRONMENT') != 'development'
app.config['SESSION_COOKIE_SECURE'] = is_production
app.config['SESSION_COOKIE_NAME'] = 'flask_session'  # Explicit cookie name
app.config['SESSION_COOKIE_PATH'] = '/'  # Ensure cookie is available for all paths
# Don't set SESSION_COOKIE_DOMAIN for localhost - Flask handles this automatically

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'
login_manager.login_message = 'Please log in to access the dashboard.'
login_manager.login_message_category = 'info'

# DISABLE LOGIN FOR DIRECT ACCESS (OAuth commented out)
app.config['LOGIN_DISABLED'] = True

# OAuth2 Configuration - COMMENTED OUT FOR DIRECT ACCESS
# CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
# CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
# SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
# REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/callback')
# ALLOWED_DOMAIN = '@cloudphysician.net'

# Initialize BigQuery client
client = bigquery.Client()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name
    
    @staticmethod
    def get(user_id):
        # Retrieve user from session
        if 'user_email' in session and session.get('user_id') == user_id:
            return User(
                session.get('user_id'),
                session.get('user_email'),
                session.get('user_name', '')
            )
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def escape_sql_string(value):
    """Escape single quotes for SQL strings"""
    if not value:
        return ''
    return str(value).replace("'", "''")

def build_hospital_condition(hospital_param):
    """Build SQL condition for hospital filter, handling multiple values"""
    if hospital_param == 'all' or not hospital_param:
        return None
    
    # URL decode the hospital parameter in case of encoded characters
    hospital_param = unquote(str(hospital_param))
    
    if ',' in hospital_param:
        hospitals = [h.strip() for h in hospital_param.split(',') if h.strip()]
        if not hospitals:
            return None
        
        # If too many hospitals (more than 100), treat as 'all' to avoid SQL query size issues
        if len(hospitals) > 100:
            return None
        
        # Escape each hospital name and use IN clause for better performance
        escaped_hospitals = [f"'{escape_sql_string(h)}'" for h in hospitals]
        return f"hospital_name IN ({', '.join(escaped_hospitals)})"
    else:
        escaped_hospital = escape_sql_string(hospital_param)
        return f"hospital_name = '{escaped_hospital}'"

# Define column mappings for each escalation type
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

def get_filter_options():
    """Get unique values for filter dropdowns - optimized for performance"""
    # Limit to last 3 months for filter options to improve load time
    # Get escalation data from nursing pod quality data
    query1 = """
    SELECT DISTINCT 
        escalation_observation,
        email_address,
        hospital_name,
        DATE(timestamp) as date_only
    FROM `prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data`
    WHERE escalation_observation IS NOT NULL 
    AND escalation_observation != ''
    AND email_address IS NOT NULL 
    AND email_address != ''
    AND email_address != '0'
    AND hospital_name IS NOT NULL 
    AND hospital_name != ''
    AND DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
    ORDER BY escalation_observation, email_address, hospital_name, date_only
    LIMIT 10000
    """
    
    df1 = client.query(query1).result().to_dataframe()
    
    # Get impact cases data (limited to last 3 months)
    query2 = """
    SELECT DISTINCT 
        email_address,
        hospital_name
    FROM `prod-tech-project1-bv479-zo027.gsheet_data.impact_cases`
    WHERE email_address IS NOT NULL 
    AND email_address != ''
    AND hospital_name IS NOT NULL 
    AND hospital_name != ''
    AND DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
    ORDER BY email_address, hospital_name
    LIMIT 5000
    """
    
    df2 = client.query(query2).result().to_dataframe()
    
    # Get camera annotation events data (limited to last 7 days for filter options)
    query3 = """
    SELECT DISTINCT 
        user_email,
        hospital_name,
        DATE(timestamp) as date_only
    FROM `prod-tech-project1-bv479-zo027.mongodb.camera_annotation_events`
    WHERE user_email IS NOT NULL 
    AND user_email != ''
    AND hospital_name IS NOT NULL 
    AND hospital_name != ''
    AND TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    ORDER BY user_email, hospital_name, date_only
    LIMIT 5000
    """
    
    df3 = client.query(query3).result().to_dataframe()
    
    # Combine escalations and add new types
    escalations = sorted(df1['escalation_observation'].unique().tolist())
    escalations.append('Impact Cases')
    escalations.append('Camera Annotation Events')
    
    # Combine emails from all tables
    emails1 = set(df1['email_address'].unique())
    emails2 = set(df2['email_address'].unique())
    emails3 = set(df3['user_email'].unique())
    all_emails = sorted(list(emails1.union(emails2).union(emails3)))
    
    # Combine hospitals from all tables
    hospitals1 = set(df1['hospital_name'].unique())
    hospitals2 = set(df2['hospital_name'].unique())
    hospitals3 = set(df3['hospital_name'].unique())
    all_hospitals = sorted(list(hospitals1.union(hospitals2).union(hospitals3)))
    
    # Combine dates from nursing pod and camera events
    dates1 = set(df1['date_only'].unique())
    dates3 = set(df3['date_only'].unique())
    all_dates = sorted(list(dates1.union(dates3)))
    
    return {
        'escalations': escalations,
        'emails': all_emails,
        'hospitals': all_hospitals,
        'dates': all_dates
    }

def get_filtered_data(escalation='all', email='all', hospital='all', date='all', exclude_camera=False):
    """Get filtered data based on selected filters"""
    # URL decode and normalize escalation
    escalation = unquote(str(escalation)).strip() if escalation != 'all' else 'all'
    
    # Debug logging
    print(f"\nDEBUG: get_filtered_data called with escalation='{escalation}', email='{email}', hospital='{hospital}', date='{date}', exclude_camera={exclude_camera}")
    
    # If exclude_camera is True and escalation is Camera Annotation Events, return empty
    if escalation == 'Camera Annotation Events' and exclude_camera:
        return pd.DataFrame()
    
    if escalation == 'Camera Annotation Events':
        # Query camera annotation events table
        where_conditions = []
        
        if email != 'all':
            escaped_email = escape_sql_string(email)
            where_conditions.append(f"user_email = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions.append(hospital_condition)
        
        # Handle date range filtering
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions.append(f"DATE(timestamp) = '{date}'")
        else:
            # Default to recent data (last 30 days) if no date specified
            where_conditions.append("TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
        
        query = f"""
        SELECT *
        FROM `prod-tech-project1-bv479-zo027.mongodb.camera_annotation_events`
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT 1000
        """
        
        df = client.query(query).result().to_dataframe()
        return df
    elif escalation == 'Impact Cases':
        # Query impact cases table
        where_conditions = []
        
        if email != 'all':
            escaped_email = escape_sql_string(email)
            where_conditions.append(f"email_address = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions.append(hospital_condition)
        
        # Handle date range filtering - Impact Cases table has timestamp column
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions.append(f"DATE(timestamp) = '{date}'")
        # Note: When date='all', we don't add a date filter to show all Impact Cases data
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = f"""
        SELECT *
        FROM `prod-tech-project1-bv479-zo027.gsheet_data.impact_cases`
        WHERE {where_clause}
        ORDER BY impact_score DESC
        LIMIT 1000
        """
        
        df = client.query(query).result().to_dataframe()
        return df
    else:
        # Query nursing pod quality data table
        where_conditions = []
        
        if escalation != 'all':
            # Clean and escape escalation - use TRIM to handle any leading/trailing spaces
            escalation_clean = escalation.strip()
            escaped_escalation = escape_sql_string(escalation_clean)
            where_conditions.append(f"TRIM(escalation_observation) = '{escaped_escalation}'")
        
        if email != 'all':
            escaped_email = escape_sql_string(email)
            where_conditions.append(f"email_address = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions.append(hospital_condition)
        
        # Handle date range filtering
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions.append(f"DATE(timestamp) = '{date}'")
        else:
            # Default to recent data (last 90 days) if no date specified for better performance
            where_conditions.append("DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)"
        
        # Debug logging
        print(f"DEBUG: get_filtered_data - WHERE clause: {where_clause}")
        print(f"DEBUG: get_filtered_data - Number of conditions: {len(where_conditions)}")
        
        query = f"""
        SELECT *
        FROM `prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data`
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT 1000
        """
        
        df = client.query(query).result().to_dataframe()
        print(f"DEBUG: get_filtered_data - Returned {len(df)} rows")
        if not df.empty and escalation != 'all':
            unique_escalations = df['escalation_observation'].str.strip().unique().tolist() if 'escalation_observation' in df.columns else []
            print(f"DEBUG: get_filtered_data - Unique escalation types in results: {unique_escalations}")
        
        return df

def get_monthly_data(escalation='all', email='all', hospital='all', date='all', exclude_camera=False):
    """Get monthly aggregated data for charts with filters"""
    # URL decode and normalize escalation
    escalation = unquote(str(escalation)).strip() if escalation != 'all' else 'all'
    
    print(f"\nDEBUG: get_monthly_data called with escalation='{escalation}', exclude_camera={exclude_camera}")
    
    # If exclude_camera is True and escalation is Camera Annotation Events, return empty
    if escalation == 'Camera Annotation Events' and exclude_camera:
        print("DEBUG: Camera Annotation Events excluded - returning empty dataframe")
        return pd.DataFrame()
    
    if escalation == 'Camera Annotation Events':
        print("DEBUG: Branch: Camera Annotation Events")
        # For camera annotation events, we'll create monthly trends
        where_conditions = []
        
        if email != 'all':
            escaped_email = escape_sql_string(email)
            where_conditions.append(f"user_email = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions.append(hospital_condition)
        
        # Handle date range filtering
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions.append(f"DATE(timestamp) = '{date}'")
        else:
            # Default to recent data (last 30 days) if no date specified
            where_conditions.append("TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
        
        query = f"""
        SELECT 
            DATE_TRUNC(DATE(timestamp), MONTH) as date,
            "Camera Annotation Events" as escalation_observation,
            COUNT(*) as count
        FROM `prod-tech-project1-bv479-zo027.mongodb.camera_annotation_events`
        WHERE event_name IS NOT NULL 
        AND event_name != ''
        AND {where_clause}
        GROUP BY DATE_TRUNC(DATE(timestamp), MONTH)
        ORDER BY DATE_TRUNC(DATE(timestamp), MONTH)
        """
        
        df = client.query(query).result().to_dataframe()
        return df
    elif escalation == 'Impact Cases':
        print("DEBUG: Branch: Impact Cases")
        # For impact cases, we'll create monthly trends
        where_conditions = []
        
        if email != 'all':
            escaped_email = escape_sql_string(email)
            where_conditions.append(f"email_address = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions.append(hospital_condition)
        
        # Handle date range filtering
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions.append(f"DATE(timestamp) = '{date}'")
        # Note: When date='all', we don't add a date filter to show all Impact Cases data
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        query = f"""
        SELECT 
            DATE_TRUNC(DATE(timestamp), MONTH) as date,
            "Impact Cases" as escalation_observation,
            COUNT(*) as count
        FROM `prod-tech-project1-bv479-zo027.gsheet_data.impact_cases`
        WHERE impact_type IS NOT NULL 
        AND impact_type != ''
        AND {where_clause}
        GROUP BY DATE_TRUNC(DATE(timestamp), MONTH)
        ORDER BY DATE_TRUNC(DATE(timestamp), MONTH)
        """
        
        df = client.query(query).result().to_dataframe()
        return df
    elif escalation != 'all':
        print(f"DEBUG: Branch: Specific escalation (not Camera/Impact, not 'all') - '{escalation}'")
        # For specific escalation types (not Impact Cases or Camera Annotation Events), only query nursing pod data
        where_conditions = []
        
        # Add escalation filter - ensure exact match with trimmed value
        escalation_clean = escalation.strip()
        escaped_escalation = escape_sql_string(escalation_clean)
        # Use TRIM to handle any leading/trailing spaces in database
        where_conditions.append(f"TRIM(escalation_observation) = '{escaped_escalation}'")
        print(f"DEBUG: Filtering for escalation (cleaned): '{escalation_clean}' (escaped: '{escaped_escalation}')")
        
        # Debug logging
        print(f"DEBUG: get_monthly_data - escalation='{escalation}', escaped='{escaped_escalation}'")
        
        if email != 'all':
            escaped_email = escape_sql_string(email)
            where_conditions.append(f"email_address = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions.append(hospital_condition)
        
        # Handle date range filtering
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions.append(f"DATE(timestamp) = '{date}'")
        else:
            # Default to recent data (last 90 days) if no date specified for better performance
            where_conditions.append("DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)"
        
        query = f"""
        SELECT 
            DATE_TRUNC(DATE(timestamp), MONTH) as date,
            escalation_observation,
            COUNT(*) as count
        FROM `prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data`
        WHERE escalation_observation IS NOT NULL 
        AND escalation_observation != ''
        AND {where_clause}
        GROUP BY DATE_TRUNC(DATE(timestamp), MONTH), escalation_observation
        ORDER BY DATE_TRUNC(DATE(timestamp), MONTH)
        """
        
        # Debug: Print query
        print(f"DEBUG: SQL Query (first 500 chars): {query[:500]}")
        print(f"DEBUG: WHERE clause: {where_clause}")
        
        df = client.query(query).result().to_dataframe()
        
        # Debug logging
        print(f"DEBUG: get_monthly_data (specific escalation) - returned {len(df)} rows")
        if not df.empty:
            unique_escalations = df['escalation_observation'].unique().tolist()
            print(f"DEBUG: Unique escalation types BEFORE filter check: {unique_escalations}")
            
            # CRITICAL FIX: Ensure data is actually filtered to the requested escalation
            escalation_clean = escalation.strip()
            # Also check trimmed values in the dataframe
            df['escalation_observation_trimmed'] = df['escalation_observation'].str.strip()
            
            if escalation_clean not in unique_escalations and escalation_clean not in df['escalation_observation_trimmed'].unique().tolist() and len(unique_escalations) > 0:
                print(f"WARNING: Requested escalation '{escalation_clean}' not found in results. Found: {unique_escalations}")
                print(f"Attempting to filter dataframe to match '{escalation_clean}' exactly (trimmed)...")
                # Try exact match with trimmed values
                df = df[df['escalation_observation_trimmed'] == escalation_clean].copy()
                df = df.drop(columns=['escalation_observation_trimmed'])
                print(f"After filtering, {len(df)} rows remain")
            elif len(unique_escalations) > 1:
                print(f"WARNING: Multiple escalation types found when filtering for '{escalation_clean}'. Filtering down...")
                df = df[df['escalation_observation_trimmed'] == escalation_clean].copy()
                df = df.drop(columns=['escalation_observation_trimmed'])
                print(f"After filtering, unique types: {df['escalation_observation'].unique().tolist()}")
            else:
                # Clean up the helper column if we didn't use it for filtering
                if 'escalation_observation_trimmed' in df.columns:
                    df = df.drop(columns=['escalation_observation_trimmed'])
        else:
            print("DEBUG: DataFrame is empty - no data found for this filter")
        
        return df
    else:
        print(f"DEBUG: Branch: 'all' - will query all sources")
        # Query all sources and combine (only when escalation == 'all')
        dfs = []
        
        # Query nursing pod quality data
        where_conditions = []
        
        if email != 'all':
            escaped_email = escape_sql_string(email)
            where_conditions.append(f"email_address = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions.append(hospital_condition)
        
        # Handle date range filtering
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions.append(f"DATE(timestamp) = '{date}'")
        else:
            # Default to recent data (last 90 days) if no date specified for better performance
            where_conditions.append("DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)"
        
        query1 = f"""
        SELECT 
            DATE_TRUNC(DATE(timestamp), MONTH) as date,
            escalation_observation,
            COUNT(*) as count
        FROM `prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data`
        WHERE escalation_observation IS NOT NULL 
        AND escalation_observation != ''
        AND {where_clause}
        GROUP BY DATE_TRUNC(DATE(timestamp), MONTH), escalation_observation
        """
        
        df1 = client.query(query1).result().to_dataframe()
        if not df1.empty:
            dfs.append(df1)
        
        # Query impact cases
        where_conditions_impact = []
        if email != 'all':
            escaped_email = email.replace("'", "''")
            where_conditions_impact.append(f"email_address = '{escaped_email}'")
        
        # Build hospital condition using helper function
        hospital_condition = build_hospital_condition(hospital)
        if hospital_condition:
            where_conditions_impact.append(hospital_condition)
        
        if date != 'all' and ',' in date:
            start_date, end_date = date.split(',')
            where_conditions_impact.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
        elif date != 'all':
            where_conditions_impact.append(f"DATE(timestamp) = '{date}'")
        # Note: When date='all', we don't add a date filter to show all Impact Cases data
        
        where_clause_impact = " AND ".join(where_conditions_impact) if where_conditions_impact else "1=1"
        
        query2 = f"""
        SELECT 
            DATE_TRUNC(DATE(timestamp), MONTH) as date,
            "Impact Cases" as escalation_observation,
            COUNT(*) as count
        FROM `prod-tech-project1-bv479-zo027.gsheet_data.impact_cases`
        WHERE impact_type IS NOT NULL 
        AND impact_type != ''
        AND {where_clause_impact}
        GROUP BY DATE_TRUNC(DATE(timestamp), MONTH)
        """
        
        df2 = client.query(query2).result().to_dataframe()
        if not df2.empty:
            dfs.append(df2)
        
        # Query camera annotation events (only if not excluded)
        if not exclude_camera:
            where_conditions_camera = []
            if email != 'all':
                escaped_email = email.replace("'", "''")
                where_conditions_camera.append(f"user_email = '{escaped_email}'")
            
            # Build hospital condition using helper function
            hospital_condition = build_hospital_condition(hospital)
            if hospital_condition:
                where_conditions_camera.append(hospital_condition)
            
            if date != 'all' and ',' in date:
                start_date, end_date = date.split(',')
                where_conditions_camera.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
            elif date != 'all':
                where_conditions_camera.append(f"DATE(timestamp) = '{date}'")
            else:
                where_conditions_camera.append("TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)")
            
            where_clause_camera = " AND ".join(where_conditions_camera) if where_conditions_camera else "TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
            
            query3 = f"""
            SELECT 
                DATE_TRUNC(DATE(timestamp), MONTH) as date,
                "Camera Annotation Events" as escalation_observation,
                COUNT(*) as count
            FROM `prod-tech-project1-bv479-zo027.mongodb.camera_annotation_events`
            WHERE event_name IS NOT NULL 
            AND event_name != ''
            AND {where_clause_camera}
            GROUP BY DATE_TRUNC(DATE(timestamp), MONTH)
            """
            
            df3 = client.query(query3).result().to_dataframe()
            if not df3.empty:
                dfs.append(df3)
        else:
            print("DEBUG: Camera Annotation Events excluded from query")
        
        # Combine all dataframes
        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            df = df.groupby(['date', 'escalation_observation'])['count'].sum().reset_index()
            
            # Filter out "Camera Annotation Events" if exclude_camera is True (safety check)
            if exclude_camera:
                df = df[df['escalation_observation'] != 'Camera Annotation Events'].copy()
            
            df = df.sort_values(['date', 'escalation_observation'])
            return df
        else:
            return pd.DataFrame()

# OAuth flow function - COMMENTED OUT FOR DIRECT ACCESS
# def get_google_flow():
#     """Create and return a Google OAuth flow with timeout configuration"""
#     client_config = {
#         "web": {
#             "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET,
#             "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#             "token_uri": "https://oauth2.googleapis.com/token",
#             "redirect_uris": [REDIRECT_URI]
#         }
#     }
#     flow = Flow.from_client_config(
#         client_config,
#         scopes=SCOPES,
#         redirect_uri=REDIRECT_URI
#     )
#     # Configure timeout on the underlying requests session
#     # This prevents the request from hanging indefinitely
#     if hasattr(flow, 'oauth2session') and hasattr(flow.oauth2session, 'request'):
#         # Set default timeout for requests made by this session
#         original_request = flow.oauth2session.request
#         def request_with_timeout(*args, **kwargs):
#             if 'timeout' not in kwargs:
#                 kwargs['timeout'] = (10, 30)  # (connect timeout, read timeout) in seconds
#             return original_request(*args, **kwargs)
#         flow.oauth2session.request = request_with_timeout
#     return flow

# OAuth login route - COMMENTED OUT FOR DIRECT ACCESS
# @app.route('/login')
# def login():
#     """Login page - redirects to Google OAuth"""
#     # If already logged in, redirect to dashboard
#     if current_user.is_authenticated:
#         return redirect(url_for('index'))
#     
#     # If OAuth not configured, show error
#     if not CLIENT_ID or not CLIENT_SECRET:
#         response = make_response(render_template('error.html', 
#                               error_title='OAuth Not Configured',
#                               error_message='Google OAuth credentials are not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.'))
#         response.status_code = 500
#         return response
#     
#     # Validate redirect URI
#     if not REDIRECT_URI:
#         response = make_response(render_template('error.html', 
#                               error_title='Configuration Error',
#                               error_message='REDIRECT_URI is not configured. Please set it in your .env file.'))
#         response.status_code = 500
#         return response
#     
#     # Debug logging
#     print(f"OAuth Login - Redirect URI: {REDIRECT_URI}")
#     print(f"OAuth Login - Client ID: {CLIENT_ID[:20]}...")
#     
#     # Clear any existing state from previous login attempts to prevent conflicts
#     remnant_state = session.get('state')
#     if remnant_state:
#         print(f"⚠️ Found previous state in session: {remnant_state[:20]}... (clearing it)")
#         session.pop('state', None)
#         session.pop('oauth_start_time', None)
#     
#     # Make session permanent to ensure it persists across the OAuth flow
#     session.permanent = True
#     session.modified = True  # Mark session as modified to force save
#     
#     # Initiate OAuth flow
#     try:
#         flow = get_google_flow()
#         authorization_url, state = flow.authorization_url(
#             access_type='offline',
#             include_granted_scopes='true',
#             prompt='select_account'
#         )
#         session['state'] = state
#         session['oauth_start_time'] = datetime.now().isoformat()
#         # Force session save to ensure state persists across redirect
#         session.permanent = True
#         session.modified = True
#         
#         print(f"Generated new state: {state[:20]}...")
#         print(f"Generated authorization URL (first 100 chars): {authorization_url[:100]}...")
#         
#         # Create response and ensure session is saved
#         response = redirect(authorization_url)
#         # Explicitly save session by ensuring it's in the response
#         # Flask will automatically save the session when response is returned
#         # But we need to make sure session is marked as modified
#         return response
#     except Exception as e:
#         print(f"Error generating authorization URL: {str(e)}")
#         response = make_response(render_template('error.html',
#                               error_title='OAuth Configuration Error',
#                               error_message=f'Failed to generate authorization URL: {str(e)}. Please check your OAuth credentials and redirect URI configuration.'))
#         response.status_code = 500
#         return response

@app.route('/login-page')
def login_page():
    """Show login page template - Redirects to index since OAuth is disabled"""
    # Redirect directly to index since authentication is disabled
    return redirect(url_for('index'))

# OAuth callback route - COMMENTED OUT FOR DIRECT ACCESS
# @app.route('/callback')
# def callback():
#     """Handle Google OAuth callback"""
#     # Check for OAuth errors first
#     if 'error' in request.args:
#         error_msg = request.args.get('error_description', request.args.get('error', 'Authentication failed.'))
#         response = make_response(render_template('error.html',
#                               error_title='Authentication Error',
#                               error_message=error_msg))
#         response.status_code = 403
#         return response
    
    # Check if code is present
#    if 'code' not in request.args:
#        response = make_response(render_template('error.html',
#                              error_title='Missing Authorization Code',
#                              error_message='No authorization code received from Google. Please try logging in again.'))
#        response.status_code = 400
#        return response
    
    # Check session state
#    if 'state' not in session:
#        response = make_response(render_template('error.html',
#                              error_title='Session Error',
#                              error_message='Session expired. Please try logging in again.'))
#        response.status_code = 400
#        return response
    
    # Verify state parameter (CRITICAL: Must match exactly)
#    request_state = request.args.get('state')
#    session_state = session.get('state')
    
#    if request_state != session_state:
#        print(f"❌ State mismatch detected!")
#        print(f"   Request state: '{request_state}'")
#        print(f"   Session state: '{session_state}'")
#        print(f"   Session keys: {list(session.keys())}")
#        print(f"   OAuth start time: {session.get('oauth_start_time', 'Not found')}")
        
        # Check if this is an old callback from a previous login attempt
#        oauth_start_time_str = session.get('oauth_start_time')
#        if oauth_start_time_str:
#            try:
#                from datetime import datetime
#                start_time = datetime.fromisoformat(oauth_start_time_str)
#                elapsed = (datetime.now() - start_time).total_seconds()
#                print(f"   Time since OAuth start: {elapsed:.1f} seconds")
#                if elapsed > 300:  # 5 minutes
#                    print(f"   ⚠️ This appears to be a very old OAuth attempt ({elapsed:.0f} seconds ago)")
#            except:
#                pass
        
        # Provide helpful error message with troubleshooting steps
#        error_message = """<strong>Invalid state parameter - Session Mismatch</strong><br><br>This usually means the OAuth callback state doesn't match the session state.<br><br><strong>Common causes:</strong><br>• Multiple browser tabs/windows open (one with old login attempt)<br>• Session cookies were cleared between login and callback<br>• Previous login attempt still completing<br><br><strong>To fix:</strong><br>1. <strong>Close ALL browser tabs</strong> for localhost:5000<br>2. Clear browser cookies for localhost<br>3. Open a fresh browser window/tab<br>4. Try logging in again (click login only once)<br><br>If the problem persists, try using an incognito/private browser window."""
#        response = make_response(render_template('error.html',
#                              error_title='Security Error - State Mismatch',
#                              error_message=error_message))
#        response.status_code = 400
        # Clear the stale state from session
#        session.pop('state', None)
#        session.pop('oauth_start_time', None)
#        return response
    
#    try:
        # Debug logging
#        print(f"\n=== OAuth Callback Debug ===")
#        print(f"Full callback URL: {request.url}")
#        print(f"Redirect URI configured in app: {REDIRECT_URI}")
#        print(f"Code parameter present: {'code' in request.args}")
#        print(f"State from request: {request.args.get('state', 'NOT PROVIDED')}")
#        print(f"State from session: {session.get('state', 'NOT IN SESSION')}")
#        print(f"Error from request (if any): {request.args.get('error', 'None')}")
#        print(f"Error description (if any): {request.args.get('error_description', 'None')}")
        
        # Check if Google returned an error
#        if 'error' in request.args:
#            error = request.args.get('error')
#            error_desc = request.args.get('error_description', 'No description provided')
#            print(f"\n❌ Google OAuth Error: {error}")
#            print(f"   Description: {error_desc}")
            
            # Provide specific guidance based on error type
#            if 'redirect_uri_mismatch' in error.lower():
#                guidance = f"""
#                REDIRECT URI MISMATCH ERROR
                
#                The redirect URI in your request does not match what's configured in Google Cloud Console.
                
#                Your app is configured with: {REDIRECT_URI}
                
#                To fix this:
#                1. Go to: https://console.cloud.google.com/apis/credentials
#                2. Find your OAuth 2.0 Client ID
#                3. Click Edit
#                4. Under "Authorized redirect URIs", add EXACTLY:
#                   {REDIRECT_URI}
                
#                5. Make sure:
#                   - No trailing slash
#                   - Protocol matches (http:// not https:// for localhost)
#                   - Port number matches (5000)
#                   - Case sensitive
                
#                6. Save and wait 1-2 minutes for changes to propagate
#                """
#                response = make_response(render_template('error.html',
#                                  error_title='Redirect URI Mismatch',
#                                  error_message=f'{error_desc}\n\n{guidance}'))
#                response.status_code = 400
#                return response
#            elif 'access_denied' in error.lower():
#                guidance = "You denied access to the application. Please try logging in again and grant permissions."
#                response = make_response(render_template('error.html',
#                                  error_title='Access Denied',
#                                  error_message=guidance))
#                response.status_code = 403
#                return response
#            else:
#                response = make_response(render_template('error.html',
#                                  error_title='OAuth Error',
#                                  error_message=f'{error}: {error_desc}'))
#                response.status_code = 400
#                return response
        
        # Create flow
#        flow = get_google_flow()
        
        # Fetch token from Google
#        print("🔄 Starting token exchange with Google...")
#        try:
#            import time
#            import socket
#            from requests.exceptions import ConnectionError, Timeout
            
            # Set socket timeout to prevent hanging
#            original_timeout = socket.getdefaulttimeout()
#            socket.setdefaulttimeout(30)  # 30 second timeout
            
#            start_time = time.time()
            
            # Retry logic for transient network/DNS errors
#            max_retries = 3
#            retry_count = 0
#            last_error = None
            
#            while retry_count < max_retries:
#                try:
                    # Create a fresh flow for each retry attempt if needed
#                    if retry_count > 0:
#                        flow = get_google_flow()
#                        print(f"   Retry attempt {retry_count}/{max_retries}...")
                    
                    # Direct fetch (timeout handled by requests library timeout configuration)
                    # The timeout is configured in get_google_flow() function (10s connect, 30s read)
#                    flow.fetch_token(authorization_response=request.url)
#                    elapsed = time.time() - start_time
#                    print(f"✅ Token exchange completed in {elapsed:.2f} seconds")
#                    credentials = flow.credentials
#                    break  # Success, exit retry loop
                    
#                except (socket.gaierror, ConnectionError, OSError, Timeout) as network_error:
#                    retry_count += 1
#                    last_error = network_error
#                    error_str = str(network_error).lower()
                    
#                    if 'name resolution' in error_str or 'name_not_resolved' in error_str or 'failed to resolve' in error_str:
#                        print(f"⚠️ DNS resolution error (attempt {retry_count}/{max_retries})")
#                        if retry_count < max_retries:
#                            wait_time = retry_count * 2  # Exponential backoff: 2s, 4s
#                            print(f"   Retrying in {wait_time} seconds...")
#                            time.sleep(wait_time)
#                        else:
#                            print(f"❌ DNS resolution failed after {max_retries} attempts")
#                            socket.setdefaulttimeout(original_timeout)
                            # Provide helpful error message
#                            guidance = """
#                            DNS resolution failure - cannot connect to Google OAuth servers.
                            
#                            This may be due to:
#                            1. Network connectivity issues
#                            2. DNS server problems  
#                            3. Firewall blocking outbound connections
#                            4. VPN/proxy configuration issues
                            
#                            Please check your network connection and try again.
#                            If the problem persists, contact your network administrator.
#                            """
#                            response = make_response(render_template('error.html',
#                                              error_title='Network Error - DNS Resolution Failed',
#                                              error_message=f'Cannot resolve oauth2.googleapis.com: {str(network_error)}\n\n{guidance}'))
#                            response.status_code = 503
#                            return response
#                    else:
                        # Other network errors
#                        if retry_count < max_retries:
#                            wait_time = retry_count * 2
#                            print(f"⚠️ Network error (attempt {retry_count}/{max_retries}): {str(network_error)[:100]}")
#                            print(f"   Retrying in {wait_time} seconds...")
#                            time.sleep(wait_time)
#                        else:
#                            print(f"❌ Network error after {max_retries} attempts")
#                            socket.setdefaulttimeout(original_timeout)
#                            raise
            
            # Restore original timeout
#            if 'original_timeout' in locals():
#                socket.setdefaulttimeout(original_timeout)
            
            # If we exhausted retries without success
#            if retry_count >= max_retries and last_error:
#                socket.setdefaulttimeout(original_timeout)
#                raise last_error
#        except Exception as token_error:
#            print(f"\n❌ Token fetch error: {str(token_error)}")
#            print(f"   Error type: {type(token_error).__name__}")
            
            # Check for specific error types
#            error_str = str(token_error).lower()
#            error_type = type(token_error).__name__
            
            # Handle timeout errors
#            if 'timeout' in error_str or error_type == 'Timeout':
#                guidance = """
#                Connection timeout - cannot reach Google OAuth servers.
                
#                This usually means:
#                1. Network is unreachable or very slow
#                2. Firewall is blocking outbound HTTPS connections
#                3. DNS is not resolving oauth2.googleapis.com
                
#                Please check:
#                • Your internet connection
#                • Firewall/VPN settings  
#                • Try: ping oauth2.googleapis.com
                
#                If the problem persists, contact your network administrator.
#                """
#                response = make_response(render_template('error.html',
#                                  error_title='Connection Timeout',
#                                  error_message=f'Request timed out: {str(token_error)}\n\n{guidance}'))
#                response.status_code = 504
#                return response
            
            # Handle DNS/network errors
#            if 'name resolution' in error_str or 'name_not_resolved' in error_str or 'failed to resolve' in error_str:
#                guidance = """
#                DNS resolution failure - cannot connect to Google OAuth servers.
                
#                Please check:
#                1. Your network connection is active
#                2. DNS servers are reachable (try: nslookup oauth2.googleapis.com)
#                3. No firewall is blocking outbound HTTPS connections
#                4. VPN/proxy settings are correct
                
#                Try again in a few moments. If the problem persists, contact your network administrator.
#                """
#                response = make_response(render_template('error.html',
#                                  error_title='Network Error',
#                                  error_message=f'DNS resolution failed: {str(token_error)}\n\n{guidance}'))
#                response.status_code = 503
#                return response
            
            # Handle insecure transport error (HTTP instead of HTTPS)
#            if 'insecure_transport' in error_str or error_type == 'InsecureTransportError':
                # Check if we're on localhost
#                if 'localhost' in REDIRECT_URI or '127.0.0.1' in REDIRECT_URI:
                    # This should not happen if OAUTHLIB_INSECURE_TRANSPORT is set correctly
#                    guidance = """
#                    OAuth requires HTTPS, but you're using HTTP on localhost.
                    
#                    The application should automatically enable insecure transport for localhost.
#                    If you see this error, please:
                    
#                    1. Ensure you're accessing via http://localhost:5000 (not https://)
#                    2. Restart the Flask server after any code changes
#                    3. Check that OAUTHLIB_INSECURE_TRANSPORT environment variable is set
                    
#                    Note: For production, you MUST use HTTPS.
#                    """
#                    response = make_response(render_template('error.html',
#                                      error_title='HTTPS Required Error',
#                                      error_message=guidance))
#                    response.status_code = 500
#                    return response
#                else:
#                    guidance = """
#                    OAuth requires HTTPS for security. You're accessing the application via HTTP.
                    
#                    Please access the application using HTTPS instead of HTTP.
#                    """
#                    response = make_response(render_template('error.html',
#                                      error_title='HTTPS Required',
#                                      error_message=guidance))
#                    response.status_code = 400
#                    return response
            # Check for redirect URI mismatch in the error
#            elif 'redirect_uri_mismatch' in error_str or 'redirect_uri' in error_str:
#                guidance = f"""
#                The redirect URI does not match Google Cloud Console settings.
                
#                Configured URI: {REDIRECT_URI}
                
#                Please verify in Google Cloud Console that this EXACT URI is listed
#                under "Authorized redirect URIs" (no trailing slash, correct protocol).
#                """
#                response = make_response(render_template('error.html',
#                                  error_title='Redirect URI Configuration Error',
#                                  error_message=guidance))
#                response.status_code = 400
#                return response
#            else:
#                raise  # Re-raise if it's a different error
        
        # Clear state from session after successful token exchange
#        session.pop('state', None)
        
#        print("🔄 Verifying ID token and fetching user info...")
#        import time
#        start_time = time.time()
        
#        credentials = flow.credentials
#        from google.oauth2 import id_token
#        from google.auth.transport import requests as google_requests
        
        # Verify and get user info
#        request_session = google_requests.Request()
#        idinfo = id_token.verify_oauth2_token(
#            credentials.id_token, request_session, CLIENT_ID)
        
#        elapsed = time.time() - start_time
#        print(f"✅ ID token verification completed in {elapsed:.2f} seconds")
        
#        email = idinfo.get('email')
#        name = idinfo.get('name', '')
#        user_id = idinfo.get('sub')
        
        # Check if email domain is allowed
#        if not email or not email.endswith(ALLOWED_DOMAIN):
#            response = make_response(render_template('error.html',
#                                  error_title='Access Denied',
#                                  error_message=f'Access is restricted to {ALLOWED_DOMAIN} email addresses. Your email ({email}) is not authorized.'))
#            response.status_code = 403
#            return response
        
        # Create user and log in
#        print(f"✅ User authenticated: {email} ({name})")
#        user = User(user_id, email, name)
#        session['user_id'] = user_id
#        session['user_email'] = email
#        session['user_name'] = name
#        login_user(user)
        
#        print("✅ Login successful, redirecting to dashboard...")
#        return redirect(url_for('index'))
    
#    except Exception as e:
#        import traceback
#        error_details = traceback.format_exc()
#        print(f"OAuth callback error: {str(e)}")
#        print(f"Error traceback: {error_details}")
        
        # Provide more specific error messages
#        error_message = str(e)
#        if 'redirect_uri_mismatch' in error_message.lower() or 'redirect_uri' in error_message.lower():
#            error_message = f'Redirect URI mismatch. Configured: {REDIRECT_URI}. Please ensure this exact URL is added in Google Cloud Console under Authorized redirect URIs.'
#        elif 'invalid_grant' in error_message.lower():
#            error_message = 'Invalid authorization code. This may happen if the code was already used or expired. Please try logging in again.'
#        elif 'invalid_client' in error_message.lower():
#            error_message = 'Invalid OAuth client. Please check your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in the .env file.'
        
#        response = make_response(render_template('error.html',
#                              error_title='Authentication Error',
#                              error_message=f'An error occurred during authentication: {error_message}'))
#        response.status_code = 500
#        return response

@app.route('/logout')
@login_required
def logout():
    """Log out the current user"""
    logout_user()
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/')
@login_required
def index():
    """Main dashboard page"""
    filter_options = get_filter_options()
    # Initial load with recent data only (last 3 months) for better performance
    # Note: get_monthly_data will use default 90 days if date='all', but we explicitly set it here for clarity
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    monthly_data = get_monthly_data('all', 'all', 'all', f'{start_date},{end_date}')
    
    # Create monthly trend chart
    monthly_trend = create_monthly_trend_chart(monthly_data)
    
    # Create escalation distribution chart
    escalation_dist = create_escalation_distribution_chart(monthly_data)
    
    return render_template('index.html', 
                         filter_options=filter_options,
                         monthly_trend=monthly_trend,
                         escalation_dist=escalation_dist,
                         current_user=current_user)

@app.route('/api/filter')
@login_required
def api_filter():
    """API endpoint for filtering data"""
    try:
        escalation = request.args.get('escalation', 'all')
        email = request.args.get('email', 'all')
        hospital = request.args.get('hospital', 'all')
        date = request.args.get('date', 'all')
        exclude_camera = request.args.get('exclude_camera', 'false').lower() == 'true'
        
        df = get_filtered_data(escalation, email, hospital, date, exclude_camera=exclude_camera)
        
        # Get columns to display based on escalation type
        if escalation != 'all' and escalation in ESCALATION_COLUMNS:
            display_columns = ESCALATION_COLUMNS[escalation]
            # Filter dataframe to only include available columns
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
        
        return jsonify({
            'table_html': table_html,
            'row_count': len(df_filtered),
            'columns': available_columns
        })
    except Exception as e:
        # Log the error and return JSON error response
        import traceback
        error_msg = str(e)
        print(f"Error in api_filter: {error_msg}")
        print(traceback.format_exc())
        
        return jsonify({
            'table_html': '<tr><td colspan="10" class="text-center text-danger">Error loading data. Please try again.</td></tr>',
            'row_count': 0,
            'columns': [],
            'error': error_msg
        }), 500

@app.route('/api/charts')
@login_required
def api_charts():
    """API endpoint for getting filtered chart data"""
    try:
        escalation = request.args.get('escalation', 'all')
        email = request.args.get('email', 'all')
        hospital = request.args.get('hospital', 'all')
        date = request.args.get('date', 'all')
        exclude_camera = request.args.get('exclude_camera', 'false').lower() == 'true'
        
        # URL decode and normalize escalation
        # Flask's request.args automatically decodes '+' to spaces, but unquote handles % encoding
        escalation = unquote(str(escalation)).strip()
        
        # Normalize escalation value for comparison (handle any encoding issues)
        escalation_normalized = escalation.strip()
        
        # Debug logging
        print(f"\n=== API CHARTS DEBUG ===")
        print(f"Received params - escalation: '{escalation}' (type: {type(escalation).__name__}, length: {len(escalation)}), email: '{email}', hospital: '{str(hospital)[:100]}...', date: '{date}', exclude_camera: {exclude_camera}")
        print(f"Escalation normalized: '{escalation_normalized}'")
        print(f"Escalation comparison - == 'all': {escalation_normalized == 'all'}, == 'Camera Annotation Events': {escalation_normalized == 'Camera Annotation Events'}, == 'Impact Cases': {escalation_normalized == 'Impact Cases'}, == 'Educating nurses': {escalation_normalized == 'Educating nurses'}, != 'all': {escalation_normalized != 'all'}")
        print(f"Escalation repr: {repr(escalation_normalized)}")
        
        # If exclude_camera is True and escalation is Camera Annotation Events, return empty charts
        if escalation_normalized == 'Camera Annotation Events' and exclude_camera:
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
            return jsonify({
                'monthly_trend': empty_chart,
                'escalation_dist': empty_chart,
                'nurse_wise_trend': empty_chart
            })
        
        if escalation_normalized == 'Camera Annotation Events':
            print("DEBUG: api_charts - Branch: Camera Annotation Events")
            # Create specialized camera events charts
            camera_dist = create_camera_events_charts(escalation_normalized, email, hospital, date)
            
            # Get monthly trend data
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera)
            monthly_trend = create_monthly_trend_chart(monthly_data)
            
            # Create nurse-wise month-on-month trend chart
            nurse_wise_trend = create_nurse_wise_trend_chart(email, hospital, date)
            
            return jsonify({
                'monthly_trend': monthly_trend,
                'escalation_dist': camera_dist,
                'nurse_wise_trend': nurse_wise_trend
            })
        elif escalation_normalized == 'Educating nurses':
            print("DEBUG: api_charts - Branch: Educating nurses")
            # Get monthly trend data
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera)
            monthly_trend = create_monthly_trend_chart(monthly_data)
            
            # Create escalation distribution chart
            escalation_dist = create_escalation_distribution_chart(monthly_data)
            
            # Create nurse-wise month-on-month trend chart for Educating nurses
            nurse_wise_trend = create_educating_nurses_nurse_wise_trend_chart(email, hospital, date)
            
            return jsonify({
                'monthly_trend': monthly_trend,
                'escalation_dist': escalation_dist,
                'nurse_wise_trend': nurse_wise_trend
            })
        elif escalation_normalized == 'Impact Cases':
            print("DEBUG: api_charts - Branch: Impact Cases")
            # Create specialized impact cases charts
            impact_dist = create_impact_cases_charts(escalation_normalized, email, hospital, date)
            
            # Get monthly trend data
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera)
            monthly_trend = create_monthly_trend_chart(monthly_data)
            
            return jsonify({
                'monthly_trend': monthly_trend,
                'escalation_dist': impact_dist
            })
        else:
            print(f"DEBUG: api_charts - Branch: else (escalation='{escalation_normalized}')")
            monthly_data = get_monthly_data(escalation_normalized, email, hospital, date, exclude_camera=exclude_camera)
            
            # Debug: Check what escalation types are in the data
            if not monthly_data.empty:
                unique_escalations = monthly_data['escalation_observation'].unique().tolist()
                print(f"DEBUG: Monthly data has {len(unique_escalations)} escalation types: {unique_escalations}")
            else:
                print("DEBUG: Monthly data is empty")
            
            # Create charts with filtered data
            monthly_trend = create_monthly_trend_chart(monthly_data)
            escalation_dist = create_escalation_distribution_chart(monthly_data)
            
            # Debug: Parse and check chart data
            monthly_trend_parsed = json.loads(monthly_trend)
            if monthly_trend_parsed.get('data'):
                chart_escalations = [trace.get('name') for trace in monthly_trend_parsed['data']]
                print(f"DEBUG: Chart will display {len(chart_escalations)} escalation types: {chart_escalations}")
            
            return jsonify({
                'monthly_trend': monthly_trend,
                'escalation_dist': escalation_dist
            })
    except Exception as e:
        # Log the error and return JSON error response
        import traceback
        error_msg = str(e)
        print(f"Error in api_charts: {error_msg}")
        print(traceback.format_exc())
        
        # Return empty charts on error
        empty_chart = json.dumps({
            'data': [],
            'layout': {
                'title': 'Error loading chart data',
                'font': {'family': 'Source Sans Pro', 'size': 12},
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white'
            }
        }, cls=plotly.utils.PlotlyJSONEncoder)
        
        return jsonify({
            'monthly_trend': empty_chart,
            'escalation_dist': empty_chart,
            'nurse_wise_trend': empty_chart,
            'error': error_msg
        }), 500

def create_camera_user_role_chart(email='all', hospital='all'):
    """Create camera events user role distribution chart"""
    where_conditions = []
    
    if email != 'all':
        escaped_email = escape_sql_string(email)
        where_conditions.append(f"user_email = '{escaped_email}'")
    
    # Build hospital condition using helper function
    hospital_condition = build_hospital_condition(hospital)
    if hospital_condition:
        where_conditions.append(hospital_condition)
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
    
    query = f"""
    SELECT 
        user_role,
        COUNT(*) as count
    FROM `prod-tech-project1-bv479-zo027.mongodb.camera_annotation_events`
    WHERE user_role IS NOT NULL 
    AND user_role != ''
    AND TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    AND {where_clause}
    GROUP BY user_role
    ORDER BY count DESC
    """
    
    df = client.query(query).result().to_dataframe()
    
    if df.empty:
        # Return empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title='User Role Distribution',
            xaxis_title='User Role',
            yaxis_title='Number of Events',
            font=dict(family='Source Sans Pro', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Create bar chart for user roles
    fig = go.Figure(data=[go.Bar(
        x=df['user_role'],
        y=df['count'],
        marker=dict(color='#1188C9'),
        text=df['count'],
        textposition='auto'
    )])
    
    fig.update_layout(
        title='User Role Distribution',
        xaxis_title='User Role',
        yaxis_title='Number of Events',
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_camera_events_charts(escalation='all', email='all', hospital='all', date='all'):
    """Create specialized charts for camera annotation events"""
    where_conditions = []
    
    if email != 'all':
        escaped_email = escape_sql_string(email)
        where_conditions.append(f"user_email = '{escaped_email}'")
    
    # Build hospital condition using helper function
    hospital_condition = build_hospital_condition(hospital)
    if hospital_condition:
        where_conditions.append(hospital_condition)
    
    # Handle date range filtering
    if date != 'all' and ',' in date:
        start_date, end_date = date.split(',')
        where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
    elif date != 'all':
        where_conditions.append(f"DATE(timestamp) = '{date}'")
    else:
        # Default to recent data (last 30 days) if no date specified
        where_conditions.append("TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)")
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "TIMESTAMP_TRUNC(timestamp, DAY) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
    
    # Get camera events data
    query = f"""
    SELECT 
        event_name,
        user_role,
        unit_name,
        COUNT(*) as count
    FROM `prod-tech-project1-bv479-zo027.mongodb.camera_annotation_events`
    WHERE event_name IS NOT NULL 
    AND event_name != ''
    AND {where_clause}
    GROUP BY event_name, user_role, unit_name
    ORDER BY count DESC
    """
    
    df = client.query(query).result().to_dataframe()
    
    if df.empty:
        # Return empty charts if no data
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title='No Camera Events Data',
            font=dict(family='Source Sans Pro', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return json.dumps(empty_fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Create event name distribution chart
    event_counts = df.groupby('event_name')['count'].sum().reset_index()
    event_counts = event_counts.sort_values('count', ascending=False)
    
    # Get top 5 + others
    if len(event_counts) > 5:
        top_5 = event_counts.head(5)
        others_count = event_counts.iloc[5:]['count'].sum()
        if others_count > 0:
            others_row = pd.DataFrame({
                'event_name': ['Others'],
                'count': [others_count]
            })
            final_data = pd.concat([top_5, others_row], ignore_index=True)
        else:
            final_data = top_5
    else:
        final_data = event_counts
    
    colors = ['#1188C9', '#0253a5', '#5f4987', '#dcb695', '#dcb695', '#1188C9']
    
    fig = go.Figure(data=[go.Pie(
        labels=final_data['event_name'],
        values=final_data['count'],
        marker=dict(colors=colors[:len(final_data)]),
        textinfo='label+percent',
        textfont=dict(family='Source Sans Pro', size=12)
    )])
    
    fig.update_layout(
        title='Camera Events Distribution (Top 5 + Others)',
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_nurse_wise_trend_chart(email='all', hospital='all', date='all'):
    """Create nurse-wise month-on-month trend chart for camera annotations"""
    where_conditions = []
    
    if email != 'all':
        escaped_email = escape_sql_string(email)
        where_conditions.append(f"user_email = '{escaped_email}'")
    
    # Build hospital condition using helper function
    hospital_condition = build_hospital_condition(hospital)
    if hospital_condition:
        where_conditions.append(hospital_condition)
    
    # Handle date range filtering
    if date != 'all' and ',' in date:
        start_date, end_date = date.split(',')
        where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
    elif date != 'all':
        where_conditions.append(f"DATE(timestamp) = '{date}'")
    # When date='all', don't apply any date filter - show all historical data
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Query to get nurse-wise monthly data
    query = f"""
    SELECT 
        EXTRACT(YEAR FROM timestamp) as year,
        EXTRACT(MONTH FROM timestamp) as month,
        user_email as nurse_email,
        COUNT(*) as count
    FROM `prod-tech-project1-bv479-zo027.mongodb.camera_annotation_events`
    WHERE user_email IS NOT NULL 
    AND user_email != ''
    AND {where_clause}
    GROUP BY year, month, user_email
    ORDER BY year, month, user_email
    """
    
    df = client.query(query).result().to_dataframe()
    
    if df.empty:
        # Return empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title='Nurse-wise Month-on-Month Trend',
            xaxis_title='Month',
            yaxis_title='Number of Camera Annotations',
            font=dict(family='Source Sans Pro', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Sort data by year and month
    df = df.sort_values(['year', 'month', 'nurse_email'])
    
    # Create month labels with month names
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    df['month_label'] = df.apply(
        lambda x: f"{month_names[int(x['month'])]} {int(x['year'])}", axis=1
    )
    
    # Get unique nurses
    unique_nurses = df['nurse_email'].unique()
    
    # Color palette for nurses
    colors = [
        '#1188C9', '#0253a5', '#5f4987', '#dcb695',
        '#4BA8E8', '#3B8FD8', '#7B6AA5', '#F2D6B8',
        '#0D6B9F', '#01387A', '#3E2F5A', '#B8966F',
        '#2D9FD4', '#1B6FBF', '#6B5A97', '#E6C9A5',
        '#1A9BC9', '#0369C9', '#6F5A9F', '#D4B687',
        '#3CA8D9', '#045EA9', '#8068B0', '#E8D1A3',
        '#28B5E5', '#0257A3', '#7560A8', '#DFC28F',
        '#5BB8E0', '#0840A0', '#8A70BA', '#F0D99F'
    ]
    
    traces = []
    # Collect all counts across all months for global SD and median calculation
    all_counts = []
    for _, row in df.iterrows():
        all_counts.append(row['count'])
    
    # Calculate single median and +3 SD across entire date range
    # Sort months by year-month (not alphabetically) to preserve chronological order
    month_year_pairs = df[['year', 'month', 'month_label']].drop_duplicates()
    month_year_pairs = month_year_pairs.sort_values(['year', 'month'])
    months_sorted = month_year_pairs['month_label'].tolist()
    
    if len(all_counts) > 0:
        global_median = np.median(all_counts)
        global_mean = np.mean(all_counts)
        global_std = np.std(all_counts) if len(all_counts) > 1 else 0
        global_sd_3 = global_mean + 3 * global_std
    else:
        global_median = 0
        global_sd_3 = 0
    
    # Create constant values for horizontal lines across all months
    median_values = [global_median] * len(months_sorted)
    sd_3_values = [global_sd_3] * len(months_sorted)
    
    for i, nurse in enumerate(unique_nurses):
        nurse_data = df[df['nurse_email'] == nurse].sort_values(['year', 'month'])
        color = colors[i % len(colors)]
        
        # Get display name (just the part before @ for cleaner display)
        display_name = nurse.split('@')[0] if '@' in nurse else nurse
        
        traces.append(go.Scatter(
            x=nurse_data['month_label'],
            y=nurse_data['count'],
            mode='lines+markers',
            name=display_name,
            line=dict(color=color, width=2.5),
            marker=dict(size=7, symbol='circle'),
            hovertemplate=f'<b>{nurse}</b><br>Month: %{{x}}<br>Count: %{{y}}<extra></extra>'
        ))
    
    # Add median line (horizontal constant value)
    traces.append(go.Scatter(
        x=months_sorted,
        y=median_values,
        mode='lines',
        name='Median',
        line=dict(color='red', width=2.5, dash='dash'),
        hovertemplate='<b>Median</b><br>Month: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    # Add +3 SD line (horizontal constant value)
    traces.append(go.Scatter(
        x=months_sorted,
        y=sd_3_values,
        mode='lines',
        name='+3 SD',
        line=dict(color='orange', width=2.5, dash='dot'),
        hovertemplate='<b>+3 SD</b><br>Month: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text='Nurse-wise Month-on-Month Trend (Camera Annotations)', font=dict(size=18, family='Source Sans Pro', color='#0253a5')),
        xaxis=dict(
            title='Month',
            tickangle=-45,
            showgrid=True,
            gridcolor='#E0E0E0',
            type='category',
            categoryorder='array',
            categoryarray=months_sorted
        ),
        yaxis=dict(
            title='Number of Camera Annotations',
            showgrid=True,
            gridcolor='#E0E0E0'
        ),
        hovermode='closest',
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=500,
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            font=dict(size=10)
        ),
        margin=dict(l=80, r=150, t=80, b=100)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_educating_nurses_nurse_wise_trend_chart(email='all', hospital='all', date='all'):
    """Create nurse-wise month-on-month trend chart for Educating nurses escalation"""
    where_conditions = []
    
    # Always filter for Educating nurses escalation
    where_conditions.append("TRIM(escalation_observation) = 'Educating nurses'")
    
    if email != 'all':
        escaped_email = escape_sql_string(email)
        where_conditions.append(f"email_address = '{escaped_email}'")
    
    # Build hospital condition using helper function
    hospital_condition = build_hospital_condition(hospital)
    if hospital_condition:
        where_conditions.append(hospital_condition)
    
    # Handle date range filtering
    if date != 'all' and ',' in date:
        start_date, end_date = date.split(',')
        where_conditions.append(f"DATE(timestamp) >= '{start_date}' AND DATE(timestamp) <= '{end_date}'")
    elif date != 'all':
        where_conditions.append(f"DATE(timestamp) = '{date}'")
    # When date='all', don't apply any date filter - show all historical data
    
    where_clause = " AND ".join(where_conditions)
    
    # Query to get nurse-wise monthly data
    query = f"""
    SELECT 
        EXTRACT(YEAR FROM timestamp) as year,
        EXTRACT(MONTH FROM timestamp) as month,
        email_address as nurse_email,
        COUNT(*) as count
    FROM `prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data`
    WHERE email_address IS NOT NULL 
    AND email_address != ''
    AND {where_clause}
    GROUP BY year, month, email_address
    ORDER BY year, month, email_address
    """
    
    df = client.query(query).result().to_dataframe()
    
    if df.empty:
        # Return empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title='Nurse-wise Month-on-Month Trend',
            xaxis_title='Month',
            yaxis_title='Number of Educating Nurses Events',
            font=dict(family='Source Sans Pro', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Sort data by year and month
    df = df.sort_values(['year', 'month', 'nurse_email'])
    
    # Create month labels with month names
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    df['month_label'] = df.apply(
        lambda x: f"{month_names[int(x['month'])]} {int(x['year'])}", axis=1
    )
    
    # Get unique nurses
    unique_nurses = df['nurse_email'].unique()
    
    # Color palette for nurses
    colors = [
        '#1188C9', '#0253a5', '#5f4987', '#dcb695',
        '#4BA8E8', '#3B8FD8', '#7B6AA5', '#F2D6B8',
        '#0D6B9F', '#01387A', '#3E2F5A', '#B8966F',
        '#2D9FD4', '#1B6FBF', '#6B5A97', '#E6C9A5',
        '#1A9BC9', '#0369C9', '#6F5A9F', '#D4B687',
        '#3CA8D9', '#045EA9', '#8068B0', '#E8D1A3',
        '#28B5E5', '#0257A3', '#7560A8', '#DFC28F',
        '#5BB8E0', '#0840A0', '#8A70BA', '#F0D99F'
    ]
    
    traces = []
    # Collect all counts across all months for global SD and median calculation
    all_counts = []
    for _, row in df.iterrows():
        all_counts.append(row['count'])
    
    # Calculate single median and +3 SD across entire date range
    # Sort months by year-month (not alphabetically) to preserve chronological order
    month_year_pairs = df[['year', 'month', 'month_label']].drop_duplicates()
    month_year_pairs = month_year_pairs.sort_values(['year', 'month'])
    months_sorted = month_year_pairs['month_label'].tolist()
    
    if len(all_counts) > 0:
        global_median = np.median(all_counts)
        global_mean = np.mean(all_counts)
        global_std = np.std(all_counts) if len(all_counts) > 1 else 0
        global_sd_3 = global_mean + 3 * global_std
    else:
        global_median = 0
        global_sd_3 = 0
    
    # Create constant values for horizontal lines across all months
    median_values = [global_median] * len(months_sorted)
    sd_3_values = [global_sd_3] * len(months_sorted)
    
    for i, nurse in enumerate(unique_nurses):
        nurse_data = df[df['nurse_email'] == nurse].sort_values(['year', 'month'])
        color = colors[i % len(colors)]
        
        # Get display name (just the part before @ for cleaner display)
        display_name = nurse.split('@')[0] if '@' in nurse else nurse
        
        traces.append(go.Scatter(
            x=nurse_data['month_label'],
            y=nurse_data['count'],
            mode='lines+markers',
            name=display_name,
            line=dict(color=color, width=2.5),
            marker=dict(size=7, symbol='circle'),
            hovertemplate=f'<b>{nurse}</b><br>Month: %{{x}}<br>Count: %{{y}}<extra></extra>'
        ))
    
    # Add median line (horizontal constant value)
    traces.append(go.Scatter(
        x=months_sorted,
        y=median_values,
        mode='lines',
        name='Median',
        line=dict(color='red', width=2.5, dash='dash'),
        hovertemplate='<b>Median</b><br>Month: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    # Add +3 SD line (horizontal constant value)
    traces.append(go.Scatter(
        x=months_sorted,
        y=sd_3_values,
        mode='lines',
        name='+3 SD',
        line=dict(color='orange', width=2.5, dash='dot'),
        hovertemplate='<b>+3 SD</b><br>Month: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text='Nurse-wise Month-on-Month Trend (Educating Nurses)', font=dict(size=18, family='Source Sans Pro', color='#0253a5')),
        xaxis=dict(
            title='Month',
            tickangle=-45,
            showgrid=True,
            gridcolor='#E0E0E0',
            type='category',
            categoryorder='array',
            categoryarray=months_sorted
        ),
        yaxis=dict(
            title='Number of Educating Nurses Events',
            showgrid=True,
            gridcolor='#E0E0E0'
        ),
        hovermode='closest',
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=500,
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            font=dict(size=10)
        ),
        margin=dict(l=80, r=150, t=80, b=100)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_impact_score_chart(email='all', hospital='all'):
    """Create impact score distribution chart"""
    where_conditions = []
    
    if email != 'all':
        where_conditions.append(f"email_address = '{email}'")
    
    # Build hospital condition using helper function
    hospital_condition = build_hospital_condition(hospital)
    if hospital_condition:
        where_conditions.append(hospital_condition)
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    query = f"""
    SELECT 
        impact_score,
        COUNT(*) as count
    FROM `prod-tech-project1-bv479-zo027.gsheet_data.impact_cases`
    WHERE impact_score IS NOT NULL 
    AND {where_clause}
    GROUP BY impact_score
    ORDER BY impact_score DESC
    """
    
    df = client.query(query).result().to_dataframe()
    
    if df.empty:
        # Return empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title='Impact Score Distribution',
            xaxis_title='Impact Score',
            yaxis_title='Number of Cases',
            font=dict(family='Source Sans Pro', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Create bar chart for impact scores
    fig = go.Figure(data=[go.Bar(
        x=df['impact_score'],
        y=df['count'],
        marker=dict(color='#1188C9'),
        text=df['count'],
        textposition='auto'
    )])
    
    fig.update_layout(
        title='Impact Score Distribution',
        xaxis_title='Impact Score',
        yaxis_title='Number of Cases',
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_impact_cases_charts(escalation='all', email='all', hospital='all', date='all'):
    """Create specialized charts for impact cases"""
    where_conditions = []
    
    if email != 'all':
        where_conditions.append(f"email_address = '{email}'")
    
    # Build hospital condition using helper function
    hospital_condition = build_hospital_condition(hospital)
    if hospital_condition:
        where_conditions.append(hospital_condition)
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Get impact cases data
    query = f"""
    SELECT 
        impact_type,
        impact_score,
        impact_rating,
        bed_name_score,
        eagle_score,
        COUNT(*) as count
    FROM `prod-tech-project1-bv479-zo027.gsheet_data.impact_cases`
    WHERE impact_type IS NOT NULL 
    AND impact_type != ''
    AND {where_clause}
    GROUP BY impact_type, impact_score, impact_rating, bed_name_score, eagle_score
    ORDER BY impact_score DESC
    """
    
    df = client.query(query).result().to_dataframe()
    
    if df.empty:
        # Return empty charts if no data
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title='No Impact Cases Data',
            font=dict(family='Source Sans Pro', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return json.dumps(empty_fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Create impact type distribution chart
    impact_counts = df.groupby('impact_type')['count'].sum().reset_index()
    impact_counts = impact_counts.sort_values('count', ascending=False)
    
    # Get top 5 + others
    if len(impact_counts) > 5:
        top_5 = impact_counts.head(5)
        others_count = impact_counts.iloc[5:]['count'].sum()
        if others_count > 0:
            others_row = pd.DataFrame({
                'impact_type': ['Others'],
                'count': [others_count]
            })
            final_data = pd.concat([top_5, others_row], ignore_index=True)
        else:
            final_data = top_5
    else:
        final_data = impact_counts
    
    colors = ['#1188C9', '#0253a5', '#5f4987', '#dcb695', '#dcb695', '#1188C9']
    
    fig = go.Figure(data=[go.Pie(
        labels=final_data['impact_type'],
        values=final_data['count'],
        marker=dict(colors=colors[:len(final_data)]),
        textinfo='label+percent',
        textfont=dict(family='Source Sans Pro', size=12)
    )])
    
    fig.update_layout(
        title='Impact Cases Distribution (Top 5 + Others)',
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_monthly_trend_chart(monthly_data):
    """Create monthly trend chart"""
    if monthly_data.empty:
        # Return empty chart if no data
        fig = go.Figure()
        fig.update_layout(
            title='Monthly Escalation Trends',
            xaxis_title='Month',
            yaxis_title='Number of Escalations',
            font=dict(family='Source Sans Pro', size=12),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Ensure date column is datetime type
    monthly_data['date'] = pd.to_datetime(monthly_data['date'])
    monthly_data_sorted = monthly_data.sort_values('date').copy()
    
    # Pivot data for chart using date as index (already monthly aggregated)
    pivot_data = monthly_data_sorted.pivot_table(
        index='date', 
        columns='escalation_observation', 
        values='count', 
        fill_value=0,
        aggfunc='sum'
    ).reset_index()
    
    # Sort pivot data by date
    pivot_data = pivot_data.sort_values('date')
    
    # Get all unique dates (these are now month-start dates)
    dates_list = pivot_data['date'].tolist()
    
    # Create month labels for x-axis ticks
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    # Since dates are already month-start dates, create labels directly
    month_starts = dates_list
    month_labels = [f"{month_names[date.month]} {date.year}" for date in dates_list]
    
    traces = []
    # Extended color palette with variations of base colors and complementary colors
    # Base colors: #1188C9 (blue), #0253a5 (dark blue), #5f4987 (purple), #dcb695 (tan)
    colors = [
        '#1188C9',  # Base blue
        '#0253a5',  # Base dark blue
        '#5f4987',  # Base purple
        '#dcb695',  # Base tan
        # Lighter variations
        '#4BA8E8', '#3B8FD8', '#7B6AA5', '#F2D6B8',
        # Darker variations
        '#0D6B9F', '#01387A', '#3E2F5A', '#B8966F',
        # Medium variations
        '#2D9FD4', '#1B6FBF', '#6B5A97', '#E6C9A5',
        # Additional complementary colors (still harmonious with palette)
        '#1A9BC9', '#0369C9', '#6F5A9F', '#D4B687',
        '#3CA8D9', '#045EA9', '#8068B0', '#E8D1A3',
        '#28B5E5', '#0257A3', '#7560A8', '#DFC28F',
        '#5BB8E0', '#0840A0', '#8A70BA', '#F0D99F',
        '#47A8D1', '#063399', '#775FA5', '#E3CC9B',
        # More variations
        '#1199D0', '#0256A8', '#625A9A', '#D9C091',
        '#2FA5D6', '#0452A6', '#6D5CA2', '#E5CE96',
        '#1CA0CE', '#0248A1', '#6858A0', '#DDC595',
        '#39ABDC', '#0559AB', '#735CA6', '#E7D09A'
    ]
    
    # Line styles for additional differentiation
    line_styles = ['solid', 'dash', 'dot', 'dashdot']
    
    # Marker symbols for additional differentiation
    marker_symbols = ['circle', 'square', 'diamond', 'triangle-up', 'triangle-down', 
                     'pentagon', 'hexagon', 'star', 'cross', 'x']
    
    # Get escalation columns (exclude date)
    escalation_columns = [col for col in pivot_data.columns if col != 'date']
    
    # Collect all values for SD and median calculation across all escalations
    import numpy as np
    all_values = []
    
    for i, escalation in enumerate(escalation_columns):
        color = colors[i % len(colors)]
        line_style = line_styles[(i // len(colors)) % len(line_styles)]
        marker_symbol = marker_symbols[(i // (len(colors) * len(line_styles))) % len(marker_symbols)]
        
        # Adjust line width based on style for better visibility
        line_width = 2.5
        
        # Create line dictionary with dash style only if not solid
        line_dict = dict(color=color, width=line_width)
        if line_style != 'solid':
            line_dict['dash'] = line_style
        
        # Get values for this escalation
        escalation_values = pivot_data[escalation].tolist()
        all_values.extend([v for v in escalation_values if v > 0])  # Exclude zeros for global calculation
        
        traces.append(go.Scatter(
            x=pivot_data['date'],
            y=escalation_values,
            mode='lines+markers',
            name=escalation,
            line=line_dict,
            marker=dict(size=7, symbol=marker_symbol)
        ))
    
    # Calculate single global median and +3 SD for entire period
    if len(all_values) > 0:
        global_median = np.median(all_values)
        global_mean = np.mean(all_values)
        global_std = np.std(all_values) if len(all_values) > 1 else 0
        global_sd_3 = global_mean + 3 * global_std
    else:
        global_median = 0
        global_sd_3 = 0
    
    # Create constant values for horizontal lines across all dates
    median_values = [global_median] * len(dates_list)
    sd_3_values = [global_sd_3] * len(dates_list)
    
    # Add median line (horizontal constant value)
    traces.append(go.Scatter(
        x=dates_list,
        y=median_values,
        mode='lines',
        name='Median',
        line=dict(color='red', width=2.5, dash='dash'),
        hovertemplate='<b>Median</b><br>Date: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    # Add +3 SD line (horizontal constant value)
    traces.append(go.Scatter(
        x=dates_list,
        y=sd_3_values,
        mode='lines',
        name='+3 SD',
        line=dict(color='orange', width=2.5, dash='dot'),
        hovertemplate='<b>+3 SD</b><br>Date: %{x}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text='Monthly Escalation Trends', font=dict(size=18, family='Source Sans Pro', color='#0253a5')),
        xaxis=dict(
            title='Month',
            tickangle=-45,
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            zeroline=False,
            type='date',
            tickmode='array',
            tickvals=month_starts,
            ticktext=month_labels,
            tickformat='%B %Y'
        ),
        yaxis=dict(
            title='Number of Escalations',
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1
        ),
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        height=700,
        margin=dict(l=80, r=200, t=100, b=120),
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            font=dict(size=9, family='Source Sans Pro'),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#1188C9',
            borderwidth=1,
            itemwidth=30
        )
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_escalation_distribution_chart(monthly_data):
    """Create escalation distribution pie chart with top 5 + Others"""
    escalation_counts = monthly_data.groupby('escalation_observation')['count'].sum().reset_index()
    
    # Sort by count descending and get top 5
    escalation_counts = escalation_counts.sort_values('count', ascending=False)
    
    if len(escalation_counts) > 5:
        # Get top 5
        top_5 = escalation_counts.head(5)
        
        # Calculate others count
        others_count = escalation_counts.iloc[5:]['count'].sum()
        
        # Create final data with top 5 + others
        final_data = top_5.copy()
        if others_count > 0:
            others_row = pd.DataFrame({
                'escalation_observation': ['Others'],
                'count': [others_count]
            })
            final_data = pd.concat([final_data, others_row], ignore_index=True)
    else:
        final_data = escalation_counts
    
    colors = ['#1188C9', '#0253a5', '#5f4987', '#dcb695', '#dcb695', '#1188C9']
    
    fig = go.Figure(data=[go.Pie(
        labels=final_data['escalation_observation'],
        values=final_data['count'],
        marker=dict(colors=colors[:len(final_data)], line=dict(color='white', width=2)),
        textinfo='label+percent',
        textfont=dict(family='Source Sans Pro', size=11),
        hole=0,
        textposition='outside',
        automargin=True
    )])
    
    fig.update_layout(
        title=dict(text='Escalation Distribution (Top 5 + Others)', font=dict(size=16, family='Source Sans Pro')),
        font=dict(family='Source Sans Pro', size=12),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=500,
        margin=dict(l=50, r=50, t=80, b=50),
        showlegend=True,
        legend=dict(
            orientation='v',
            yanchor='middle',
            y=0.5,
            xanchor='right',
            x=1.15,
            font=dict(size=11)
        )
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development' or os.getenv('ENVIRONMENT') == 'development'
    # Disable reloader when running in background (nohup/detached) to prevent process issues
    use_reloader = debug and os.isatty(0)  # Only use reloader if running in foreground terminal
    app.run(debug=debug, host='0.0.0.0', port=port, use_reloader=use_reloader)
