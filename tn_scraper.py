"""Tennessee TDCI contractor license API"""
import requests, csv, json, time, os

token_b64 = 'NzY0MDk0YTktNmNmMi00ZTY4LTgxMTItMjdjNDk1MWI3NmM0OjYwMjgwYjQxLTFjNjgtNDBjZi05MWM0LWY0ODEyYTdkNmUyMQ=='
API_BASE = 'https://access.cloud.commerce.tn.gov/entellitrak/api/endpoints/v1'

def get_token():
    r = requests.post('https://access.cloud.commerce.tn.gov/entellitrak/auth/oauth/token?grant_type=client_credentials',
        headers={'Authorization': f'Basic {token_b64}', 'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=15)
    return r.json()['access_token']

token = get_token()
headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}

# Explore the API
print("Exploring TN API...")
r = requests.get(f"{API_BASE}", headers=headers, timeout=15)
print(f"Base: {r.status_code} {r.text[:300]}")

# Try license endpoint
for endpoint in ['licenses', 'licensees', 'contractors', 'boards', 'license-types', 'search']:
    r = requests.get(f"{API_BASE}/{endpoint}", headers=headers, timeout=10)
    print(f"/{endpoint}: {r.status_code} {r.text[:100]}")
    time.sleep(0.2)

