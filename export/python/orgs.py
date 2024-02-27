"""
This script exports data from the orgs_enriched table to a CSV file, picking only the name, link, and location fields.
"""

import csv
import sqlite3
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--output", help="The output file", default="output/orgs.csv")
parser.add_argument(
    "--db-path", help="The path to the database", default="data/orgs.db"
)
args = parser.parse_args()

conn = sqlite3.connect(args.db_path)
c = conn.cursor()

c.execute("select data from orgs_enriched")
rows = c.fetchall()

# parse json and extract name, link, and location
rows = [
    (
        json.loads(row[0])["profile"]["name"],
        json.loads(row[0])["profile"]["linkedinUrl"],
        json.loads(row[0])["profile"]["industry"],
        json.loads(row[0])["profile"]["description"],
        json.loads(row[0])["profile"]["employeeCount"],
    )
    for row in rows
]

with open(args.output, "w") as f:
    print("Exporting {} rows to".format(len(rows)), args.output, "...")
    writer = csv.writer(f)
    writer.writerow(
        ["name", "linkedin_url", "industry", "description", "employee_count"]
    )
    writer.writerows(rows)

print("Exported to", args.output)
