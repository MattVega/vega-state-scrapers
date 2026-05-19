"""
Bulk download contractor data from confirmed state sources
"""
import requests, csv, io, time, os, json
import pandas as pd

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

# Confirmed working URLs
SOURCES = [
    ('NY', 'Contractor Registry', 'https://data.ny.gov/api/views/i4jv-zkey/rows.csv?accessType=DOWNLOAD'),
    ('NY', 'Mold Contractor Licenses', 'https://data.ny.gov/api/views/ikqx-ispy/rows.csv?accessType=DOWNLOAD'),
    ('IL', 'Asbestos Contractors', 'https://illinois-edp.data.socrata.com/api/views/kt5u-9dcu/rows.csv?accessType=DOWNLOAD'),
    ('IL', 'Lead Contractors', 'https://illinois-edp.data.socrata.com/api/views/vpwp-h7xr/rows.csv?accessType=DOWNLOAD'),
    # MD - county level but useful
    ('MD', 'Master Electricians Montgomery County', 'https://data.montgomerycountymd.gov/api/views/v8mn-6i2r/rows.csv?accessType=DOWNLOAD'),
]

results = {}

for state, desc, url in SOURCES:
    print(f"\nDownloading {state} - {desc}...")
    try:
        r = s.get(url, timeout=60)
        ct = r.headers.get('content-type', '')
        print(f"  Status: {r.status_code} CT: {ct[:40]} Size: {len(r.content):,}")
        
        if r.status_code == 200 and len(r.text) > 500:
            lines = r.text.split('\n')
            print(f"  Lines: {len(lines)}")
            print(f"  Header: {lines[0][:120]}")
            if len(lines) > 1: print(f"  Sample: {lines[1][:120]}")
            
            fname = f"/app/{state.lower()}_{desc.lower().replace(' ','_')[:20]}.csv"
            with open(fname, 'w') as f:
                f.write(r.text)
            print(f"  Saved: {fname}")
            
            if state not in results:
                results[state] = []
            results[state].append((desc, fname, len(lines)-1))
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(1)

print(f"\n\nResults: {json.dumps({k: [(d,c) for d,f,c in v] for k,v in results.items()}, indent=2)}")

