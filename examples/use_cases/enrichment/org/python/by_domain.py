"""
This script retrieves org data by domain from a SQLite database
and enriches them with data from the Lix API.

If the script fails, it can be resumed from the last domain.

Usage: python by_domain.py migrate # to set up the database
        python by_domain.py import --import-path <CSV_FILE> # to import domains
        python by_domain.py run --api-key <API_KEY> # to start collection
"""

import argparse
import datetime
import json
import pandas as pd
import requests
import sqlite3
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--api-key", help="The API key for the Lix API", dest="api_key")
parser.add_argument(
    "--db-path", help="The path to the database", default="data/orgs_by_domain.db"
)
parser.add_argument(
    "--import-path",
    help="The path to the CSV file to import",
    default="input/domains.csv",
)
parser.add_argument(
    "command", help="The command to run", choices=["migrate", "run", "import"]
)
args = parser.parse_args()

API_KEY = args.api_key
db_path = args.db_path

sleep_time = 3


def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print("Time taken: " + str(time.time() - start_time))
        return result

    return wrapper


def migrate(conn):
    domains_stmt = """create table if not exists domains (
        id integer primary key autoincrement,
        domain text,
        last_collected_at datetime
    )"""
    conn.execute(domains_stmt)

    domains_enriched_stmt = """create table if not exists domains_enriched (
        id integer primary key autoincrement,
        domain_id integer,
        data text,
        collected_at datetime,

        foreign key(domain_id) references domains(id)
    )"""
    conn.execute(domains_enriched_stmt)


def get_domains(conn):
    domains = conn.execute(
        "select * from domains where last_collected_at is null"
    ).fetchall()
    return domains


@timeit
def get_org_by_domain(domain):
    print("getting", domain)
    lix_url = f"https://api.lix-it.com/v1/organisations/by-domain/{domain}"

    success = False
    while success == False:
        try:
            r = requests.get(lix_url, headers={"Authorization": API_KEY})
        except Exception as e:
            print("Error getting org data for " + domain)
            print(e)
            time.sleep(sleep_time)
            return 0
        if r.status_code != 200:
            if r.status_code == 404:
                print("Org not found: " + domain)
                break
            if r.status_code == 400:
                j = r.json()
                if j.get("error", {}).get("type") == "not_found":
                    print("Org not found: " + domain)
                    break
            if r.status_code == 429:
                print("Rate limit exceeded")
                time.sleep(sleep_time)
                continue
            if r.status_code > 399 and r.status_code < 500:
                print("Error getting org: " + str(r.status_code))
                print(r.text)
                raise Exception("Client error " + str(r.status_code))
            if r.status_code > 499:
                print("Error getting org: " + str(r.status_code))
                print(r.text)
                time.sleep(sleep_time)
                continue
        success = True
        print("got", domain)
        try:
            j = r.json()
        except Exception as e:
            print("Error parsing JSON")
            print(e)
            print(r.text)
            time.sleep(sleep_time)
            return 0
    if success:
        print("parsed", domain)
        time.sleep(sleep_time)
    return j


def collect_data(conn, domains):
    for domain_row in domains:
        domain = domain_row[1]
        data = get_org_by_domain(domain)
        if data == 0:
            continue
        json_data = json.dumps(data)
        conn.execute(
            "insert into domains_enriched (domain_id, data, collected_at) values (?, ?, ?)",
            (domain_row[0], json_data, datetime.datetime.now()),
        )
        conn.execute(
            "update domains set last_collected_at = ? where id = ?",
            (datetime.datetime.now(), domain_row[0]),
        )
        conn.commit()
        print("collected", domain)


if __name__ == "__main__":
    if args.command == "migrate":
        conn = sqlite3.connect(db_path)
        migrate(conn)
        conn.close()
        print(
            "Database created at {}. Please add domains to the domains table using the `import` command and then `run` to collect data.".format(
                db_path
            )
        )
        sys.exit(0)

    if args.command == "import":
        conn = sqlite3.connect(db_path)
        print("Importing data from", args.import_path, "...")
        domains = pd.read_csv(args.import_path)
        domains.to_sql("domains", conn, if_exists="append", index=False)
        conn.close()
        print("Data imported.")
        sys.exit(0)

    if args.api_key is None:
        print("Please provide an API key")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.OperationalError:
        print("Database does not exist. Run `python [PATH]/by_domain.py migrate` first.")
        sys.exit(1)

    domains = get_domains(conn)
    print("Collecting data for", len(domains), "domains")
    collect_data(conn, domains)

    conn.close()
