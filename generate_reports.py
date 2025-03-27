import os
import requests
import time
import gzip
import shutil
import json
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables
PRIMARY_ORG_ID = os.getenv('PRIMARY_ORG_ID')
CIRCLE_TOKEN = os.getenv('CIRCLE_TOKEN')
START_DATE = os.getenv('START_DATE')  # Format: "2024-11-01T09:00:00Z"
END_DATE = os.getenv('END_DATE')      # Format: "2024-11-01T09:00:00Z"

# Create directory for usage reports
REPORT_DIR = 'usage_reports'
os.makedirs(REPORT_DIR, exist_ok=True)

# Function to get all organizations on the shared plan
def get_shared_orgs(org_id, circle_token):
    print(f"Fetching organizations on the shared plan for {org_id}...")
    url = f"https://circleci.com/private/orgs/{org_id}/plan/shares-for"
    
    headers = {
        "Circle-Token": circle_token,
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            
            # Based on the actual response format (contains 'orgs' key)
            if 'orgs' in data and isinstance(data['orgs'], list):
                orgs = data['orgs']
                
                # Print summary information
                print(f"\nFound {len(orgs)} organizations on the shared plan.")
                
                # Extract and display organization information
                print("\nOrganizations on the shared plan:")
                print(f"{'#':<4} {'Name':<30} {'VCS Type':<12} {'Organization ID'}")
                print("-" * 75)
                
                for i, org in enumerate(orgs, 1):
                    org_id = org.get('id', 'Unknown ID')
                    org_name = org.get('name', 'Unknown Name')
                    vcs_type = org.get('vcs_type', 'Unknown')
                    print(f"{i:<4} {org_name:<30} {vcs_type:<12} {org_id}")
                
                return orgs
            else:
                print("Unexpected response format. Response doesn't contain 'orgs' list.")
                print("Full response:", json.dumps(data, indent=2))
                return []
        else:
            print(f"Error: API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON response: {response.text}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
    
    return []

# Function to create a usage export job
def create_usage_export_job(org_id, circle_token, start_date, end_date, shared_org_ids=None):
    url = f"https://circleci.com/api/v2/organizations/{org_id}/usage_export_job"
    headers = {
        "Circle-Token": circle_token,
        "Content-Type": "application/json"
    }
    
    # If shared_org_ids is not provided, use the org_id itself
    if shared_org_ids is None:
        shared_org_ids = [org_id]
    
    data = {
        "start": start_date,
        "end": end_date,
        "shared_org_ids": shared_org_ids
    }
    
    print(f"Creating export job for timeframe: {start_date} to {end_date}")
    print(f"Including {len(shared_org_ids)} organizations in the report")
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 201:
        print(f"Failed to create usage export job: {response.text}")
        return None
    
    return response.json().get('usage_export_job_id')

# Function to check the status of the usage export job
def check_job_status(org_id, circle_token, job_id):
    url = f"https://circleci.com/api/v2/organizations/{org_id}/usage_export_job/{job_id}"
    headers = {
        "Circle-Token": circle_token
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to get job status: {response.text}")
        return None
    
    return response.json()

# Function to download files from URLs
def download_files(download_urls, start_date, end_date, filename_prefix):
    max_retries = 3
    downloaded_files = []
    
    for url in download_urls:
        print(f"Downloading {url}...")
        for attempt in range(1, max_retries + 1):
            response = requests.get(url, allow_redirects=True)
            if response.status_code == 200:
                # Create a structured filename
                date_part = f"{start_date[:10]}_{end_date[:10]}"
                filename = f"{filename_prefix}_{date_part}.csv.gz"
                file_path = os.path.join(REPORT_DIR, filename)
                
                # Save the file
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                print(f"Downloaded {file_path}")
                downloaded_files.append(file_path)
                break  # Exit retry loop on success
            else:
                print(f"Attempt {attempt}/{max_retries} failed to download {url}, Status Code: {response.status_code}")
                if attempt == max_retries:
                    print(f"Failed to download {url} after {max_retries} attempts.")
    
    return downloaded_files

# Function to validate file format
def validate_file(file_path):
    try:
        with open(file_path, 'rb') as file:
            # Check if the file starts with gzip magic number
            if file.read(2) != b'\x1f\x8b':
                print(f"File {file_path} is not a valid gzipped file.")
                return False
    except Exception as e:
        print(f"Error validating file {file_path}: {e}")
        return False
    return True

# Function to unzip downloaded files
def unzip_files(file_path, start_date, end_date, filename_prefix):
    if validate_file(file_path):
        print(f"Unzipping {file_path}...")
        try:
            date_part = f"{start_date[:10]}_{end_date[:10]}"
            csv_filename = f"{filename_prefix}_{date_part}.csv"
            output_path = os.path.join(REPORT_DIR, csv_filename)
            
            with gzip.open(file_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            print(f"Unzipped to {output_path}")
            return output_path
        except Exception as e:
            print(f"Error unzipping {file_path}: {e}")
    return None

# Process a single time frame for all organizations
def process_specific_timeframe(orgs, start_date, end_date):
    print(f"\nProcessing timeframe: {start_date} to {end_date} for {len(orgs)} organizations")
    
    # Format org IDs for API request
    org_id_list = []
    for org in orgs:
        if isinstance(org, dict) and 'id' in org:
            org_id_list.append(org['id'])
        elif isinstance(org, str):
            org_id_list.append(org)
    
    if not org_id_list:
        print("No valid organization IDs found.")
        return None
    
    print(f"Requesting usage data for {len(org_id_list)} organizations")
    
    # Create the usage export job with all organization IDs
    job_id = create_usage_export_job(PRIMARY_ORG_ID, CIRCLE_TOKEN, start_date, end_date, org_id_list)
    
    if not job_id:
        print(f"Failed to create export job for timeframe {start_date} to {end_date}")
        return None
    
    print(f"Usage export job created with ID: {job_id}")
    
    # Poll for job status
    max_attempts = 30  # Increased for jobs with many organizations
    attempt = 0
    job_state = "processing"
    
    while job_state == "processing" and attempt < max_attempts:
        job_status = check_job_status(PRIMARY_ORG_ID, CIRCLE_TOKEN, job_id)
        
        if job_status is None:
            break
        
        job_state = job_status.get('state')
        print(f"Job state: {job_state} (attempt {attempt+1}/{max_attempts})")
        
        if job_state == "processing":
            wait_time = min(30 * (attempt + 1), 300)  # Progressive backoff, max 5 minutes
            print(f"Job is still processing. Waiting for {wait_time} seconds before checking again...")
            time.sleep(wait_time)
        
        attempt += 1
    
    # Check if the job has completed
    if job_state == "completed":
        print("Job has completed. Downloading files...")
        download_urls = job_status.get('download_urls', [])
        
        # Generate a timestamp for the filename
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        downloaded_files = download_files(download_urls, start_date, end_date, f"all_orgs_{timestamp}")
        
        csv_files = []
        for file_path in downloaded_files:
            csv_file = unzip_files(file_path, start_date, end_date, f"all_orgs_{timestamp}")
            if csv_file:
                csv_files.append(csv_file)
                print(f"\nSuccess! Report is available at: {csv_file}")
        
        return csv_files
    else:
        print(f"Job has finished with state: {job_state}")
        if job_state == "processing":
            print("Max attempts reached. Job is still processing.")
        return None

# Main script execution
if __name__ == "__main__":
    print("CircleCI Usage Report Generator for Specific Timeframe")
    
    # Check for required environment variables
    if not CIRCLE_TOKEN:
        exit("Please set CIRCLE_TOKEN in your environment variables.")
    
    if not PRIMARY_ORG_ID:
        exit("Please set PRIMARY_ORG_ID in your environment variables.")
    
    if not START_DATE or not END_DATE:
        exit("Please set both START_DATE and END_DATE environment variables in the format: 2024-11-01T09:00:00Z")
    
    # Validate date format
    try:
        # Basic validation - just check if they conform to expected pattern
        if (not START_DATE.endswith('Z') or not END_DATE.endswith('Z') or 
            len(START_DATE) != 20 or len(END_DATE) != 20):
            exit("Date format incorrect. Please use the format: 2024-11-01T09:00:00Z")
        
        print(f"Generating report for timeframe: {START_DATE} to {END_DATE}")
        
        # Get all organizations on the shared plan
        orgs = get_shared_orgs(PRIMARY_ORG_ID, CIRCLE_TOKEN)
        
        if not orgs:
            exit("No organizations found on the shared plan. Exiting.")
        
        # Process the specific timeframe
        csv_files = process_specific_timeframe(orgs, START_DATE, END_DATE)
        
        if not csv_files:
            print("No reports were generated. Please check the errors above.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
