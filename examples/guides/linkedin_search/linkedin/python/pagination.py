"""
This script demonstrates how to use the Lix API to paginate through the results of a standard LinkedIn People search.

It starts by making a GET request to the Lix API to get the first page of search results. It then extracts the paging 
information from the response and continues to make subsequent requests to get the next pages of results until it has 
retrieved all the results.

Data is saved as a JSONL file in the data folder.

Usage:
    python pagination.py --api-key YOUR_API_KEY --result-path data/linkedinPeopleSearch.jsonl

The search URL should be a standard LinkedIn people search URL, for example:
    https://www.linkedin.com/search/results/people/?keywords=software%20engineer&origin=GLOBAL_SEARCH_HEADER
"""

import json
import argparse
import requests
import time
import urllib.parse
import uuid


parser = argparse.ArgumentParser()

parser.add_argument("--api-key", help="The API key for the Lix API", dest="api_key", required=True)
parser.add_argument(
    "--result-path", help="The path to the JSONL results file", default="data/linkedinPeopleSearch.jsonl"
)
parser.add_argument(
    "--max-results", help="Maximum number of results to retrieve (default: no limit)", type=int, default=None
)

args = parser.parse_args()
API_KEY = args.api_key
RESULT_PATH = args.result_path
MAX_RESULTS = args.max_results
SLEEP_TIME = 3  # number of seconds to sleep between requests to avoid rate limit

# Example search URL - replace with your own LinkedIn people search URL
base_search_url = "https://www.linkedin.com/search/results/people/?keywords=software%20engineer&origin=GLOBAL_SEARCH_HEADER"


def get_page(url, start, sequence_id):
    """
    Fetch a single page of search results from the Lix API.
    
    Args:
        url: The LinkedIn search URL
        start: The offset to start from (0-indexed)
        sequence_id: A unique identifier to maintain collection settings between requests
    
    Returns:
        The JSON response from the API, or None on failure
    """
    print(f"Getting results starting at offset {start}")
    
    headers = {
        'Authorization': API_KEY, 
    }
    
    # Add or update the page parameter in the URL
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    # Calculate page number from start offset (assuming 10 results per page for standard search)
    page = (start // 10) + 1 if start > 0 else 1
    query_params['page'] = [str(page)]
    
    # Rebuild the URL with the updated page parameter
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    paginated_url = urllib.parse.urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    
    # URL encode the LinkedIn URL for the API request
    encoded_url = urllib.parse.quote(paginated_url, safe='')
    
    # Build the API URL with sequence_id
    api_url = f"https://api.lix-it.com/v1/li/linkedin/search/people?url={encoded_url}"
    if sequence_id:
        api_url += f"&sequence_id={sequence_id}"
    
    success = False
    while not success:
        try:
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                success = True
                time.sleep(SLEEP_TIME)
                return response.json()
            elif response.status_code == 429:
                print(f"Rate limited, waiting {SLEEP_TIME} seconds...")
                time.sleep(SLEEP_TIME)
                continue
            elif response.status_code >= 500:
                print(f"Server error ({response.status_code}), retrying...")
                time.sleep(SLEEP_TIME)
                continue
            else:
                print(f"Error getting page: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"Request failed: {e}")
            time.sleep(SLEEP_TIME)
            continue
    
    return None


def collect_search(start_offset=0):
    """
    Collect all search results by paginating through the API.
    
    Args:
        start_offset: The offset to start from (for resuming interrupted collections)
    """
    finish = False
    current_start = start_offset
    
    # Generate a unique sequence ID for this collection run
    sequence_id = str(uuid.uuid4())
    
    count = 0
    while not finish:
        print(f"Current offset: {current_start}, Total collected: {count}")
        
        result = get_page(base_search_url, current_start, sequence_id)
        
        if result is None:
            print("Failed to get page, stopping collection.")
            break
        
        # Handle the response structure - the API returns { "response": { ... }, "meta": { ... } }
        response_data = result.get('response', result)
        paging = response_data.get('paging', {})
        
        # Update sequence_id if returned by the API
        meta = result.get('meta', {})
        if meta.get('sequenceId'):
            sequence_id = meta['sequenceId']
        
        page_count = paging.get('count', 0)
        total = paging.get('total', 0)
        page_start = paging.get('start', current_start)
        
        count += page_count
        
        # Add metadata to the result for tracking
        result['_collection_metadata'] = {
            'offset': current_start,
            'sequence_id': sequence_id
        }
        
        with open(RESULT_PATH, 'a') as f:
            f.write(json.dumps(result) + '\n')
        
        print(f"Total available: {total}, Collected so far: {count}")
        
        # Check termination conditions
        if count >= total:
            print("Collected all available results.")
            finish = True
        elif MAX_RESULTS and count >= MAX_RESULTS:
            print(f"Reached maximum results limit ({MAX_RESULTS}), stopping.")
            finish = True
        elif page_count == 0:
            print("No more results returned, stopping.")
            finish = True
        else:
            # Move to the next page
            current_start = page_start + page_count


if __name__ == "__main__":
    # Open up the result file to see how many results we've retrieved so far
    start_offset = 0
    try:
        with open(RESULT_PATH, "r") as f:
            results = f.readlines()
            if results:
                # Calculate the starting offset from the last result
                last_result = json.loads(results[-1])
                response_data = last_result.get('response', last_result)
                paging = response_data.get('paging', {})
                last_start = paging.get('start', 0)
                last_count = paging.get('count', 0)
                start_offset = last_start + last_count
                print(f"Resuming from offset {start_offset}")
    except FileNotFoundError:
        # Create the data directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(RESULT_PATH), exist_ok=True)
        open(RESULT_PATH, 'a').close()
    
    collect_search(start_offset)
