"""
This script retrieves all employees for a specified organisation from the LookC API
and stores them in a SQLite database.

The script supports pagination and can be resumed if interrupted.

Usage: python get_employees.py migrate # to set up the database
       python get_employees.py run --api-key <API_KEY> --org-id <ORG_UUID> # to start collection
       python get_employees.py run --org-id <ORG_UUID> # uses LOOKC_API_TOKEN env var
"""

import argparse
import datetime
import json
import os
import requests
import sqlite3
import sys
import time
from urllib.parse import urljoin

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument("--api-key", help="The API key for the LookC API", dest="api_key")
parser.add_argument(
    "--org-id", help="The LookC organisation UUID to fetch employees for", dest="org_id"
)
parser.add_argument(
    "--db-path", help="The path to the database", default="data/employees.db"
)
parser.add_argument(
    "--page-size", help="Number of employees per page", type=int, dest="page_size"
)
parser.add_argument(
    "command", help="The command to run", choices=["migrate", "run"]
)
args = parser.parse_args()

API_KEY = args.api_key or os.environ.get("LOOKC_API_TOKEN")
db_path = args.db_path

# Parameters
SLEEP_TIME = 0.05  # LookC supports 50 requests/s, using 0.05s (20 req/s) to be conservative
BASE_URL = "https://api.lookc.io"


# helper functions
def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print("Time taken: " + str(time.time() - start_time))
        return result

    return wrapper


# set up migrations for database
def migrate(conn):
    employees_stmt = """create table if not exists employees (
        id integer primary key autoincrement,
        person_id text not null,
        org_id text not null,
        data text not null,
        collected_at datetime not null,
        unique(person_id, org_id)
    )"""
    conn.execute(employees_stmt)

    run_state_stmt = """create table if not exists run_state (
        org_id text primary key,
        last_collected_at datetime,
        is_complete boolean default 0
    )"""
    conn.execute(run_state_stmt)
    conn.commit()
    
    ensure_columns(conn)


def ensure_columns(conn):
    """Add columns to employees table if they don't exist (for backward compatibility)"""
    cursor = conn.execute("PRAGMA table_info(employees)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    desired_columns = {
        'name': 'TEXT',
        'title': 'TEXT',
        'date_started': 'TEXT',
        'date_ended': 'TEXT',
        'location': 'TEXT',
        'image': 'TEXT',
        'current_org_id': 'TEXT',
        'current_org_name': 'TEXT',
        'links_linkedin': 'TEXT',
        'links_sales_nav': 'TEXT',
        'tenure_at_org_months': 'INTEGER',
        'tenure_in_role_months': 'INTEGER',
    }
    
    for col_name, col_type in desired_columns.items():
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except Exception as e:
                print(f"Warning: Could not add column {col_name}: {e}")
    
    conn.commit()


def check_if_complete(conn, org_id):
    """Check if we've already collected all employees for this org"""
    result = conn.execute(
        "select is_complete from run_state where org_id = ?", (org_id,)
    ).fetchone()
    if result and result[0]:
        return True
    return False


def mark_complete(conn, org_id):
    """Mark the collection as complete for this org"""
    conn.execute(
        """insert into run_state (org_id, last_collected_at, is_complete) 
           values (?, ?, 1)
           on conflict(org_id) do update set 
           last_collected_at = excluded.last_collected_at,
           is_complete = 1""",
        (org_id, datetime.datetime.now()),
    )
    conn.commit()


@timeit
def get_employees_page(org_id, after=None, page_size=None):
    """Fetch a single page of employees from the LookC API"""
    url = f"{BASE_URL}/org/{org_id}/employees"
    
    params = {}
    if after:
        params["after"] = after
    if page_size:
        params["page_size"] = page_size
    
    print(f"Fetching employees for org {org_id}" + (f" (after={after})" if after else ""))
    
    success = False
    while not success:
        try:
            r = requests.get(url, headers={"Authorization": API_KEY}, params=params)
        except Exception as e:
            print(f"Error fetching employees: {e}")
            time.sleep(SLEEP_TIME)
            continue
        
        if r.status_code == 200:
            success = True
            try:
                data = r.json()
                print(f"Fetched {len(data.get('employees', []))} employees")
                return data
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                print(r.text)
                time.sleep(SLEEP_TIME)
                return None
        elif r.status_code == 401:
            print("Authentication failed. Please check your API key.")
            print("Hint: Make sure you're using a valid LookC API token.")
            raise Exception("Authentication error (401)")
        elif r.status_code == 402:
            print("Payment required. LookC credits need to be purchased in advance.")
            raise Exception("Payment required (402)")
        elif r.status_code == 404:
            print(f"Organisation not found: {org_id}")
            return None
        elif r.status_code == 429:
            print("Rate limit exceeded, waiting...")
            time.sleep(SLEEP_TIME)
            continue
        elif 400 <= r.status_code < 500:
            print(f"Client error ({r.status_code}): {r.text}")
            raise Exception(f"Client error {r.status_code}")
        elif r.status_code >= 500:
            print(f"Server error ({r.status_code}), retrying...")
            print(r.text)
            time.sleep(SLEEP_TIME)
            continue
    
    return None


