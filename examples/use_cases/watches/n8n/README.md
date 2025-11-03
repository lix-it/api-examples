# n8n Workflow for LookC GetEmployees

This directory contains an n8n workflow that retrieves all employees for a specified organization from the LookC API and stores them in a SQLite database.

## Workflow: get_employees_workflow.json

This workflow demonstrates how to:
- Fetch all employees for an organization using the LookC API
- Handle pagination automatically
- Store employee data in a SQLite database
- Track completion status to avoid re-fetching data
- Implement rate limiting (50ms delay between requests)

### Features

- **Automatic Pagination**: The workflow automatically follows pagination links to retrieve all employees
- **SQLite Storage**: Stores employee data with extracted fields for easy querying
- **Resumable**: Tracks completion status to avoid re-processing the same organization
- **Rate Limiting**: Implements a 50ms delay between API requests (20 req/s) to stay within API limits
- **Error Handling**: Built-in retry logic for API requests
- **Data Extraction**: Extracts key fields from employee records for structured storage

### Setup

1. **Import the Workflow**
   - Open n8n
   - Click "Import from File"
   - Select `get_employees_workflow.json`

2. **Configure Credentials**

   **SQLite Database**:
   - Create a new SQLite credential in n8n
   - Set the database file path (e.g., `/path/to/employees.db`)
   - The workflow will automatically create the necessary tables

   **LookC API Authentication**:
   - Create a new "Header Auth" credential
   - Set Header Name: `Authorization`
   - Set Header Value: Your LookC API token (e.g., `Bearer YOUR_TOKEN_HERE`)
   - Or set the `LOOKC_API_TOKEN` environment variable

3. **Set Organization ID**
   - In the "Set Variables" node, update the `org_id` value
   - Replace `YOUR_ORG_ID_HERE` with your LookC organization UUID

### Usage

1. **Configure the org_id**:
   - Edit the "Set Variables" node
   - Set the `org_id` field to your LookC organization UUID

2. **Run the Workflow**:
   - Click "Execute Workflow" or "Test workflow"
   - The workflow will fetch all employees and store them in SQLite

3. **Monitor Progress**:
   - Watch the execution flow through the nodes
   - The "Success Message" node will show total pages and employees collected

### Database Schema

The workflow creates two tables:

**employees**:
- `id`: Auto-incrementing primary key
- `person_id`: LookC person identifier
- `org_id`: LookC organization identifier
- `name`: Employee name
- `title`: Job title
- `date_started`: Start date at organization
- `date_ended`: End date (null if current)
- `location`: Employee location
- `image`: Profile image URL
- `current_org_id`: Current organization ID
- `current_org_name`: Current organization name
- `links_linkedin`: LinkedIn profile URL
- `links_sales_nav`: Sales Navigator URL
- `tenure_at_org_months`: Total tenure at organization in months
- `tenure_in_role_months`: Tenure in current role in months
- `data`: Full JSON response from API
- `collected_at`: Timestamp of collection

**run_state**:
- `org_id`: Organization identifier (primary key)
- `last_collected_at`: Last collection timestamp
- `is_complete`: Boolean flag indicating completion

### Workflow Nodes

1. **When clicking 'Test workflow'**: Manual trigger to start the workflow
2. **Set Variables**: Initialize workflow variables (org_id, API key, etc.)
3. **Create Database Tables**: Create SQLite tables if they don't exist
4. **Check if Already Complete**: Query run_state to see if org was already processed
5. **Is Complete?**: Branch based on completion status
6. **Fetch Employees Page**: Make HTTP request to LookC API
7. **Process Response**: Parse API response and extract pagination info
8. **Prepare for Database**: Transform employee data for database insertion
9. **Insert Employee**: Insert/update employee records in SQLite
10. **Check for More Pages**: Determine if more pages exist
11. **Has More Pages?**: Branch based on pagination status
12. **Rate Limit Wait**: 50ms delay between requests
13. **Mark Complete**: Update run_state when all pages are fetched
14. **Success Message**: Display completion summary

### API Endpoint

The workflow calls:
```
GET https://api.lookc.io/org/{orgId}/employees
```

With pagination parameter:
- `after`: Cursor for pagination

### Rate Limiting

The workflow implements a 50ms delay between API requests (20 requests/second), which is conservative compared to the LookC API limit of 50 requests/second.

### Comparison with Python Script

This n8n workflow provides the same functionality as the Python script `get_employees.py`:

| Feature | Python Script | n8n Workflow |
|---------|--------------|--------------|
| Pagination | ✓ | ✓ |
| SQLite Storage | ✓ | ✓ |
| Rate Limiting | ✓ (50ms) | ✓ (50ms) |
| Resume Support | ✓ | ✓ |
| Error Handling | ✓ | ✓ |
| Visual Interface | ✗ | ✓ |
| Code-free | ✗ | ✓ |

### Troubleshooting

**Authentication Errors (401)**:
- Verify your LookC API token is correct
- Ensure the Authorization header is properly configured

**Payment Required (402)**:
- LookC credits need to be purchased in advance
- Contact LookC support to add credits

**Organization Not Found (404)**:
- Verify the org_id is a valid LookC organization UUID
- Check that you have access to this organization

**Rate Limiting (429)**:
- The workflow includes automatic rate limiting
- If you still hit limits, increase the wait time in "Rate Limit Wait" node

### Notes

- The workflow stores the full JSON response in the `data` column for reference
- Duplicate employees (same person_id and org_id) are updated rather than creating new records
- The workflow can be run multiple times safely - it will skip organizations already marked as complete
- To re-fetch data for an organization, delete its entry from the `run_state` table
