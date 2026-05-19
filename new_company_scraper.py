#!/usr/bin/env python3
"""
New Subcontractor Company Finder
- Utah: DOPL contractor license registry filtered for licenses issued in last 12 months
- Texas: TDLR license registry (electrical, A/C) + Texas SOS new business filings via name keyword search
Both filtered to construction/trade contractors only.
"""

import requests
import pandas as pd
import re
import json
from datetime import datetime, timedelta
from io import StringIO
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

CUTOFF_DATE = datetime.now() - timedelta(days=365)
TODAY = datetime.now().strftime('%Y-%m-%d')

print(f"Looking for licenses/entities created after {CUTOFF_DATE.strftime('%Y-%m-%d')}")
print("="*60)

all_results = []

# ─────────────────────────────────────────────
# UTAH — DOPL Contractor License API
# ─────────────────────────────────────────────
print("\n[UTAH] Querying DOPL contractor license API...")

UTAH_TRADES = ['drywall', 'paint', 'floor', 'plaster', 'stucco', 'tile', 'finish', 'framing', 'ceiling']

try:
    # Utah DOPL has a public search endpoint
    session = requests.Session()
    session.headers.update(HEADERS)
    
    ut_results = []
    
    for trade_kw in UTAH_TRADES:
        try:
            # Try the DOPL public lookup API
            url = f"https://dopl.utah.gov/lookup/contractor/ajax/search/"
            params = {
                'q': trade_kw,
                'lictype': 'CO',
                'page': 1,
                'per_page': 100
            }
            r = session.get(url, params=params, timeout=15)
            if r.status_code == 200 and r.text.strip().startswith('{'):
                data = r.json()
                contractors = data.get('results', data.get('contractors', data.get('data', [])))
                for c in contractors:
                    name = c.get('business_name', c.get('name', ''))
                    issue_date = c.get('issue_date', c.get('license_date', c.get('original_issue_date', '')))
                    phone = c.get('phone', c.get('telephone', ''))
                    address = c.get('address', '')
                    city = c.get('city', '')
                    if name:
                        ut_results.append({
                            'Company Name': name,
                            'Contact Name': c.get('owner_name', c.get('contact_name', '')),
                            'Trade': trade_kw.title(),
                            'State': 'UT',
                            'City': city,
                            'Address': address,
                            'Phone': phone,
                            'Email': c.get('email', ''),
                            'Website': c.get('website', ''),
                            'License Number': c.get('license_number', c.get('licno', '')),
                            'License Issue Date': issue_date,
                            'Source': 'Utah DOPL'
                        })
            time.sleep(0.5)
        except Exception as e:
            pass
    
    if ut_results:
        print(f"  Found {len(ut_results)} Utah DOPL results via API")
    else:
        print("  DOPL API blocked — trying alternative Utah source...")
        
        # Alternative: Utah SOS new entity search (construction keywords)
        construction_keywords = [
            'drywall', 'paint', 'flooring', 'plastering', 'stucco',
            'tile', 'drywalling', 'painting contractor', 'floor covering',
            'wallboard', 'framing', 'ceiling'
        ]
        
        for kw in construction_keywords:
            try:
                # Utah SOS entity search
                url = "https://secure.utah.gov/bes/index.html"
                # Try their search endpoint
                search_url = f"https://secure.utah.gov/bes/search.html"
                params = {'q': kw, 'type': 'ALL', 'status': 'ACTIVE'}
                r = session.get(search_url, params=params, timeout=15)
                if r.status_code == 200 and 'result' in r.text.lower():
                    # Parse HTML results
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, 'html.parser')
                    rows = soup.find_all('tr')
                    for row in rows[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            name = cols[0].get_text(strip=True)
                            reg_date = cols[2].get_text(strip=True) if len(cols) > 2 else ''
                            entity_type = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                            if name and reg_date:
                                try:
                                    reg_dt = datetime.strptime(reg_date, '%m/%d/%Y')
                                    if reg_dt >= CUTOFF_DATE:
                                        ut_results.append({
                                            'Company Name': name,
                                            'Contact Name': '',
                                            'Trade': kw.title(),
                                            'State': 'UT',
                                            'City': '',
                                            'Address': '',
                                            'Phone': '',
                                            'Email': '',
                                            'Website': '',
                                            'License Number': '',
                                            'License Issue Date': reg_date,
                                            'Source': 'Utah SOS'
                                        })
                                except:
                                    pass
                time.sleep(0.3)
            except Exception as e:
                pass
        
        if ut_results:
            print(f"  Found {len(ut_results)} Utah SOS results")
        else:
            print("  Utah SOS also blocked — will use Socrata API")
    
    all_results.extend(ut_results)

except Exception as e:
    print(f"  Utah error: {e}")

# ─────────────────────────────────────────────
# TEXAS — TDLR (licensed trades) + keyword new entity search
# ─────────────────────────────────────────────
print("\n[TEXAS] Querying TDLR license API...")

try:
    session2 = requests.Session()
    session2.headers.update(HEADERS)
    
    tx_results = []
    
    # TDLR has Socrata API - filter for recently licensed trades
    # Relevant license types from TDLR
    TDLR_TYPES = ['Electrical Contractor', 'A/C Contractor', 'Appliance Installation Contractor']
    
    for lic_type in TDLR_TYPES:
        try:
            # Socrata API for TDLR - filter by expiration date proxy for new licenses
            # Licenses expiring 2026-2027 = issued 2024-2025 (2-year license cycle)
            url = "https://data.texas.gov/resource/7358-krk7.json"
            params = {
                '$where': f"license_type='{lic_type}'",
                '$limit': 5000,
                '$order': 'license_number DESC'  # Higher numbers = newer
            }
            r = session2.get(url, params=params, timeout=30)
            if r.status_code == 200:
                data = r.json()
                print(f"  TDLR {lic_type}: {len(data)} records")
                for rec in data:
                    name = rec.get('business_name', '')
                    phone = rec.get('business_telephone', rec.get('owner_telephone', ''))
                    address = rec.get('business_address_line1', '')
                    city_state_zip = rec.get('business_city_state_zip', '')
                    city = city_state_zip.split(',')[0].strip() if ',' in city_state_zip else city_state_zip.split(' TX')[0].strip()
                    exp_date = rec.get('license_expiration_date_mmddccyy', '')
                    
                    # Estimate new: license expires 2026 or 2027 = issued recently
                    is_new = False
                    if exp_date:
                        try:
                            exp_dt = datetime.strptime(exp_date, '%m/%d/%Y')
                            # If expires in 2026-2027, issued within last 1-2 years
                            if exp_dt.year >= 2026:
                                is_new = True
                        except:
                            pass
                    
                    if name and is_new:
                        tx_results.append({
                            'Company Name': name,
                            'Contact Name': rec.get('owner_name', ''),
                            'Trade': lic_type.replace(' Contractor','').replace('A/C','HVAC'),
                            'State': 'TX',
                            'City': city,
                            'Address': address,
                            'Phone': phone,
                            'Email': '',
                            'Website': '',
                            'License Number': rec.get('license_number', ''),
                            'License Issue Date': '',
                            'Source': 'Texas TDLR'
                        })
            time.sleep(1)
        except Exception as e:
            print(f"  TDLR {lic_type} error: {e}")
    
    # Texas SOS new entity search via name keywords
    print("\n[TEXAS] Querying Texas SOS for new construction entities...")
    TX_KEYWORDS = ['drywall', 'painting', 'flooring', 'plastering', 'stucco', 'tile contractor', 'floor covering', 'wallboard', 'paint contractor']
    
    for kw in TX_KEYWORDS:
        try:
            # Texas SOS public search
            url = "https://mycpa.cpa.state.tx.us/coa/coaSearchBtn"
            params = {
                'entry': kw,
                'searchType': 'NAME',
                'searchMethod': 'BEGINS',
                'activeFlag': 'A'
            }
            r = session2.get(url, params=params, timeout=15)
            if r.status_code == 200 and len(r.text) > 500:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, 'html.parser')
                rows = soup.find_all('tr', class_=re.compile(r'odd|even|row|result', re.I))
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        name = cols[0].get_text(strip=True)
                        if name and any(k in name.lower() for k in ['drywall','paint','floor','tile','plaster']):
                            tx_results.append({
                                'Company Name': name,
                                'Contact Name': '',
                                'Trade': kw.title(),
                                'State': 'TX',
                                'City': cols[2].get_text(strip=True) if len(cols) > 2 else '',
                                'Address': '',
                                'Phone': '',
                                'Email': '',
                                'Website': '',
                                'License Number': '',
                                'License Issue Date': cols[1].get_text(strip=True) if len(cols) > 1 else '',
                                'Source': 'Texas SOS'
                            })
            time.sleep(0.5)
        except Exception as e:
            pass
    
    print(f"  Total Texas results: {len(tx_results)}")
    all_results.extend(tx_results)

except Exception as e:
    print(f"  Texas error: {e}")

# ─────────────────────────────────────────────
# DEDUPLICATE & SAVE
# ─────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Total raw results: {len(all_results)}")

if all_results:
    df = pd.DataFrame(all_results)
    
    # Normalize phone for dedup
    df['phone_norm'] = df['Phone'].astype(str).str.replace(r'\D','',regex=True)
    df = df[df['phone_norm'].str.len() >= 7]
    
    # Dedup by phone
    df = df.drop_duplicates(subset=['phone_norm'], keep='first')
    df = df.drop(columns=['phone_norm'])
    
    print(f"After dedup: {len(df)} records")
    print(f"\nBreakdown by state:")
    print(df['State'].value_counts().to_string())
    print(f"\nBreakdown by source:")
    print(df['Source'].value_counts().to_string())
    
    # Save
    outfile = f"/app/new_companies_{TODAY}.csv"
    df.to_csv(outfile, index=False)
    print(f"\nSaved to: {outfile}")
else:
    print("No results — APIs may need browser automation. See output above for details.")

