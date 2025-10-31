#!/usr/bin/env python3
"""
BigQuery Connector Script
Connects to Google Cloud BigQuery and displays data from the nursing_pod_quality_data table.
"""

import os
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import json

def authenticate_bigquery():
    """
    Authenticate with Google Cloud BigQuery.
    Supports both service account key file and Application Default Credentials.
    """
    # Check if service account key file exists
    service_account_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if service_account_path and os.path.exists(service_account_path):
        print(f"Using service account key file: {service_account_path}")
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        client = bigquery.Client(credentials=credentials)
    else:
        print("Using Application Default Credentials")
        # This will use the default credentials (gcloud auth application-default login)
        client = bigquery.Client()
    
    return client

def query_nursing_pod_data(client, limit=1000):
    """
    Query the nursing pod quality data table.
    """
    query = f"""
    SELECT * FROM `prod-tech-project1-bv479-zo027.gsheet_data.nursing_pod_quality_data`
    LIMIT {limit}
    """
    
    print(f"Executing query: {query}")
    print("-" * 80)
    
    try:
        # Execute the query
        query_job = client.query(query)
        results = query_job.result()
        
        # Convert to pandas DataFrame for better display
        df = results.to_dataframe()
        
        print(f"Query completed successfully!")
        print(f"Number of rows returned: {len(df)}")
        print(f"Number of columns: {len(df.columns)}")
        print("-" * 80)
        
        # Display column information
        print("Column Information:")
        for i, col in enumerate(df.columns, 1):
            print(f"{i:2d}. {col}")
        print("-" * 80)
        
        # Display first few rows
        print("First 10 rows of data:")
        print(df.head(10).to_string(index=False))
        
        if len(df) > 10:
            print(f"\n... and {len(df) - 10} more rows")
        
        # Display basic statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            print("\n" + "=" * 80)
            print("Basic Statistics for Numeric Columns:")
            print(df[numeric_cols].describe().to_string())
        
        return df
        
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return None

def main():
    """
    Main function to connect to BigQuery and display data.
    """
    print("BigQuery Nursing Pod Quality Data Connector")
    print("=" * 80)
    
    try:
        # Authenticate with BigQuery
        client = authenticate_bigquery()
        print("Successfully authenticated with BigQuery!")
        print("-" * 80)
        
        # Query the data
        df = query_nursing_pod_data(client, limit=1000)
        
        if df is not None:
            print("\n" + "=" * 80)
            print("Data retrieval completed successfully!")
            
            # Optionally save to CSV
            save_csv = input("\nWould you like to save the data to a CSV file? (y/n): ").lower().strip()
            if save_csv == 'y':
                csv_filename = "nursing_pod_quality_data.csv"
                df.to_csv(csv_filename, index=False)
                print(f"Data saved to {csv_filename}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you have authenticated with Google Cloud:")
        print("   gcloud auth application-default login")
        print("2. Or set the GOOGLE_APPLICATION_CREDENTIALS environment variable")
        print("   to point to your service account key file")
        print("3. Ensure you have the necessary permissions to access the BigQuery dataset")

if __name__ == "__main__":
    main()

