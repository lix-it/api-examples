# n8n Workflow for LookC GetEmployees

This directory contains an n8n workflow that retrieves all employees for a specified organization from the LookC API and stores them in a SQLite database.

## Workflow: get_employees_workflow.json

This workflow demonstrates how to:
- Fetch all employees for an organization using the LookC API
- Handle pagination automatically
- Store employee data in SQLite with programmatic schema creation
- Track completion status to avoid re-fetching data
- Implement rate limiting (20ms delay = 50 req/s to match LookC API limit)

### Features

- **Automatic Pagination**: The workflow automatically follows pagination links to retrieve all employees
- **Programmatic Schema Creation**: Database tables are created automatically via CREATE TABLE IF NOT EXISTS statements
- **SQLite Storage**: Uses the n8n-nodes-sqlite3 community node for local SQLite database storage
- **Resumable**: Tracks completion status to avoid re-processing the same organization
- **Rate Limiting**: Implements a 20ms delay between API requests (50 req/s) to match LookC API limits
- **Error Handling**: Built-in retry logic for API requests
- **Composite Key Upserts**: Uses ON CONFLICT with composite keys (person_id, org_id) to prevent duplicate records

### Prerequisites

1. **Install the n8n-nodes-sqlite3 Community Node**

   This workflow requires the `n8n-nodes-sqlite3` community node by DangerBlack.

   **For n8n Cloud or Desktop**:
   - Go to Settings → Community Nodes
   - Click "Install a community node"
   - Enter: `n8n-nodes-sqlite3`
   - Click Install

   **For Self-Hosted n8n**:
   - Set environment variable: `N8N_COMMUNITY_NODES_ENABLED=true`
   - Restart n8n
   - Follow the Cloud/Desktop installation steps above

   **Repository**: https://github.com/DangerBlack/n8n-node-sqlite3

2. **Database File Path**

   The workflow uses `/data/lookc_employees.db` as the default database path.

   **For Docker deployments**:
   - Mount a volume to persist the database:
     ```bash
     docker run -v ./n8n_data:/data n8nio/n8n
     ```

   **For self-hosted (non-Docker)**:
   - The default path `/data/` should be writable by the n8n process
   - Alternatively, change `db_path` in the "Set Variables" node to a path like `~/.n8n/lookc_employees.db`

### Setup

1. **Import the Workflow**
   - Open n8n
   - Click "Import from File"
   - Select `get_employees_workflow.json`

2. **Configure LookC API Credentials**

   The workflow needs your LookC API token to authenticate requests.

   **Option A: Environment Variable (Recommended)**:
   - Set the `LOOKC_API_TOKEN` environment variable with your API token
   - The workflow will automatically use it via `$env.LOOKC_API_TOKEN`

   **Option B: Header Auth Credential**:
   - Create a new "Header Auth" credential in n8n
   - Set Header Name: `Authorization`
   - Set Header Value: Your LookC API token
   - Assign this credential to the **"Fetch Employees Page"** HTTP Request node

3. **Configure Database Path (Optional)**

   If you want to use a different database location:
   - Open the **"Set Variables"** node
   - Update the `db_path` value to your desired path
   - Ensure the path is writable by the n8n process

4. **Set Organization ID**
   - In the **"Set Variables"** node, update the `org_id` value
   - Replace `YOUR_ORG_ID_HERE` with your LookC organization UUID

### Usage

1. **Run the Workflow**:
   - Click "Execute Workflow" or "Test workflow"
   - The workflow will:
     - Create the database tables if they don't exist
     - Check if the organization has already been processed
     - Fetch all employees page by page
     - Store them in the SQLite database

2. **Monitor Progress**:
   - Watch the execution flow through the nodes
   - The **"Success Message"** node will show total pages and employees collected

3. **View Results**:
   - Query the SQLite database directly using any SQLite client
   - Or create another n8n workflow with SQLite nodes to query the data

### Database Schema

The workflow creates two tables automatically:

**employees**:
```sql
CREATE TABLE IF NOT EXISTS employees (
  person_id TEXT NOT NULL,
  org_id TEXT NOT NULL,
  name TEXT,
  title TEXT,
  date_started TEXT,
  date_ended TEXT,
  location TEXT,
  image TEXT,
  current_org_id TEXT,
  current_org_name TEXT,
  links_linkedin TEXT,
  links_sales_nav TEXT,
  tenure_at_org_months REAL,
  tenure_in_role_months REAL,
  data TEXT,
  collected_at TEXT,
  UNIQUE (person_id, org_id)
);
```

