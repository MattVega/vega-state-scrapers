#!/usr/bin/env python3
"""
North Dakota SOS Contractor Registry Scraper
Uses the firststop.sos.nd.gov API to pull all active contractor records.
Note: Search API returns name/class/status only — no phone/address.
We capture what's available and note what's missing.
"""
import requests, json, time, csv, string
from datetime import datetime

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
})

URL = "https://firststop.sos.nd.gov/api/Records/contractorsearch"
LOG = "/app/nd_scraper.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + "\n")

def search(prefix, active_only=True):
    payload = {
        "SEARCH_VALUE": prefix,
        "STARTS_WITH_YN": True,
        "ACTIVE_ONLY_YN": active_only
    }
    for attempt in range(3):
        try:
            r = session.post(URL, json=payload, timeout=20)
            data = r.json()
            return data.get('rows', {})
        except Exception as e:
            log(f"  Error on '{prefix}' attempt {attempt+1}: {e}")
            time.sleep(2)
    return {}

letters = string.ascii_uppercase
all_rows = {}

log("=== ND Contractor Scraper Started ===")

# Phase 1: single letters
log("Phase 1: Single-letter scan...")
capped = []
for L in letters:
    rows = search(L)
    count = len(rows)
    if count == 100:
        capped.append(L)
        log(f"  {L}: {count} (CAPPED - will expand)")
    else:
        all_rows.update(rows)
        log(f"  {L}: {count}")
    time.sleep(0.25)

log(f"Phase 1 done. Capped letters: {capped}. Unique so far: {len(all_rows)}")

# Phase 2: 2-letter combos for capped letters
log("Phase 2: 2-letter expansion for capped letters...")
still_capped = []
for L in capped:
    letter_count = 0
    for L2 in letters:
        prefix = L + L2
        rows = search(prefix)
        count = len(rows)
        all_rows.update(rows)
        letter_count += count
        if count == 100:
            still_capped.append(prefix)
            log(f"  {prefix}: STILL CAPPED at 100!")
        time.sleep(0.15)
    log(f"  {L}*: done ({letter_count} records)")

log(f"Phase 2 done. Still-capped prefixes: {still_capped}. Unique so far: {len(all_rows)}")

# Phase 3: 3-letter for any still-capped 2-letter combos
if still_capped:
    log("Phase 3: 3-letter expansion...")
    for prefix2 in still_capped:
        for L3 in letters:
            prefix = prefix2 + L3
            rows = search(prefix)
            all_rows.update(rows)
            time.sleep(0.15)
        log(f"  {prefix2}*: done")

log(f"All phases done. Total unique records: {len(all_rows)}")

# Extract and save
records = []
for rec_id, row in all_rows.items():
    title = row.get('TITLE', [''])
    company = title[0].strip() if len(title) > 0 else ''
    license_class = title[1].strip() if len(title) > 1 else ''
    records.append({
        'company_name': company,
        'license_class': license_class,
        'status': row.get('STATUS', ''),
        'standing': row.get('STANDING', ''),
        'filing_date': row.get('FILING_DATE', ''),
        'record_num': row.get('RECORD_NUM', ''),
        'nd_id': rec_id,
        'state': 'ND',
        'phone': '',
        'address': '',
        'city': '',
        'zip': '',
        'source': 'ND SOS Contractor Registry'
    })

out_file = '/app/nd_contractors_raw.csv'
with open(out_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['company_name','license_class','status','standing',
                                            'filing_date','record_num','nd_id','state',
                                            'phone','address','city','zip','source'])
    writer.writeheader()
    writer.writerows(records)

log(f"Saved {len(records)} records to {out_file}")
log("=== Done ===")
