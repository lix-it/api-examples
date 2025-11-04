# n8n Workflow for LookC GetEmployees

This directory contains an n8n workflow that retrieves all employees for a specified organization from the LookC API and stores them in n8n data tables.

## Workflow: get_employees_workflow.json

This workflow demonstrates how to:
- Fetch all employees for an organization using the LookC API
- Handle pagination automatically
- Store employee data in n8n data tables
- Track completion status to avoid re-fetching data
- Implement rate limiting (50ms delay between requests)

### Features

- **Automatic Pagination**: The workflow automatically follows pagination links to retrieve all employees
- **Native n8n Data Tables**: Uses n8n's built-in data tables for storage (no external database required)
- **Resumable**: Tracks completion status to avoid re-processing the same organization
- **Rate Limiting**: Implements a 50ms delay between API requests (20 req/s) to stay within API limits
- **Error Handling**: Built-in retry logic for API requests
- **Data Extraction**: Extracts key fields from employee records for structured storage

### Setup

1. **Create Data Tables**
   
   Before importing the workflow, create two data tables in your n8n project. You have two options:

   **Option A: Quick Setup with CSV Import (Recommended)**
   
   The `data_tables/` directory contains CSV templates that you can import to quickly create the tables:
   
   1. Navigate to the Data tables tab in your n8n project
   2. Click "Import from file"
   3. Select `data_tables/employees.csv` to create the `employees` table
   4. After import, verify the column types:
      - Set `tenure_at_org_months` to **Number** type
      - Set `tenure_in_role_months` to **Number** type
      - All other columns should be **String** type
   5. Repeat for `data_tables/employees_run_state.csv` to create the `employees_run_state` table
   6. After import, verify the column types:
      - Set `is_complete` to **Boolean** type
      - Other columns should be **String** type

   **Option B: Manual Setup**
   
   Alternatively, create the tables manually following the schema definitions in `data_tables/*.schema.json`:

   **Table 1: `employees`**
   - Navigate to the Data tables tab in your n8n project
   - Click "Create Data table"
   - Name it `employees`
   - Add the following columns:
     - `person_id` (String) - Primary identifier
     - `org_id` (String)
     - `name` (String)
     - `title` (String)
     - `date_started` (String)
     - `date_ended` (String)
     - `location` (String)
     - `image` (String)
     - `current_org_id` (String)
     - `current_org_name` (String)
     - `links_linkedin` (String)
     - `links_sales_nav` (String)
     - `tenure_at_org_months` (Number)
     - `tenure_in_role_months` (Number)
     - `data` (String) - Full JSON response
     - `collected_at` (String) - ISO timestamp

   **Table 2: `employees_run_state`**
   - Create another data table named `employees_run_state`
   - Add the following columns:
     - `org_id` (String) - Primary identifier
     - `last_collected_at` (String) - ISO timestamp
     - `is_complete` (Boolean)

2. **Import the Workflow**
   - Open n8n
   - Click "Import from File"
   - Select `get_employees_workflow.json`

3. **Configure Data Table Nodes**
   
   After importing, you must configure each Data table node to select the correct table:
   
   - Open the **"Check Run State"** node
     - Click on the "Data table" dropdown
     - Select `employees_run_state`
   
   - Open the **"Upsert Employee"** node
     - Click on the "Data table" dropdown
     - Select `employees`
   
   - Open the **"Mark Complete"** node
     - Click on the "Data table" dropdown
     - Select `employees_run_state`

4. **Configure Credentials**

   **LookC API Authentication**:
   - Create a new "Header Auth" credential in n8n
   - Set Header Name: `Authorization`
   - Set Header Value: Your LookC API token
   - Or set the `LOOKC_API_TOKEN` environment variable
   - Assign this credential to the **"Fetch Employees Page"** HTTP Request node

5. **Set Organization ID**
   - In the "Set Variables" node, update the `org_id` value
   - Replace `YOUR_ORG_ID_HERE` with your LookC organization UUID

### Usage

1. **Configure the org_id**:
   - Edit the "Set Variables" node
   - Set the `org_id` field to your LookC organization UUID

2. **Run the Workflow**:
   - Click "Execute Workflow" or "Test workflow"
   - The workflow will fetch all employees and store them in the data tables

3. **Monitor Progress**:
   - Watch the execution flow through the nodes
   - The "Success Message" node will show total pages and employees collected

4. **View Results**:
   - Navigate to the Data tables tab
   - Open the `employees` table to view collected employee data
   - Check `employees_run_state` to see completion status

### Programmatic Setup

The `data_tables/` directory contains schema definition files and CSV templates to help automate data table creation:

**Schema Files**:
- `data_tables/employees.schema.json` - Complete schema definition for the employees table
- `data_tables/employees_run_state.schema.json` - Complete schema definition for the run state table

