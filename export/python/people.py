"""
This script exports data from the people_enriched table to a CSV file, picking only the name, link, and location fields.
"""
import csv
import sqlite3
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--output", help="The output file", default="output/people.csv")
parser.add_argument("--db-path", help="The path to the database", default="data/people.db")
args = parser.parse_args()

conn = sqlite3.connect(args.db_path)
c = conn.cursor()

c.execute("select data from people_enriched")
rows = c.fetchall()

# parse json and extract name, link, and location
rows = [
    (
        json.loads(row[0])["name"],
        json.loads(row[0])["link"],
        json.loads(row[0])["location"],
    )
    for row in rows
]

with open(args.output, "w") as f:
    print("Exporting {} rows to".format(len(rows)), args.output, "...")
    writer = csv.writer(f)
    writer.writerow(["name", "link", "location"])
    writer.writerows(rows)

print("Exported to", args.output)
