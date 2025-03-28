# CircleCI Usage Report Generator for Specific Timeframe

This tool generates usage reports for all organizations on a shared CircleCI plan for a specific timeframe. Please note that the APi endpoint used to retrieve organizations on a shared plan is not supported and is not guarenteed. It may be deprecated without notice. 

## Features

- **Specific Timeframe**: Generates reports for exactly the date range you specify
- **Organization Discovery**: Automatically finds all organizations on your shared plan
- **Batch Processing**: Processes all organizations together in a single job
- **Error Handling**: Implements retry logic and progressive backoff

## Prerequisites

- Python 3.6 or higher
- CircleCI API token with admin access to the primary organization
- Primary organization ID (the organization that owns the plan)
- Start and end dates for the report

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/circleci-usage-reports.git
   cd circleci-usage-reports
   ```

2. Install required packages:
   ```bash
   pip install requests python-dotenv
   ```

3. Create a `.env` file in the project directory using the provided `.env.sample` as a template:
   ```bash
   cp .env.sample .env
   ```

4. Edit the `.env` file with your specific information:
   ```
   CIRCLE_TOKEN=your_circleci_api_token
   PRIMARY_ORG_ID=your_primary_organization_id
   START_DATE=2024-11-01T00:00:00Z
   END_DATE=2024-11-30T23:59:59Z
   ```

## Usage

Run the script:

```bash
python generate_reports.py
```

Alternatively, you can set the environment variables at runtime:

```bash
START_DATE=2024-11-01T00:00:00Z END_DATE=2024-11-30T23:59:59Z python generate_reports.py
```

The script will:
1. Fetch all organizations on your shared plan
2. Create a usage export job for your specified timeframe
3. Download and unzip the report

## Date Format

The dates must be in ISO 8601 format with UTC timezone indicated by 'Z':
- `YYYY-MM-DDThh:mm:ssZ`

Examples:
- `2024-11-01T00:00:00Z` (Midnight UTC on November 1, 2024)
- `2024-11-30T23:59:59Z` (Just before midnight UTC on November 30, 2024)

## Output

- The script creates a `usage_reports` directory
- Both the compressed (.csv.gz) and uncompressed (.csv) files are saved
- Files are named with a timestamp and the date range for easy identification

## Troubleshooting

### Date Format Issues
If you get an error about date format, double-check that your dates match the required format exactly, including the 'T', colons, and 'Z' at the end.

### Large Number of Organizations
If you have a very large number of organizations, the job might take longer to complete. The script has a 30-attempt polling limit with progressive backoff up to 5 minutes between attempts.

### API Rate Limits
If you encounter rate limit errors, you might need to increase the delays between API calls or run the script after 24 hours. CircleCI currently supports 10 requests per day. 

## Data Analysis

The generated CSV can be analyzed using:
- Excel or Google Sheets for basic analysis
- Python with pandas and matplotlib for more advanced analysis
- Data visualization tools like Tableau or Power BI

