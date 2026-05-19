import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import os

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# First POST to initialize session with NE filter
print("Initializing session...")
r0 = s.post('https://dol.nebraska.gov/conreg/Search/AdvancedSearch', data={
    'Page': 1, 'ResultsPerPage': 25, 'TotalPages': 0,
    'AdvancedSearch.DBAName': '', 'AdvancedSearch.ContractorCorpName': '',
    'AdvancedSearch.City': '', 'AdvancedSearch.ZipCode': '',
    'AdvancedSearch.PhoneNumber': '', 'AdvancedSearch.RegistrationNumber': '',
    'AdvancedSearch.State': 'NE', 'AdvancedSearch.County': '', 'AdvancedSearch.NAICSCode': '',
}, timeout=30)
print(f"Session initialized: {r0.status_code}")

# Now paginate all 157 pages with 100 results each
all_contacts = []
detail_ids = []

for page in range(1, 158):
    url = f'https://dol.nebraska.gov/conreg/Search/AdvancedSearch?page={page}&resultsPerPage=100'
    try:
        r = s.get(url, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table')
        if not table:
            print(f"  Page {page}: No table found")
            break
        rows = table.find_all('tr')[1:]  # skip header
        if not rows:
            print(f"  Page {page}: No rows")
            break
        
        page_contacts = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            
            # Cell 0 has: Name + Address
            name_addr = cells[0].get_text(separator='\n', strip=True)
            lines = [l.strip() for l in name_addr.split('\n') if l.strip()]
            
            company = lines[0] if lines else ''
            address = lines[1] if len(lines) > 1 else ''
            city_state_zip = lines[2] if len(lines) > 2 else ''
            
            # Parse city, state, zip
            city = state = zipcode = ''
            if city_state_zip:
                m = re.match(r'^(.+),\s*(\w{2})\s*(\d{5}(?:-\d{4})?)?$', city_state_zip)
                if m:
                    city = m.group(1).strip()
                    state = m.group(2).strip()
                    zipcode = m.group(3).strip() if m.group(3) else ''
                else:
                    city = city_state_zip
            
            # Get detail link
            detail_link = row.find('a', string='View Details')
            detail_id = ''
            if detail_link:
                href = detail_link.get('href', '')
                detail_id = href.split('/')[-1]
            
            expiry = cells[2].get_text(strip=True) if len(cells) > 2 else ''
            
            page_contacts.append({
                'Company Name': company,
                'Address': address,
                'City': city,
                'State': state if state else 'NE',
                'Zip': zipcode,
                'Expiry': expiry,
                'Detail ID': detail_id,
            })
        
        all_contacts.extend(page_contacts)
        if page % 25 == 0 or page <= 5:
            print(f"  Page {page}: {len(page_contacts)} contacts (total: {len(all_contacts):,})")
        
        time.sleep(0.3)
        
    except Exception as e:
        print(f"  Page {page} ERROR: {e}")
        time.sleep(2)

print(f"\nTotal contacts from list pages: {len(all_contacts):,}")

# Save raw
with open('/app/ne_contractors_raw.csv', 'w', newline='', encoding='utf-8') as f:
    fields = ['Company Name', 'Address', 'City', 'State', 'Zip', 'Expiry', 'Detail ID']
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(all_contacts)
print("Saved to ne_contractors_raw.csv")
