# Nursing Pod Quality Dashboard

A comprehensive Flask-based web application for monitoring and analyzing nursing pod quality data from BigQuery.

## Features

### 🎯 **Dynamic Filtering System**
- **Escalation Type Filter**: Filter by specific escalation types (Lab abnormality, Vitals abnormality, Nursing care, etc.)
- **Nurse Email Filter**: Filter by specific nurse email addresses
- **Hospital Filter**: Filter by hospital names
- **Date Filter**: Filter by specific dates with calendar dropdown
- **Default Selection**: All filters default to "All" for comprehensive view

### 📊 **Interactive Data Visualization**
- **Monthly Trend Charts**: Line graphs showing escalation trends over time
- **Escalation Distribution**: Pie charts showing distribution of escalation types
- **Real-time Updates**: Charts update based on applied filters

### 📋 **Dynamic Table Display**
- **Smart Column Selection**: Only displays relevant columns based on selected escalation type
- **Hardcoded Column Mappings**: Each escalation type has predefined relevant columns
- **Responsive Design**: Tables adapt to different screen sizes
- **Interactive Elements**: Clickable patient links, status badges

### 🎨 **Custom Styling**
- **Fonts**: Source Sans Pro (body text) and Playfair Display (headings)
- **Color Scheme**: 
  - Primary Blue: #1188C9
  - Dark Blue: #0253a5
  - Purple: #5f4987
  - Gold: #dcb695
- **Modern UI**: Gradient backgrounds, hover effects, smooth animations

## Escalation Types & Column Mappings

### Lab Abnormality
- timestamp, email_address, nurse_on_shift, hospital_name
- escalation_observation, bedside_staff_name, intervention_advised
- communication_method, intervention_status, recommend_icu_move
- patient_moved_to_icu, reason_not_moved, patient_handover_completed
- comments, patient_link

### Vitals Abnormality
- timestamp, email_address, nurse_on_shift, hospital_name
- escalation_observation, bedside_staff_name, intervention_advised
- communication_method, intervention_status, recommend_icu_move
- who_recommended_icu_move, patient_moved_to_icu, reason_not_moved
- workspace_moved_to, patient_handover_completed, concerns_feedback
- comments, patient_link

### Nursing Care
- timestamp, email_address, nurse_on_shift, hospital_name
- escalation_observation, bedside_staff_name, intervention_advised
- communication_method, intervention_status, recommend_icu_move
- patient_moved_to_icu, reason_not_moved, patient_handover_completed
- comments, patient_link

### Educating Nurses
- timestamp, email_address, nurse_on_shift, hospital_name
- escalation_observation, bedside_staff_name, intervention_advised
- communication_method, intervention_status, training_session_image
- issue_details, session_attendees, teaching_session_screenshot
- session_topic, score, issues, patient_link

### And more escalation types with their specific column mappings...

## Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Google Cloud Authentication**:
   ```bash
   gcloud auth application-default login
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```

4. **Access the Dashboard**:
   Open your browser and navigate to `http://localhost:5000`

## Usage

1. **Apply Filters**: Use the dropdown filters to narrow down data
2. **View Charts**: Monthly trends and distribution charts update automatically
3. **Explore Data**: Click on table rows to see detailed information
4. **Patient Links**: Click "View Patient" buttons to access patient records
5. **Reset Filters**: Use the "Reset" button to clear all filters

## Technical Stack

- **Backend**: Flask (Python)
- **Database**: Google Cloud BigQuery
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Plotly.js
- **Styling**: Bootstrap 5 + Custom CSS
- **Authentication**: Google Cloud Application Default Credentials

## API Endpoints

- `GET /`: Main dashboard page
- `GET /api/filter`: Filtered data API with parameters:
  - `escalation`: Escalation type filter
  - `email`: Nurse email filter
  - `hospital`: Hospital name filter
  - `date`: Date filter

## Data Source

The application connects to BigQuery table:
`prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data`

## Customization

- **Colors**: Modify the color scheme in `static/css/style.css`
- **Fonts**: Update font families in CSS
- **Column Mappings**: Edit `ESCALATION_COLUMNS` in `app.py`
- **Charts**: Customize chart configurations in chart functions

## Browser Compatibility

- Chrome (recommended)
- Firefox
- Safari
- Edge

## Performance

- Optimized BigQuery queries with LIMIT 1000
- Responsive design for mobile and desktop
- Efficient data loading with AJAX
- Cached filter options for faster loading








