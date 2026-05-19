import requests, json, time, csv

TOKEN_B64 = "NzY0MDk0YTktNmNmMi00ZTY4LTgxMTItMjdjNDk1MWI3NmM0OjYwMjgwYjQxLTFjNjgtNDBjZi05MWM0LWY0ODEyYTdkNmUyMQ=="
AUTH_URL = "https://access.cloud.commerce.tn.gov/entellitrak/auth/oauth/token?grant_type=client_credentials"
API_BASE = "https://access.cloud.commerce.tn.gov/entellitrak/api/endpoints/v1"

def get_token():
    r = requests.post(AUTH_URL, headers={"Authorization": f"Basic {TOKEN_B64}", "Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
    return r.json()['access_token']

token = get_token()
hdrs = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}

# First, check what a result record looks like
payload = {
    "lookupString": "contractor",
    "rows": 5,
    "start": 0,
    "type": "credential",
    "highlight": "true",
    "appliedFilters": None,
    "formRequest": None
}
r = requests.post(f"{API_BASE}/portal/search", headers=hdrs, json=payload, timeout=30)
data = r.json()
print("Keys in response:", list(data.keys()))
if 'results' in data:
    print(f"\nTotal results: {data.get('totalCount', 'unknown')}")
    print(f"\nSample record:")
    if data['results']:
        print(json.dumps(data['results'][0], indent=2))