def save_employees(conn, org_id, employees):
    """Save employees to the database with extracted fields"""
    for employee in employees:
        person_id = employee.get("personId")
        if not person_id:
            print("Warning: Employee missing personId, skipping")
            continue
        
        name = employee.get("name")
        title = employee.get("title")
        date_started = employee.get("dateStarted")
        date_ended = employee.get("dateEnded")
        location = employee.get("location")
        image = employee.get("image")
        
        links = employee.get("links") or {}
        links_linkedin = links.get("linkedin")
        links_sales_nav = links.get("salesNav")
        
        current_org = employee.get("currentOrg") or {}
        current_org_id = current_org.get("orgId")
        current_org_name = current_org.get("name")
        
        if not current_org_id and date_ended is None:
            current_org_id = org_id
        
        def to_months(duration_obj):
            if not duration_obj:
                return None
            years = duration_obj.get("years", 0)
            months = duration_obj.get("months", 0)
            return years * 12 + months
        
        tenure_at_org_months = to_months(employee.get("tenureAtOrg"))
        tenure_in_role_months = to_months(employee.get("tenureInRole"))
        
        json_data = json.dumps(employee)
        
        try:
            conn.execute(
                """insert into employees (
                    person_id, org_id, name, title, date_started, date_ended, 
                    location, image, current_org_id, current_org_name, 
                    links_linkedin, links_sales_nav, tenure_at_org_months, 
                    tenure_in_role_months, data, collected_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(person_id, org_id) do update set
                    name = excluded.name,
                    title = excluded.title,
                    date_started = excluded.date_started,
                    date_ended = excluded.date_ended,
                    location = excluded.location,
                    image = excluded.image,
                    current_org_id = excluded.current_org_id,
                    current_org_name = excluded.current_org_name,
                    links_linkedin = excluded.links_linkedin,
                    links_sales_nav = excluded.links_sales_nav,
                    tenure_at_org_months = excluded.tenure_at_org_months,
                    tenure_in_role_months = excluded.tenure_in_role_months,
                    data = excluded.data,
                    collected_at = excluded.collected_at""",
                (person_id, org_id, name, title, date_started, date_ended,
                 location, image, current_org_id, current_org_name,
                 links_linkedin, links_sales_nav, tenure_at_org_months,
                 tenure_in_role_months, json_data, datetime.datetime.now()),
            )
        except Exception as e:
            print(f"Error saving employee {person_id}: {e}")
            continue
    
    conn.commit()


def collect_all_employees(conn, org_id, page_size=None):
    """Collect all employees for an organisation with pagination"""
    if check_if_complete(conn, org_id):
        print(f"Already collected all employees for org {org_id}")
        return
    
    after = None
    total_collected = 0
    
    while True:
        data = get_employees_page(org_id, after=after, page_size=page_size)
        
        if data is None:
            print("No data returned, stopping collection")
            break
        
        employees = data.get("employees", [])
        if not employees:
            print("No more employees to collect")
            break
        
        save_employees(conn, org_id, employees)
        total_collected += len(employees)
        print(f"Saved {len(employees)} employees (total: {total_collected})")
        
        paging = data.get("paging", {})
        links = paging.get("_links", {})
        next_link = links.get("next")
        
        if not next_link:
            print("No more pages, collection complete")
            break
        
        if next_link.startswith("http"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(next_link)
            query_params = parse_qs(parsed.query)
            after = query_params.get("after", [None])[0]
        else:
            from urllib.parse import parse_qs
            if "?" in next_link:
                query_string = next_link.split("?")[1]
                query_params = parse_qs(query_string)
                after = query_params.get("after", [None])[0]
            else:
                print(f"Warning: Could not parse next link: {next_link}")
                break
        
        if not after:
            print("Warning: No 'after' cursor found in next link, stopping")
            break
        
        time.sleep(SLEEP_TIME)
    
    mark_complete(conn, org_id)
    print(f"Collection complete! Total employees collected: {total_collected}")


if __name__ == "__main__":
    if args.command == "migrate":
        conn = sqlite3.connect(db_path)
        migrate(conn)
        conn.close()
        print(
            f"Database created at {db_path}. Use `run` command with --org-id to collect employees."
        )
        sys.exit(0)

    if args.command == "run":
        if not API_KEY:
            print("Error: API key is required. Provide --api-key or set LOOKC_API_TOKEN environment variable.")
            sys.exit(1)
        
        if not args.org_id:
            print("Error: Organisation ID is required. Provide --org-id argument.")
            sys.exit(1)
        
        try:
            conn = sqlite3.connect(db_path)
        except sqlite3.OperationalError:
            print(f"Database does not exist. Run `python get_employees.py migrate` first.")
            sys.exit(1)
        
        print(f"Collecting employees for organisation: {args.org_id}")
        collect_all_employees(conn, args.org_id, page_size=args.page_size)
        
        conn.close()
