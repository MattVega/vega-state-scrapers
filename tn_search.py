import requests, json, time

TOKEN_B64 = "NzY0MDk0YTktNmNmMi00ZTY4LTgxMTItMjdjNDk1MWI3NmM0OjYwMjgwYjQxLTFjNjgtNDBjZi05MWM0LWY0ODEyYTdkNmUyMQ=="
AUTH_URL = "https://access.cloud.commerce.tn.gov/entellitrak/auth/oauth/token?grant_type=client_credentials"
API_BASE = "https://access.cloud.commerce.tn.gov/entellitrak/api/endpoints/v1"

r = requests.post(AUTH_URL, headers={"Authorization": f"Basic {TOKEN_B64}", "Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
token = r.json()['access_token']
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

# Get the configuration to understand the search structure
r = requests.get(f"{API_BASE}/portal/search/configuration", headers=headers, timeout=15)
config = r.json()
print("Search config:")
print(json.dumps(config, indent=2)[:2000])

# The search config should tell us search options/types

# The search is POST-based - let's try POST to /portal/search with keyword
search_url = f"{API_BASE}/portal/search"
payload = {"keyword": "contractor", "type": None, "page": 0, "size": 50}
r = requests.post(search_url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=15)
print(f"\nPOST /portal/search: {r.status_code}")
print(r.text[:500])

# Also try with just a letter
payload2 = {"keyword": "a", "page": 0, "size": 50}
r2 = requests.post(search_url, headers={**headers, "Content-Type": "application/json"}, json=payload2, timeout=15)
print(f"\nPOST /portal/search 'a': {r2.status_code}")
print(r2.text[:500])