**CSV Templates**:
- `data_tables/employees.csv` - Header-only CSV for quick import
- `data_tables/employees_run_state.csv` - Header-only CSV for quick import

**Limitations**:
- n8n does not currently provide an official REST API for programmatically creating data tables and columns
- The Data table node does not have a "create table" operation
- The recommended approach is to use CSV import (Option A above) or manual creation (Option B)
- Data tables are project-scoped, so the workflow and tables must be in the same n8n Project/Canvas

**For Automation**:
If you need to automate data table creation across multiple n8n instances, you can:
1. Use the CSV import feature via the n8n UI
2. For self-hosted instances, explore the internal API endpoints (not officially documented, version-specific)
3. Create a setup workflow that validates table existence and guides users through manual creation

### Data Table Schema

The workflow uses two data tables:

**employees**:
- `person_id`: LookC person identifier (unique key)
- `org_id`: LookC organization identifier
- `name`: Employee name
- `title`: Job title
- `date_started`: Start date at organization
- `date_ended`: End date (empty if current)
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

**employees_run_state**:
- `org_id`: Organization identifier (unique key)
- `last_collected_at`: Last collection timestamp
- `is_complete`: Boolean flag indicating completion

### Workflow Nodes

1. **When clicking 'Test workflow'**: Manual trigger to start the workflow
2. **Set Variables**: Initialize workflow variables (org_id, API key, etc.)
3. **Check Run State**: Query employees_run_state data table to see if org was already processed
4. **Is Complete?**: Branch based on completion status
5. **Fetch Employees Page**: Make HTTP request to LookC API
6. **Process Response**: Parse API response and extract pagination info
7. **Prepare for Data Table**: Transform employee data for data table insertion
8. **Upsert Employee**: Insert/update employee records in employees data table
9. **Check for More Pages**: Determine if more pages exist
10. **Has More Pages?**: Branch based on pagination status
11. **Rate Limit Wait**: 50ms delay between requests
12. **Update Variables for Next Page**: Update pagination cursor for next iteration
13. **Mark Complete**: Update employees_run_state when all pages are fetched
14. **Success Message**: Display completion summary
15. **Already Complete Message**: Display message if org was already processed

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
| Data Storage | SQLite | n8n Data Tables |
| Rate Limiting | ✓ (50ms) | ✓ (50ms) |
| Resume Support | ✓ | ✓ |
| Error Handling | ✓ | ✓ |
| Visual Interface | ✗ | ✓ |
| Code-free | ✗ | ✓ |
| External Database | Required | Not Required |

### Advantages of n8n Data Tables

- **No External Database**: Data tables are built into n8n, no need to set up SQLite or other databases
- **Visual Management**: View and edit data directly in the n8n UI
- **Project-Scoped**: Data tables are accessible to all workflows in the same project
- **Automatic Backups**: Data is backed up with your n8n instance
- **Easy Export**: Export data to CSV or other formats using n8n nodes

### Troubleshooting

**Authentication Errors (401)**:
- Verify your LookC API token is correct
- Ensure the Authorization header is properly configured in the HTTP Request node credentials

**Payment Required (402)**:
- LookC credits need to be purchased in advance
- Contact LookC support to add credits

**Organization Not Found (404)**:
- Verify the org_id is a valid LookC organization UUID
- Check that you have access to this organization

**Rate Limiting (429)**:
- The workflow includes automatic rate limiting
- If you still hit limits, increase the wait time in "Rate Limit Wait" node

**Data Table Not Found**:
- Ensure you've created both `employees` and `employees_run_state` data tables
- Verify the table names match exactly (case-sensitive)
- Check that the data tables are in the same project as the workflow

**Storage Limit Reached**:
- n8n data tables have a default 50MB limit per table
- Monitor your storage usage in the Data tables tab
- Consider exporting and archiving old data if approaching the limit

### Notes

- The workflow stores the full JSON response in the `data` column for reference
- Duplicate employees (same person_id) are updated rather than creating new records using the Upsert operation
- The workflow can be run multiple times safely - it will skip organizations already marked as complete
- To re-fetch data for an organization, delete its entry from the `employees_run_state` table or set `is_complete` to false
- Data tables are scoped to your n8n project and accessible by all team members in that project
- For self-hosted n8n, you can increase the data table size limit using the `N8N_DATA_TABLES_MAX_SIZE_BYTES` environment variable

### Exporting Data

To export employee data from the data table:

1. Create a new workflow with a Manual Trigger
2. Add a Data table node set to "Get" operation
3. Select the `employees` table
4. Add filters if needed (e.g., filter by org_id)
5. Add a "Convert to File" node to export as CSV or JSON
6. Execute the workflow to download the data

See the [n8n data tables documentation](https://docs.n8n.io/data/data-tables/) for more details on exporting and managing data tables.
