"""
This script retrieves search pages from the Lix API using programmatic
filters. It runs through all permutations of job titles and companies.

It queries the Lix API to get the ID of the job titles and companies and
uses these IDs to build a search URL to get the search results.

Data is saved as JSONL files in the data folder.
"""

import requests
import argparse
import sys
import time
import json
import sqlite3
import faulthandler
import urllib.parse


faulthandler.enable(),

parser = argparse.ArgumentParser()

parser.add_argument("--api-key", help="The API key for the Lix API", dest="api_key")
parser.add_argument(
    "--db-path", help="The path to the database", default="data/search_leads.db"
)

args = parser.parse_args()
API_KEY = args.api_key
db_path = args.db_path

search_url_base = "https://api.lix-it.com/v1/li/sales/search/people"
facet_url_base = "https://api.lix-it.com/v1/search/sales/facet"

sleep_time = 3  # sleep for 3 seconds to avoid rate limit

# The job titles and companies we want to search for
job_facets = ["Software engineer"]
company_facets = ["Google"]


def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print("Time taken: " + str(time.time() - start_time))
        return result

    return wrapper

def build_search_url(filters):
    """
    Build the search URL from the filters
    """
    return f"https://www.linkedin.com/sales/search/people?query=(filters%3A{urllib.parse.quote(filters, safe="")})"

def build_query_filters(job_title_pairs, company_pairs):
    """
    Build a filter string from the job title and company pairs.

    The ids and text should be URL encoded before being put into the filter.

    The filter will also later be URL encoded, but this is a separate step.
    """
    job_title_filters = []
    for job_title_pair in job_title_pairs:
        job_title_filters.append(f"(id:{job_title_pair[0]},text:{urllib.parse.quote(job_title_pair[1], safe="")},selectionType:INCLUDED)")
    job_title_filter = ""
    if len(job_title_filters) > 0:
        job_title_filter = f"(type:CURRENT_TITLE,values:List({','.join(job_title_filters)}))"

    current_company_filters = []
    for company_pair in company_pairs:
        current_company_filters.append(f"(id:{urllib.parse.quote(company_pair[0], safe="")},text:{urllib.parse.quote(company_pair[1], safe="")},selectionType:INCLUDED,parent:(id:0))")
    company_filter = ""
    if len(current_company_filters) > 0:
        company_filter = f"(type:CURRENT_COMPANY,values:List({','.join(current_company_filters)}))"

    filters = []
    if job_title_filter:
        filters.append(job_title_filter)
    if company_filter:
        filters.append(company_filter)

    return f"List({','.join(filters)})"

def get_job_title_facet(facet_query):
    """
    Get the ID of the job title
    """
    facet_url = facet_url_base + f"?type=TITLE&query={urllib.parse.quote(facet_query, safe="")}"
    r = requests.get(facet_url, headers={"Authorization": API_KEY})
    j = r.json()
    if r.status_code != 200:
        print("Error getting job title facet")
        print(r.text)
        return (0, "")
    print (j)
    time.sleep(sleep_time)
    result = j["data"]["elements"][0]
    return (result["id"], result["displayValue"])

def get_company_facet(facet_query):
    """
    Get the ID of the company
    """
    facet_url = facet_url_base + f"?type=COMPANY_WITH_LIST&query={urllib.parse.quote(facet_query, safe="")}"
    r = requests.get(facet_url, headers={"Authorization": API_KEY})
    if r.status_code != 200:
        print("Error getting company facet")
        print(r.text)
        return (0, "")
    j = r.json()
    print (j)
    time.sleep(sleep_time)
    result = j["data"]["elements"][0]["children"][0]
    return (result["id"], result["displayValue"])


@timeit
def get_page(url):
    print("getting", url)
    # encode the url
    lix_profile_url = (
        search_url_base + "?url=" + urllib.parse.quote(url, safe="")
    )
    # If data is missing then ignore errors and continue to next connection
    success = False
    while success == False:
        try:
            r = requests.get(lix_profile_url, headers={"Authorization": API_KEY})
        except Exception as e:
            print("Error getting profile data for " + url)
            print(e)
            time.sleep(sleep_time)
            return 0
        # check status
        if r.status_code != 200:
            print("Error getting page: " + str(r.status_code))
            print(r.text)
            break
        success = True
        print("got", url)
        print(r.json())
        # try:
        #     j = r.json()
        #     # write to connections
        #     c = conn.cursor()
        #     stmt = "INSERT OR REPLACE INTO connections (li_id, json) VALUES (?, ?)"
        #     c.execute(
        #         stmt,
        #         (
        #             profile_id,
        #             json.dumps(j),
        #         ),
        #     )
        #     conn.commit()
        # except Exception as e:
        #     print("Error parsing JSON")
        #     print(e)
        #     print(r.text)
        #     time.sleep(sleep_time)
        #     db_lock.release()
        #     return 0
    if success:
        print("saved!", url)
        time.sleep(sleep_time)
    return 1


# create an sqlite connection
# we use a local database in case we have intermittent connection or memory issues

# write to json files
# load all the connections from the db
# write to json file

if __name__ == "__main__":
    # get the facets
    job_facet_pairs = []
    company_facet_pairs = []

    for facet_query in job_facets:
        job_facet_pairs.append(get_job_title_facet(facet_query))


    for facet_query in company_facets:
        company_facet_pairs.append(get_company_facet(facet_query))

    print(job_facet_pairs, company_facet_pairs)

    filters = build_query_filters(job_facet_pairs, company_facet_pairs)
    
    search_url = build_search_url(filters)
    print(search_url)
    get_page(search_url)