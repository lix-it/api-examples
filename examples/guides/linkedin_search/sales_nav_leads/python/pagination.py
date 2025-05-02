"""
This script demonstrates how to use the Lix API to paginate through the results of a LinkedIn Sales Navigator search.

It starts by making a POST request to the Lix API to get the first page of search results. It then extracts the sequence ID and the total number of results from the response. 
It continues to make subsequent requests to get the next pages of results until it has retrieved all the results.

Data is saved as a JSONL file in the data folder.
"""

import json
import argparse
import requests
import time


parser = argparse.ArgumentParser()

parser.add_argument("--api-key", help="The API key for the Lix API", dest="api_key")
parser.add_argument(
    "--result-path", help="The path to the JSONL results file", default="data/searchLeadsPagination.jsonl"
)

args = parser.parse_args()
API_KEY = args.api_key
RESULT_PATH = args.result_path
SLEEP_TIME = 3 # number of seconds to sleep between requests to avoid rate limit

base_search_url = "https://www.linkedin.com/sales/search/people#_ntb=17cxdwWvR5uFdc3u0WPY7g%3D%3D&query=(recentSearchParam%3A(id%3A2400172257%2CdoLogHistory%3Atrue)%2Cfilters%3AList((type%3ACURRENT_COMPANY%2Cvalues%3AList((id%3Aurn%253Ali%253Aorganization%253A1337%2Ctext%3ALinkedIn%2CselectionType%3AINCLUDED)))%2C(type%3ASENIORITY_LEVEL%2Cvalues%3AList((id%3A220%2Ctext%3ADirector%2CselectionType%3AINCLUDED)%2C(id%3A300%2Ctext%3AVice%2520President%2CselectionType%3AINCLUDED)%2C(id%3A310%2Ctext%3ACXO%2CselectionType%3AINCLUDED)))%2C(type%3ACURRENT_TITLE%2Cvalues%3AList((text%3A%2522Product%2520Management%2522%2520OR%2520%2522VP%2520Product%2520Management%2522%2520OR%2520%2522Vice%2520President%2520of%2520Product%2520management%2522%2520OR%2520%2522Director%2520of%2520Product%2520Management%2520%2522%2520OR%2520%2522Head%2520of%2520Product%2520Management%2522%2520OR%2520%2522VP%252C%2520Product%2520Management%2522%2520OR%2520%2522VP%2520of%2520Product%2520Management%2522%2520OR%2520%2522Vice%2520President%252C%2520Product%2520management%2522%2520OR%2520%2522Product%2520Marketing%2522%2520OR%2520%2522VP%2520of%2520Product%2520Marketing%2522%2520OR%2520%2522Vice%2520President%2520Product%2520Marketing%2522%2520OR%2520%2522Vice%2520President%2520of%2520Product%2520Marketing%2522%2520OR%2520%2522Director%2520of%2520Product%2520Marketing%2520%2522%2520OR%2520%2522Head%2520of%2520Product%2520Marketing%2522%2520OR%2520%2522VP%2520Solution%2520Marketing%2522%2520OR%2520%2522Demand%2520Generation%2522%2520OR%2520%2522Vice%2520President%2520of%2520demand%2520Generation%2522%2520OR%2520%2522Head%2520of%2520Demand%2520generation%2522%2520OR%2520%2522Director%2520of%2520Demand%2520generation%2522%2520OR%2520%2522Product%2522%2520OR%2520%2522VP%2520Product%2522%2520OR%2520%2522VP%2520of%2520Product%2522%2520OR%2520%2522Vice%2520president%2520of%2520Product%2522%2520OR%2520%2522head%2520of%2520Product%2522%2520OR%2520%2522Director%2520of%2520product%2522%2520OR%2520%2522Customer%2520Marketing%2522%2520OR%2520%2522Vp%2520of%2520Customer%2520Marketing%2522%2520OR%2520%2522Vice%2520president%2520of%2520Customer%2520Marketing%2522%2520OR%2520%2522Head%2520of%2520Customer%2520Marketing%2522%2520OR%2520%2522Director%2520of%2520Customer%2520Marketing%2522%2520OR%2520%2522Director%2520Analyst%2520Relations%2522%2520OR%2520%2522Director%2520of%2520Analyst%2520Relations%2522%2520OR%2520%2522Head%2520of%2520Analyst%2520Relations%2522%2520OR%2520%2522Chief%2520Executive%2520Officer%2522%2520OR%2520%2522CEO%2522%2520OR%2520%2522Chief%2520Executive%2522%2520OR%2520%2522CMO%2522%2520OR%2520%2522Chief%2520Marketing%2520Officer%2522%2520OR%2520%2522Chief%2520Product%2520Officer%2522%2520OR%2520%2522SVP%2520Product%2522%2520OR%2520%2522VP%2520Service%2520Offerings%2522%2520OR%2520%2522VP%2520Product%2520Officer%2522%2520OR%2520%2522Service%2520Management%2522%2520OR%2520%2522Advanced%2520Technology%2522%2520OR%2520%2522Service%2520Line%2520Manager%2522%2520OR%2520%2522Integrated%2520Marketing%2522%2520OR%2520%2522General%2520Manager%2522%2520OR%2520%2522Chief%2520Technology%2520Officer%2522%2520OR%2520%2522CTO%2522%2520OR%2520%2522Product%2520Manager%2522%2520OR%2520%2522Senior%2520Product%2520Manager%2522%2520OR%2520%2522Director%2520Product%2520management%2522%2520OR%2520%2522VP%2520of%2520solution%2520Marketing%2522%2520OR%2520%2522Solution%2520Marketing%2522%2520OR%2520%2522VP%2520of%2520Demand%2520generation%2522%2520OR%2520%2522regional%2520head%2520of%2520marketing%2522%2520OR%2520%2522BU%2520head%2520of%2520marketing%2522%2520OR%2520%2522Head%2520of%2520marketing%2522%2520OR%2520%2522Chief%2520Strategy%2520Officer%2522%2520OR%2520%2522CSO%2522%2520OR%2520%2522Delivery%2520leader%2522%2520OR%2520%2522Board%2520of%2520Directors%2522%2520OR%2520%2522VP%2520of%2520marketing%2522%2520OR%2520%2522VP%2520of%2520sales%2522%2520OR%2520%2522Product%2520Development%2522%2520OR%2520%2522VP%2520Product%2520Development%2522%2520OR%2520%2522Director%2520product%2520Development%2522%2520OR%2520%2522Director%2520Product%2520marketing%2522%2520OR%2520%2522Demand%2520Gen%2522%2520OR%2520%2522CPO%2522%2520OR%2520%2522Product%2520Development%2522%2520OR%2520%2522VP%2520Product%2520Development%2522%2520OR%2520%2522Vice%2520President%2520of%2520Product%2520Development%2522%2520OR%2520%2522Director%2520of%2520Product%2520Development%2520%2522%2520OR%2520%2522Head%2520of%2520Product%2520Development%2522%2520OR%2520%2522VP%252C%2520Product%2520Development%2522%2520OR%2520%2522VP%2520of%2520Product%2520Development%2522%2520OR%2520%2522Vice%2520President%252C%2520Product%2520Development%2522%2520OR%2520%2522Business%2520Unit%2520Head%2520of%2520Marketing%2522%2520OR%2520%2522Vice%2520President%2520Customer%2520Marketing%2522%2520OR%2520%2522Analyst%2520Relations%2522%2520OR%2520%2522Sr%2520Director%2520of%2520Analyst%2520Relations%2522%2520OR%2520%2522Chief%2520Marketing%2522%2520OR%2520%2522C.E.O.%2522%2520OR%2520%2522Chief%2520Product%2522%2520OR%2520%2522c.e.o.%2522%2CselectionType%3AINCLUDED)))%2C(type%3AREGION%2Cvalues%3AList((id%3A103644278%2Ctext%3AUnited%2520States%2CselectionType%3AINCLUDED)))))&sessionId=Bj7j4q%2FzTEOY9SsYR03v9Q%3D%3D"