**employees_run_state**:
```sql
CREATE TABLE IF NOT EXISTS employees_run_state (
  org_id TEXT PRIMARY KEY,
  last_collected_at TEXT,
  is_complete INTEGER
);
```

**Column Descriptions**:

*employees table*:
- `person_id`: LookC person identifier
- `org_id`: LookC organization identifier
- `name`: Employee name
- `title`: Job title
- `date_started`: Start date at organization (ISO date string)
- `date_ended`: End date (empty if current)
- `location`: Employee location
- `image`: Profile image URL
- `current_org_id`: Current organization ID
- `current_org_name`: Current organization name
- `links_linkedin`: LinkedIn profile URL
- `links_sales_nav`: Sales Navigator URL
- `tenure_at_org_months`: Total tenure at organization in months
- `tenure_in_role_months`: Tenure in current role in months
- `data`: Full JSON response from API (stored as string)
- `collected_at`: Timestamp of collection (ISO datetime string)
- **Composite unique constraint on (person_id, org_id)** prevents duplicates

*employees_run_state table*:
- `org_id`: Organization identifier (primary key)
- `last_collected_at`: Last collection timestamp (ISO datetime string)
- `is_complete`: Completion flag (0 or 1, SQLite doesn't have native boolean)

### Workflow Nodes

1. **When clicking 'Test workflow'**: Manual trigger to start the workflow
2. **Set Variables**: Initialize workflow variables (org_id, API key, db_path, etc.)
3. **Create Schema**: Creates both database tables if they don't exist using CREATE TABLE IF NOT EXISTS
4. **Check Run State**: Queries employees_run_state to see if org was already processed
5. **Is Complete?**: Branches based on completion status (checks if is_complete = 1)
6. **Fetch Employees Page**: Makes HTTP request to LookC API with pagination
7. **Process Response**: Parses API response and extracts pagination info
8. **Prepare for SQLite**: Transforms employee data for SQLite insertion
9. **Upsert Employee**: Inserts or updates employee records using ON CONFLICT(person_id, org_id)
10. **Check for More Pages**: Determines if more pages exist
11. **Has More Pages?**: Branches based on pagination status
12. **Rate Limit Wait**: 20ms delay between requests (50 req/s)
13. **Update Variables for Next Page**: Updates pagination cursor for next iteration
14. **Mark Complete**: Updates employees_run_state when all pages are fetched
15. **Success Message**: Displays completion summary
16. **Already Complete Message**: Displays message if org was already processed

### API Endpoint

The workflow calls:
```
GET https://api.lookc.io/org/{orgId}/employees
```

With pagination parameter:
- `after`: Cursor for pagination

### Rate Limiting

The workflow implements a 20ms delay between API requests (50 requests/second) to match the LookC API limit of 50 requests/second.

### Upsert Logic

The workflow uses SQLite's `ON CONFLICT` clause with a composite key to handle duplicates:

```sql
INSERT INTO employees (...)
VALUES (...)
ON CONFLICT(person_id, org_id) DO UPDATE SET
  name = excluded.name,
  title = excluded.title,
  ...
```

This ensures that:
- If a person-org combination doesn't exist, it's inserted
- If it already exists, all fields are updated with the latest data
- The same person can appear in multiple organizations without conflicts

### Comparison with Python Script

This n8n workflow provides the same functionality as the Python script `get_employees.py`:

| Feature | Python Script | n8n Workflow |
|---------|--------------|--------------|
| Pagination | ✓ | ✓ |
| Data Storage | SQLite | SQLite |
| Rate Limiting | ✓ (50ms) | ✓ (20ms = 50 req/s) |
| Resume Support | ✓ | ✓ |
| Error Handling | ✓ | ✓ |
| Visual Interface | ✗ | ✓ |
| Code-free | ✗ | ✓ |
| Programmatic Schema | ✓ | ✓ |

### Advantages of SQLite with n8n-nodes-sqlite3

- **Programmatic Schema Creation**: Tables are created automatically via SQL in the workflow
- **Standard SQL**: Use familiar SQL syntax for queries and data manipulation
- **Portable**: SQLite database is a single file that can be easily backed up or moved
- **No Server Required**: SQLite is serverless and requires no configuration
- **ACID Compliant**: Full transaction support with rollback capabilities
- **Widely Supported**: Can be queried with any SQLite client or library

### Troubleshooting

**Community Node Not Found**:
- Ensure you've installed the `n8n-nodes-sqlite3` community node
- For self-hosted n8n, verify `N8N_COMMUNITY_NODES_ENABLED=true` is set
- Restart n8n after installing the community node

**Database Permission Errors**:
- Verify the database path is writable by the n8n process
- For Docker, ensure the volume is mounted correctly
- Check file permissions on the database file and directory

**Authentication Errors (401)**:
- Verify your LookC API token is correct
- Ensure the Authorization header is properly configured
- Check that `LOOKC_API_TOKEN` environment variable is set (if using that method)

**Payment Required (402)**:
- LookC credits need to be purchased in advance
- Contact LookC support to add credits

**Organization Not Found (404)**:
- Verify the org_id is a valid LookC organization UUID
- Check that you have access to this organization

**Rate Limiting (429)**:
- The workflow includes automatic rate limiting (20ms = 50 req/s)
- If you still hit limits, increase the wait time in "Rate Limit Wait" node

**SQLite Locked Errors**:
- Ensure only one workflow instance is accessing the database at a time
- SQLite supports multiple readers but only one writer at a time
- Consider using WAL mode for better concurrency if needed

**Native Module Errors**:
- The n8n-nodes-sqlite3 package includes prebuilt native bindings for Linux musl (Alpine)
- If you're on a different platform or Node version, you may need to rebuild
- See the [n8n-nodes-sqlite3 repository](https://github.com/DangerBlack/n8n-node-sqlite3) for build instructions

### Notes

- The workflow stores the full JSON response in the `data` column for reference
- Duplicate employees (same person_id + org_id) are updated rather than creating new records
- The workflow can be run multiple times safely - it will skip organizations already marked as complete
- To re-fetch data for an organization, run: `UPDATE employees_run_state SET is_complete = 0 WHERE org_id = 'YOUR_ORG_ID'`
- The database file will grow over time; monitor disk space and consider archiving old data periodically
- SQLite `is_complete` uses INTEGER (0 or 1) instead of BOOLEAN

### Querying Data

You can query the SQLite database using:

1. **Another n8n workflow**:
   - Add a Manual Trigger
   - Add a SQLite Node (n8n-nodes-sqlite3)
   - Set query type to SELECT
   - Write your SQL query
   - Example: `SELECT * FROM employees WHERE org_id = $org_id`

2. **SQLite command-line tool**:
   ```bash
   sqlite3 /data/lookc_employees.db
   SELECT COUNT(*) FROM employees;
   SELECT * FROM employees WHERE org_id = 'YOUR_ORG_ID' LIMIT 10;
   ```

3. **Any SQLite client**:
   - DB Browser for SQLite
   - DBeaver
   - DataGrip
   - VS Code SQLite extension

### Exporting Data

To export employee data from SQLite:

1. **Using SQLite command-line**:
   ```bash
   sqlite3 /data/lookc_employees.db
   .mode csv
   .headers on
   .output employees.csv
   SELECT * FROM employees WHERE org_id = 'YOUR_ORG_ID';
   .quit
   ```

2. **Using n8n workflow**:
   - Create a workflow with a Manual Trigger
   - Add a SQLite Node to SELECT data
   - Add a "Convert to File" node to export as CSV or JSON
   - Execute the workflow to download the data

### Community Node Information

**Package**: n8n-nodes-sqlite3  
**Author**: DangerBlack  
**Repository**: https://github.com/DangerBlack/n8n-node-sqlite3  
**License**: MIT  

The community node uses `better-sqlite3` under the hood, which is a fast, synchronous SQLite3 library for Node.js.

### Security Considerations

- **API Token**: Never commit your LookC API token to version control. Use environment variables or n8n credentials.
- **Database Access**: Ensure the SQLite database file has appropriate permissions and is not publicly accessible.
- **SQL Injection**: The workflow uses parameterized queries ($param syntax) to prevent SQL injection attacks.
- **Data Privacy**: Employee data may contain PII. Ensure compliance with data protection regulations (GDPR, CCPA, etc.).
