#!/usr/bin/env python3
"""
Nevada State Contractors Board - Full License Directory Scraper
Pulls all active contractor records from the public contractor listing.
Returns: company_name, address, city, state, zip, phone, license_num, classification, expires, status
"""
import requests
from bs4 import BeautifulSoup
import csv, re, sys
from datetime import datetime

LOG = "/app/nv_scraper.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + "\n")

log("=== NV Contractor Scraper Started ===")

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

log("Fetching form...")
r = s.get('https://app.nvcontractorsboard.com/Clients/nvscb/Public/ContractorListing/ListingSearch.aspx', timeout=30)
soup = BeautifulSoup(r.text, 'html.parser')
vs = soup.find('input', {'name': '__VIEWSTATE'})
ev = soup.find('input', {'name': '__EVENTVALIDATION'})
vsg = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})

payload = {
    '__VIEWSTATE': vs['value'] if vs else '',
    '__EVENTVALIDATION': ev['value'] if ev else '',
    '__VIEWSTATEGENERATOR': vsg['value'] if vsg else '',
    'ctl00$ContentPlaceHolder1$County': '',
    'ctl00$ContentPlaceHolder1$App': '',
    'ctl00$ContentPlaceHolder1$btnSearch': 'Search'
}

log("Downloading full contractor directory (this may take a minute)...")
r2 = s.post('https://app.nvcontractorsboard.com/Clients/nvscb/Public/ContractorListing/ListingSearch.aspx',
            data=payload, timeout=120)
log(f"Downloaded {round(len(r2.content)/1024/1024, 1)} MB")

log("Parsing HTML...")
soup2 = BeautifulSoup(r2.text, 'html.parser')

# Find the content area
content = soup2.find('div', {'id': 'ContentPlaceHolder1_UpdatePanel1'}) or \
          soup2.find('div', class_=re.compile(r'contractor|listing|result', re.I)) or \
          soup2.find('form')

# Each contractor block is a div or section
# The page is HTML-formatted text blocks - parse by structure
records = []

# Find all contractor entries - they appear as named divs or repeating patterns
# Let's look at the raw text structure
raw_text = soup2.get_text(separator='\n')

# Split on contractor name patterns - each entry starts with company name
# Then address line, city state zip, license #, phone, classifications
# Strategy: find the container holding all results, then split by license # markers

# Find all license number occurrences to count records
license_nums = re.findall(r'License\s*#:\s*(\d{7})', r2.text)
log(f"Found {len(license_nums)} license records")

# Parse using regex on the full text
# Pattern: company block separated by "Active" or "Inactive" status
blocks = re.split(r'\n(?=[A-Z0-9#].*\n.*NV\s+\d{5})', raw_text)
log(f"Initial block count: {len(blocks)}")

# Better approach: use BeautifulSoup to find repeating elements
# Look for the pattern in the HTML structure
all_text = r2.text

# Find all contractor entries using regex on HTML
# Each entry has a license number
pattern = re.compile(
    r'(?P<name>[A-Z0-9&\'\-\.\s,/]+?)\s*'
    r'(?P<addr>\d+[^<\n]+?)\s*'
    r'(?P<city>[A-Z\s]+)\s+(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)\s*'
    r'License\s*#:\s*(?P<license>\d+)\s*'
    r'(?:\((?P<phone_area>\d{3})\)\s*(?P<phone_rest>[\d\-]+))?\s*'
    r'Classifications:\s*(?P<class>[^\n]+)',
    re.MULTILINE | re.DOTALL
)

# Actually let's parse the soup structure more carefully
# Find all divs or spans that contain contractor info
log("Parsing contractor entries from HTML structure...")

# The page uses a repeating structure - let's find it
# Look for all elements containing 'License #:'
html = r2.text

# Split the HTML at each contractor entry boundary
# Each entry appears to start with the company name in an h3, div, or span
entries_html = re.split(r'(?=<(?:h[1-6]|div|span)[^>]*>\s*(?:[A-Z0-9][A-Z0-9&\'\-\.\s,/]{2,})\s*</)', html)
log(f"HTML splits: {len(entries_html)}")

# Parse with line-by-line approach on clean text
lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
records = []
i = 0
current = {}

# State machine parser
STATE_NONE = 0
STATE_NAME = 1
STATE_ADDR = 2

