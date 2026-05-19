"""Tennessee contractor scraper - uses TDCI search API and Nashville open data"""
import requests, csv, json, time, os

# Try the Nashville open data (Socrata)
print("=== Nashville Metro Contractors (Socrata) ===")
url = "https://data.nashville.gov/resource/qqst-dkzw.json"
params = {"$limit": 50000, "$offset": 0}
try:
    r = requests.get(url, params=params, timeout=30)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Records: {len(data)}")
        if data:
            print(f"Fields: {list(data[0].keys())}")
            print(f"Sample: {data[0]}")
except Exception as e:
    print(f"Error: {e}")

print()

# Try the TDCI search API
print("=== TDCI Cloud Search API ===")
search_url = "https://search.cloud.commerce.tn.gov"
endpoints = [
    "/",
    "/api/",
    "/api/licensees",
    "/api/v1/licensees", 
    "/search/api/",
]
for ep in endpoints:
    try:
        r = requests.get(f"{search_url}{ep}", timeout=10)
        print(f"{ep}: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"{ep}: ERROR - {e}")
    time.sleep(0.3)
