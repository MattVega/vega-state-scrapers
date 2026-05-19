import requests, json, time

# Try the TDCI verify portal API 
# The portal at verify.tn.gov should have an underlying API
test_urls = [
    "https://verify.tn.gov/api/search?profession=contractors&name=&limit=50",
    "https://verify.tn.gov/api/licensees?type=contractor&limit=50",
    "https://access.cloud.commerce.tn.gov/entellitrak/rd/public/lookup/search",
    "https://search.cloud.commerce.tn.gov/api/search?type=contractor&limit=50",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

for url in test_urls:
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print(f"\n{url}")
        print(f"Status: {r.status_code}")
        ct = r.headers.get('Content-Type', '')
        print(f"Content-Type: {ct}")
        print(r.text[:300])
    except Exception as e:
        print(f"{url}: {e}")
    time.sleep(0.5)
