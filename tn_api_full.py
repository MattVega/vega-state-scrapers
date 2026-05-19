import requests, json, time, base64

# Credentials from Next.js config
TOKEN_B64 = "NzY0MDk0YTktNmNmMi00ZTY4LTgxMTItMjdjNDk1MWI3NmM0OjYwMjgwYjQxLTFjNjgtNDBjZi05MWM0LWY0ODEyYTdkNmUyMQ=="
AUTH_URL = "https://access.cloud.commerce.tn.gov/entellitrak/auth/oauth/token?grant_type=client_credentials"
API_BASE = "https://access.cloud.commerce.tn.gov/entellitrak/api/endpoints/v1"

headers = {
    "Authorization": f"Basic {TOKEN_B64}",
    "Content-Type": "application/x-www-form-urlencoded"
}

# Get token
r = requests.post(AUTH_URL, headers=headers, timeout=15)
print(f"Auth: {r.status_code} - {r.text[:200]}")

if r.status_code == 200:
    token = r.json()['access_token']
    api_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Try the search configuration endpoint
    endpoints_to_try = [
        "/portal/search/configuration",
        "/portal/search",
        "/portal/search/results",
        "/licensee/search",
        "/license/search",
        "/contractor/search",
        "/search",
        "/board",
        "/boards",
        "/licenseType",
    ]
    
    for ep in endpoints_to_try:
        url = f"{API_BASE}{ep}"
        r2 = requests.get(url, headers=api_headers, timeout=15)
        ct = r2.headers.get('Content-Type', '')
        print(f"\n{ep}: {r2.status_code} {ct[:40]}")
        print(r2.text[:300])
        time.sleep(0.3)
