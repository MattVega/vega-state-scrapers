#!/usr/bin/env python3
"""
Expertise.com contractor scraper
Pulls all construction trade contacts across all US cities (excl. TX, FL)
Sources from sitemap - 6000+ city/trade pages
"""

import requests
from bs4 import BeautifulSoup
import re, json, time, csv, os, random
from collections import defaultdict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

EXCLUDED_STATES = {'texas', 'florida'}

# Trade slugs and labels
KEY_TRADES = {
    'drywall-contractors': 'Drywall',
    'painting': 'Paint',
    'flooring': 'Flooring',
    'roofing': 'Roofing',
    'plumbing': 'Plumbing',
    'electricians': 'Electrical',
    'hvac': 'HVAC',
    'concrete-contractors': 'Concrete',
    'fence-companies': 'Fencing',
    'landscaping': 'Landscaping',
    'siding-contractors': 'Siding',
    'insulation': 'Insulation',
    'remodeling': 'Remodeling',
    'deck-contractors': 'Decking',
    'handyman': 'Handyman',
    'window-replacement-and-installation': 'Windows',
    'hardwood-floor-refinishing': 'Hardwood Floors',
    'garage-doors': 'Garage Doors',
    'mold-remediation': 'Mold Remediation',
    'tree-services': 'Tree Services',
    'water-damage': 'Water Damage',
    'fire-damage-restoration': 'Fire Damage',
    'demolition-contractors': 'Demolition',
}

def load_sitemap_urls():
    """Load and filter URLs from sitemap"""
    with open('/tmp/expertise_all_urls.txt') as f:
        all_urls = [u.strip() for u in f.readlines() if u.strip()]
    
    trade_urls = defaultdict(list)
    for u in all_urls:
        m = re.match(r'https://www\.expertise\.com/home-improvement/([^/]+)/([^/]+)/([^/]+)$', u)
        if m:
            trade, state, city = m.groups()
            if trade in KEY_TRADES and state not in EXCLUDED_STATES:
                trade_urls[trade].append((u, state, city))
    
    return trade_urls

def parse_page(url, trade_label, state, city):
    """Extract businesses from an expertise.com city page"""
    businesses = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return businesses
        
        soup = BeautifulSoup(r.text, 'lxml')
        scripts = soup.find_all('script', type='application/ld+json')
        
        for s in scripts:
            if not s.string:
                continue
            try:
                data = json.loads(s.string.replace("&apos;", "'").replace("&amp;", "&"))
                btype = str(data.get('@type', ''))
                if 'Business' in btype or btype in ['LocalBusiness', 'GeneralContractor', 'HomeAndConstructionBusiness', 'Organization']:
                    phone = data.get('telephone', '')
                    name = data.get('name', '')
                    if not name or not phone:
                        continue
                    
                    # Clean phone
                    phone = re.sub(r'^1-', '', phone.strip())
                    
                    addr = data.get('address', {})
                    if isinstance(addr, dict):
                        street = addr.get('streetAddress', '')
                        biz_city = addr.get('addressLocality', city.replace('-', ' ').title())
                        biz_state = addr.get('addressRegion', state.upper()[:2])
                    else:
                        street = ''
                        biz_city = city.replace('-', ' ').title()
                        biz_state = state.upper()[:2]
                    
                    businesses.append({
                        'Company Name': name,
                        'Contact Name': '',
                        'Trade': trade_label,
                        'State': biz_state,
                        'City': biz_city,
                        'Address': street,
                        'Phone': phone,
                        'Email': '',
                        'Website': data.get('url', ''),
                        'Source': 'Expertise.com'
                    })
            except:
                pass
    except Exception as e:
        pass
    
    return businesses

def load_existing_phones():
    """Load existing phone numbers for dedup"""
    phones = set()
    existing_files = [
        '/app/master_subcontractors_v2.csv',
        '/app/dialer_ready_contacts.csv',
    ]
    for fpath in existing_files:
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        p = re.sub(r'\D', '', row.get('Phone', ''))
                        if p: phones.add(p)
                print(f"Loaded {len(phones)} phones from {fpath}")
            except:
                pass
    return phones

# ---- MAIN ----
print("Loading sitemap URLs...")
trade_urls = load_sitemap_urls()
total_pages = sum(len(v) for v in trade_urls.values())
print(f"Trades: {len(trade_urls)}, Total city pages: {total_pages}")

print("Loading existing contacts for dedup...")
seen_phones = load_existing_phones()
print(f"Existing phones to skip: {len(seen_phones)}")

output_file = '/app/expertise_contacts.csv'
fieldnames = ['Company Name','Contact Name','Trade','State','City','Address','Phone','Email','Website','Source']

results_total = 0
pages_done = 0

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    
    for trade_slug, pages in trade_urls.items():
        trade_label = KEY_TRADES[trade_slug]
        trade_count = 0
        
        for url, state, city in pages:
            businesses = parse_page(url, trade_label, state, city)
            
            for biz in businesses:
                phone_digits = re.sub(r'\D', '', biz.get('Phone', ''))
                if not phone_digits or phone_digits in seen_phones:
                    continue
                seen_phones.add(phone_digits)
                writer.writerow(biz)
                trade_count += 1
                results_total += 1
            
            pages_done += 1
            time.sleep(random.uniform(0.4, 0.8))
            
            if pages_done % 50 == 0:
                print(f"Progress: {pages_done}/{total_pages} pages | {results_total} new contacts")
        
        print(f"  {trade_label}: +{trade_count} new contacts")

print(f"\n✅ DONE! Total new contacts: {results_total}")
print(f"Saved to {output_file}")