# Find where results start
start_idx = 0
for idx, line in enumerate(lines):
    if 'Active Directory of Licensed Contractors' in line:
        start_idx = idx + 5
        break

log(f"Results start at line {start_idx}, total lines: {len(lines)}")

# Parse line by line
i = start_idx
while i < len(lines):
    line = lines[i]
    
    # Skip header/footer junk
    if not line or len(line) < 2:
        i += 1
        continue
    
    # Check if this looks like a company name (all caps, no special patterns)
    # Company names are ALL CAPS lines that aren't address/classification lines
    is_license = line.startswith('License #:')
    is_class = line.startswith('Classifications:') or line.startswith('Classification')
    is_expires = line.startswith('Expires:')
    is_monetary = line.startswith('Monetary Limit:')
    is_status = line in ('Active', 'Inactive', 'Suspended')
    is_phone = bool(re.match(r'^\(?\d{3}[\)\s\-\.]\s*\d{3}[\s\-\.]\d{4}', line))
    is_address = bool(re.match(r'^\d+\s+[A-Z]', line)) or bool(re.match(r'^[A-Z\s]+,?\s+[A-Z]{2}\s+\d{5}', line))
    
    # If we hit a license line, we're in a contractor entry
    if is_license:
        license_num = line.replace('License #:', '').strip()
        if current.get('name'):
            current['license_num'] = license_num
    elif is_class:
        classification = line.replace('Classifications:', '').replace('Classification:', '').strip()
        # Next line might be the actual classification
        if i+1 < len(lines) and not lines[i+1].startswith('Expires:') and not lines[i+1].startswith('LIMITED'):
            classification = lines[i+1].strip()
            i += 1
        if current.get('name'):
            current.setdefault('classifications', []).append(classification)
    elif is_expires:
        if current.get('name'):
            exp = line.replace('Expires:', '').strip()
            # Parse date
            try:
                dt = datetime.fromisoformat(exp.replace('T00:00:00', ''))
                current['expires'] = dt.strftime('%Y-%m-%d')
            except:
                current['expires'] = exp
    elif is_monetary:
        if current.get('name'):
            current['monetary_limit'] = line.replace('Monetary Limit:', '').strip()
    elif is_status:
        if current.get('name'):
            current['status'] = line
            # Save this record
            records.append({
                'company_name': current.get('name', ''),
                'address': current.get('address', ''),
                'city': current.get('city', ''),
                'state': 'NV',
                'zip': current.get('zip', ''),
                'phone': current.get('phone', ''),
                'license_num': current.get('license_num', ''),
                'trade': '; '.join(current.get('classifications', [])),
                'expires': current.get('expires', ''),
                'monetary_limit': current.get('monetary_limit', ''),
                'status': line,
                'source': 'NV State Contractors Board'
            })
            current = {}
    elif is_phone:
        if current.get('name'):
            current['phone'] = line
    elif is_address:
        if current.get('name'):
            # Try to parse city/state/zip
            m = re.search(r'^(.+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', line)
            if m:
                current['city'] = m.group(1).strip().rstrip(',')
                current['zip'] = m.group(3)
            else:
                current.setdefault('address', line)
    elif re.match(r'^[A-Z0-9][A-Z0-9&\'\-\.\s,/\(\)]{2,}$', line) and not is_license and not is_class:
        # Likely a company name - all caps
        if not current.get('name'):
            current = {'name': line}
        elif not current.get('address') and re.match(r'^\d+', line):
            current['address'] = line
    
    i += 1

log(f"Parsed {len(records)} contractor records")

# Deduplicate by phone
seen_phones = set()
deduped = []
no_phone = []
for r in records:
    phone = re.sub(r'\D', '', r.get('phone', ''))
    if not phone:
        no_phone.append(r)
        deduped.append(r)
    elif phone not in seen_phones:
        seen_phones.add(phone)
        deduped.append(r)

log(f"After dedup: {len(deduped)} records ({len(no_phone)} without phone)")

# Save
out_file = '/app/nv_contractors_raw.csv'
fieldnames = ['company_name', 'address', 'city', 'state', 'zip', 'phone', 
              'license_num', 'trade', 'expires', 'monetary_limit', 'status', 'source']
with open(out_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(deduped)

log(f"Saved {len(deduped)} records to {out_file}")
log("=== Done ===")
