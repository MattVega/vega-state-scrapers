#!/usr/bin/env python3
"""
Utah new contractor finder - uses DOPL public data download alternative endpoints
"""
import requests, re, time, csv
from datetime import datetime, timedelta
from io import StringIO

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
CUTOFF = datetime.now() - timedelta(days=365)
TODAY = datetime.now().strftime('%Y-%m-%d')

results = []

print("[UTAH] Trying DOPL data endpoints...")

s = requests.Session()
s.headers.update(HEADERS)

# Try 1: DOPL public contractor data CSV (various known URLs)
urls = [
    "https://dopl.utah.gov/lookup/csv/contractors.csv",
    "https://dopl.utah.gov/licensee/csv/contractors.csv",
    "https://dopl.utah.gov/lookup/contractor/csv/",
    "https://commerce.utah.gov/dopl/lookup/contractors.csv",
    "https://api.commerce.utah.gov/dopl/contractors.csv",
]

for url in urls:
    try:
        r = s.get(url, timeout=15, allow_redirects=True)
        print(f"  {url[:60]} -> {r.status_code} | {len(r.text)} bytes")
        if r.status_code == 200 and ',' in r.text[:500] and len(r.text) > 1000:
            print("  SUCCESS! Parsing CSV...")
            reader = csv.DictReader(StringIO(r.text))
            for row in reader:
                results.append(dict(row))
            print(f"  Got {len(results)} rows")
            break
    except Exception as e:
        print(f"  Error: {e}")

# Try 2: DOPL JSON API
if not results:
    print("\n[UTAH] Trying DOPL JSON API...")
    trade_keywords = ['drywall', 'paint', 'floor', 'plaster', 'tile', 'framing', 'stucco', 'finish', 'wallboard', 'ceiling']
    api_endpoints = [
        "https://dopl.utah.gov/lookup/contractor/api/search/",
        "https://dopl.utah.gov/lookup/api/contractor/search",
        "https://secure.utah.gov/dopl-contractors/api/search",
    ]
    for endpoint in api_endpoints:
        for kw in trade_keywords[:3]:
            try:
                r = s.get(endpoint, params={'q': kw, 'limit': 200}, timeout=10)
                print(f"  {endpoint[:50]} q={kw} -> {r.status_code}")
                if r.status_code == 200 and r.text.startswith('[') or r.text.startswith('{'):
                    data = r.json()
                    print(f"  Got JSON! Type: {type(data)}, len: {len(data) if isinstance(data, list) else 'dict'}")
                    break
            except: pass

# Try 3: Utah Open Data via Socrata - DOPL dataset
if not results:
    print("\n[UTAH] Trying Utah Open Data Socrata...")
    socrata_urls = [
        "https://opendata.utah.gov/resource/contractor-licenses.json",
        "https://opendata.utah.gov/resource/dopl-contractors.json",
        "https://data.utah.gov/resource/contractor-licenses.json",
    ]
    for url in socrata_urls:
        try:
            r = s.get(url, timeout=10)
            print(f"  {url} -> {r.status_code}")
            if r.status_code == 200:
                print(f"  Response: {r.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")

# Try 4: Utah new business filings via SOS (construction keywords)
print("\n[UTAH] Trying Utah SOS entity search for new construction companies...")
construction_kws = ['drywall', 'painting', 'flooring', 'plaster', 'tile', 'finish carpenter', 'wallboard']
sos_url = "https://secure.utah.gov/bes/index.html"

for kw in construction_kws[:3]:
    try:
        # Try their search
        r = s.get(f"https://secure.utah.gov/bes/search?q={kw}&type=ALL&status=A", timeout=10)
        print(f"  SOS search '{kw}': {r.status_code} | {len(r.text)} bytes | CF: {'cloudflare' in r.text.lower()}")
    except Exception as e:
        print(f"  SOS Error: {e}")

print(f"\nUtah results found: {len(results)}")

# If we got results, filter by date
if results:
    import pandas as pd
    df = pd.DataFrame(results)
    print("Columns:", list(df.columns))
    
    # Look for date column
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'issue' in c.lower() or 'original' in c.lower()]
    print("Date columns:", date_cols)
    
    if date_cols:
        dc = date_cols[0]
        def parse_date(d):
            for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
                try: return datetime.strptime(str(d), fmt)
                except: pass
            return None
        df['parsed_date'] = df[dc].apply(parse_date)
        new_df = df[df['parsed_date'] >= CUTOFF]
        print(f"New (last 12 months): {len(new_df)} of {len(df)} total")
        new_df.to_csv(f'/app/ut_new_companies_{TODAY}.csv', index=False)
        print(f"Saved: /app/ut_new_companies_{TODAY}.csv")

