"""
This script demonstrates how to use the Lix Contact API to retrieve email addresses from LinkedIn profiles.

The script takes a LinkedIn profile URL and API key, makes a request to the Contact API,
and saves the result to a JSON file in the data folder.

Usage: python email_lookup.py --api-key <API_KEY> --profile-url <LINKEDIN_URL>
"""

import argparse
import json
import requests
import time
import urllib.parse

parser = argparse.ArgumentParser()
parser.add_argument("--api-key", help="The API key for the Lix API", dest="api_key", required=True)
parser.add_argument("--profile-url", help="The LinkedIn profile URL to get email for", dest="profile_url", required=True)
parser.add_argument("--result-path", help="The path to save the JSON result", default="data/email_lookup_result.json")

args = parser.parse_args()
API_KEY = args.api_key
PROFILE_URL = args.profile_url
RESULT_PATH = args.result_path

sleep_time = 0.1

def timeit(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        print("Time taken: " + str(time.time() - start_time))
        return result
    return wrapper

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
        print("Status:", j.get("status", "Unknown"))
        if j.get("status") == "VALID":
            print("Email found:", j.get("email", "Not provided"))
        elif j.get("status") == "PROBABLE":
            print("Probable emails found:", j.get("alternatives", []))
        time.sleep(sleep_time)
    
    return j

if __name__ == "__main__":
    result = get_email_from_profile(PROFILE_URL)
    
    if result:
        with open(RESULT_PATH, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Result saved to {RESULT_PATH}")
    else:
        print("No result to save")