def get_page(url, page, sequence_id):
    print("Getting page", page)
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': API_KEY, 
    }
    payload = {
        # NOTE: you do not need to URL encode the url if you are using the POST version of the endpoint.
        "url": url + f"&page={page}",
        "sequence_id": sequence_id,
    }
    success = False
    while success == False:
        # Using the POST version of this endpoint allows you to use very large queries that would not fit in a URL
        response = requests.request(
            "POST",
            "http://api.lix-it.com/v1/li/sales/search/people",
            headers=headers,
            data=payload,
        )

        if response.status_code != 200:
            print("Error getting page: " + str(response.status_code))   
            time.sleep(SLEEP_TIME)
            continue

        time.sleep(SLEEP_TIME)

        return response.json()

    return 1

def collect_search(start_page = 1):
    finish = False
    page = start_page

    sequence_id = ""
    count = 0
    per_page = 25
    while not finish:
        print("page:", page, "sequence_id:", sequence_id, "count:", count)

        result = get_page(base_search_url, page, sequence_id)

        count += result['paging']['count']

        # add the page to the results
        for i in range(len(result['people'])):
            result['people'][i]['page'] = page

        with open(RESULT_PATH, 'a') as f:
            f.write(json.dumps(result) + '\n')

        print("total:", result['paging']['total'], "count:", count, "finish:", finish)

        if count >= result['paging']['total']:
            finish = True
        else:
            sequence_id = result['meta']['sequenceId']
            page = page + 1



if __name__ == "__main__":
    # Open up the result file to see how many pages we've retrieved so far
    start_page = 1
    try:
        with open(RESULT_PATH, "r") as f:
            results = f.readlines()
            start_page = len(results) + 1
    except FileNotFoundError:
        open(RESULT_PATH, 'a').close()

    collect_search(start_page)
