"""
This script retrieves person profile links from a SQLite database
and enriches them with data from the Lix API.

If the script fails, it can be resumed from the last profile link.

Usage: python person.py migrate # to set up the database
        python person.py import --import-path <CSV_FILE> # to import profile links
        python person.py run --api-key <API_KEY> # to start collection
"""
import argparse
import datetime
import json
import pandas as pd
import requests
import sqlite3
import sys
import time

# Arguments
parser = argparse.ArgumentParser()
parser.add_argument("--api-key", help="The API key for the Lix API", dest="api_key")
parser.add_argument("--db-path", help="The path to the database", default="data/people.db")
parser.add_argument("--import-path", help="The path to the CSV file to import", default="input/people.csv")
parser.add_argument("command", help="The command to run", choices=["migrate", "run", "import"])
args = parser.parse_args()

API_KEY = args.api_key
db_path = args.db_path

# Parameters
sleep_time = 0.1  # sleep for 1 second to avoid rate limit

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
    # The people table stores a list of profile links
    people_stmt = """create table if not exists people (
        id integer primary key autoincrement,
        name text,
        link text,
        last_collected_at datetime
    )"""
    conn.execute(people_stmt)

    # This table stores a list of profile data
    people_enriched_stmt = """create table if not exists people_enriched (
        id integer primary key autoincrement,
        person_id integer,
        data text,
        collected_at datetime,

        foreign key(person_id) references people(id)
    )"""
    conn.execute(people_enriched_stmt)

# get all profile links that have not been collected yet
def get_people(conn):
    people = conn.execute("select * from people where last_collected_at is null").fetchall()
    return people

@timeit
def get_profile(url):
    print("getting", url)
    # encode the url
    lix_url = (
        "https://api.lix-it.com/v1/person" + "?profile_link=" + url
    )

    # If data is missing then ignore errors and continue to next connection
    success = False
    while success == False:
        try:
            r = requests.get(lix_url, headers={"Authorization": API_KEY})
        except Exception as e:
            print("Error getting profile data for " + url)
            print(e)
            time.sleep(sleep_time)
            return 0
        # check status
        if r.status_code != 200:
            if r.status_code == 404:
                print("Profile not found: " + url)
                break
            if r.status_code == 429:
                print("Rate limit exceeded")
                time.sleep(sleep_time)
                continue
            # if a client error then stop
            if r.status_code > 399 and r.status_code < 500:
                print("Error getting profile: " + str(r.status_code))
                print(r.text)
                raise Exception("Client error " + str(r.status_code))
            # If an internal error then retry
            if r.status_code > 499:
                print("Error getting profile: " + str(r.status_code))
                print(r.text)
        success = True
        print("got", url)
        try:
            j = r.json()
        except Exception as e:
            print("Error parsing JSON")
            print(e)
            print(r.text)
            time.sleep(sleep_time)
            return 0
    if success:
        print("parsed", url)
        time.sleep(sleep_time)
    return j

# for each profile link, get the data from the Lix API and save
def collect_data(conn, people):
    for person in people:
        profile_url = person[2]
        data = get_profile(profile_url)
        if data == 0:
            continue
        json_data = json.dumps(data)
        # This assumes we are only running one thread and therefore don't need to lock the database
        conn.execute(
            "insert into people_enriched (person_id, data, collected_at) values (?, ?, ?)",
            (person[0], json_data, datetime.datetime.now()),
        )
        conn.execute(
            "update people set last_collected_at = ? where id = ?",
            (datetime.datetime.now(), person[0]),
        )
        conn.commit()
        print("collected", profile_url)



if __name__ == "__main__":
    if args.command == "migrate":
        conn = sqlite3.connect(db_path)
        migrate(conn)
        conn.close()
        print("Database created at {}. Please add profile links to the people table using the `import` command and then`run` to collect data.".format(db_path))
        sys.exit(0)
    
    if args.command == "import":
        conn = sqlite3.connect(db_path)
        print("Importing data from", args.import_path, "...")
        people = pd.read_csv(args.import_path)
        people.to_sql("people", conn, if_exists="append", index=False)
        conn.close()
        print("Data imported.")
        sys.exit(0)

    if args.api_key is None:
        print("Please provide an API key")
        sys.exit(1)

    # open the database if it doesn't exist then error and say to migrate first
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.OperationalError:
        print("Database does not exist. Run `python [PATH]/person.py migrate` first.")
        sys.exit(1)

    people = get_people(conn)
    print ("Collecting data for", len(people), "people")
    collect_data(conn, people)

    # close the database
    conn.close()
