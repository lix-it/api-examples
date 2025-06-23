"""
This script retrieves LinkedIn profile links from a SQLite database
and enriches them with email data from the Lix Contact API.

The script implements retry logic to continue attempting email lookup
until a VALID email is found or 6 retries are reached.

If the script fails, it can be resumed from the last profile link.

Usage: python email_enrichment.py migrate # to set up the database
       python email_enrichment.py import --import-path <CSV_FILE> # to import profile links
       python email_enrichment.py run --api-key <API_KEY> # to start email collection
"""
import argparse
import datetime
import json
import pandas as pd
import requests
import sqlite3
import sys
import time
import urllib.parse

parser = argparse.ArgumentParser()
parser.add_argument("--api-key", help="The API key for the Lix API", dest="api_key")
parser.add_argument("--db-path", help="The path to the database", default="data/email_enrichment.db")
parser.add_argument("--import-path", help="The path to the CSV file to import", default="input/profiles.csv")
parser.add_argument("command", help="The command to run", choices=["migrate", "run", "import"])
args = parser.parse_args()

API_KEY = args.api_key
db_path = args.db_path

sleep_time = 0.1
max_retries = 6

def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print("Time taken: " + str(time.time() - start_time))
        return result
    return wrapper

def migrate(conn):
    profiles_stmt = """create table if not exists profiles (
        id integer primary key autoincrement,
        name text,
        linkedin_url text,
        last_attempted_at datetime
    )"""
    conn.execute(profiles_stmt)

    email_enrichment_stmt = """create table if not exists email_enrichment (
        id integer primary key autoincrement,
        profile_id integer,
        email text,
        status text,
        alternatives text,
        retry_count integer default 0,
        collected_at datetime,

        foreign key(profile_id) references profiles(id)
    )"""
    conn.execute(email_enrichment_stmt)

def get_profiles_to_process(conn):
    query = """
    SELECT p.* FROM profiles p
    LEFT JOIN email_enrichment e ON p.id = e.profile_id 
    WHERE e.profile_id IS NULL 
       OR (e.status != 'VALID' AND e.retry_count < ?)
    """
    profiles = conn.execute(query, (max_retries,)).fetchall()
    return profiles

def get_current_retry_count(conn, profile_id):
    result = conn.execute(
        "SELECT retry_count FROM email_enrichment WHERE profile_id = ? ORDER BY collected_at DESC LIMIT 1",
        (profile_id,)
    ).fetchone()
    return result[0] if result else 0

@timeit
def get_email_from_profile(profile_url):
    print("Getting email for:", profile_url)
    
    encoded_url = urllib.parse.quote(profile_url, safe="")
    lix_url = f"https://api.lix-it.com/v1/contact/email/by-linkedin?url={encoded_url}"
    
    success = False
    while not success:
        try:
            r = requests.get(lix_url, headers={"Authorization": API_KEY})
        except Exception as e:
            print("Error getting email data for " + profile_url)
            print(e)
            time.sleep(sleep_time)
            return None
        
        if r.status_code != 200:
            if r.status_code == 404:
                print("Profile not found: " + profile_url)
                break
            if r.status_code == 400:
                try:
                    j = r.json()
                    if j.get("error", {}).get("type") == "not_found":
                        print("Profile not found: " + profile_url)
                        break
                except:
                    pass
            if r.status_code == 429:
                print("Rate limit exceeded")
                time.sleep(sleep_time)
                continue
            if r.status_code >= 400 and r.status_code < 500:
                print("Error getting email: " + str(r.status_code))
                print(r.text)
                raise Exception("Client error " + str(r.status_code))
            if r.status_code >= 500:
                print("Error getting email: " + str(r.status_code))
                print(r.text)
                time.sleep(sleep_time)
                continue
        
        success = True
        print("Got response for:", profile_url)
        
        try:
            j = r.json()
        except Exception as e:
            print("Error parsing JSON")
            print(e)
            print(r.text)
            time.sleep(sleep_time)
            return None
    
    if success:
        print("Email lookup completed for:", profile_url)
        time.sleep(sleep_time)
    
    return j

def collect_emails(conn, profiles):
    for profile in profiles:
        profile_id = profile[0]
        profile_url = profile[2]
        
        current_retry_count = get_current_retry_count(conn, profile_id)
        
        if current_retry_count >= max_retries:
            print(f"Max retries reached for profile {profile_id}, skipping")
            continue
        
        print(f"Processing profile {profile_id} (attempt {current_retry_count + 1}/{max_retries})")
        
        email_data = get_email_from_profile(profile_url)
        if email_data is None:
            continue
        
        new_retry_count = current_retry_count + 1
        status = email_data.get("status", "UNKNOWN")
        email = email_data.get("email", "")
        alternatives = json.dumps(email_data.get("alternatives", []))
        
        conn.execute(
            "INSERT INTO email_enrichment (profile_id, email, status, alternatives, retry_count, collected_at) VALUES (?, ?, ?, ?, ?, ?)",
            (profile_id, email, status, alternatives, new_retry_count, datetime.datetime.now())
        )
        conn.execute(
            "UPDATE profiles SET last_attempted_at = ? WHERE id = ?",
            (datetime.datetime.now(), profile_id)
        )
        conn.commit()
        
        print(f"Collected email data for profile {profile_id}: status={status}, retry_count={new_retry_count}")
        
        if status == "VALID":
            print(f"Valid email found for profile {profile_id}: {email}")
        elif status == "PROBABLE":
            print(f"Probable email found for profile {profile_id}, will retry if under max attempts")

if __name__ == "__main__":
    if args.command == "migrate":
        conn = sqlite3.connect(db_path)
        migrate(conn)
        conn.close()
        print("Database created at {}. Please add profile links to the profiles table using the `import` command and then `run` to collect email data.".format(db_path))
        sys.exit(0)
    
    if args.command == "import":
        conn = sqlite3.connect(db_path)
        print("Importing data from", args.import_path, "...")
        profiles = pd.read_csv(args.import_path)
        profiles.to_sql("profiles", conn, if_exists="append", index=False)
        conn.close()
        print("Data imported.")
        sys.exit(0)

    if args.api_key is None:
        print("Please provide an API key")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.OperationalError:
        print("Database does not exist. Run `python email_enrichment.py migrate` first.")
        sys.exit(1)

    profiles = get_profiles_to_process(conn)
    print("Processing email data for", len(profiles), "profiles")
    collect_emails(conn, profiles)

    conn.close()
