"""Indiana PLA bulk download - contractor types"""
import requests, csv, time, re, os, io
from bs4 import BeautifulSoup

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
BASE = "https://secure.in.gov/apps/pla/license/bulk/pla_bulk_ia"

CONTRACTOR_TYPES = [
    'Plumbing Contractor', 'Plumbing Corporation', 'Registered Home Builder',
    'Registered Home Remodeler', 'Journeyman Plumber', 'Asbestos Contractor',
    'Lead Contractor',
]

all_contacts = []
seen_keys = set()

for lt in CONTRACTOR_TYPES:
    print(f"\n=== {lt} ===")
    # Fresh session per type
    r = s.get(BASE)
    soup = BeautifulSoup(r.text, 'html.parser')
    session_val = soup.find('input', {'name': 'SESSION'})['value']
    
    # Agree to terms
    r2 = s.post(BASE, data={
        'SESSION': session_val, 'MODULE': 'conditionsModule', 'SEQUENCE_NUMBER': '0',
        'next_button.x': '10', 'next_button.y': '10',
    })
    soup2 = BeautifulSoup(r2.text, 'html.parser')
    session2 = soup2.find('input', {'name': 'SESSION'})['value']
    
    # Submit license type selection
    r3 = s.post(BASE, data={
        'SESSION': session2,
        'MODULE': 'selectionModule',
        'SEQUENCE_NUMBER': '1',
        'hpbBulkDownloadForm:0.licenseType': lt,
        'hpbBulkDownloadForm:0.counties': 'All',
        'next_button.x': '10',
        'next_button.y': '10',
    })
    print(f"  Selection: {r3.status_code} len={len(r3.text)}")
    soup3 = BeautifulSoup(r3.text, 'html.parser')
    
    # Check what's next
    text_preview = soup3.get_text(strip=True)[:300]
    print(f"  Preview: {text_preview[:200]}")
    
    # Look for download link or next step
    session3 = soup3.find('input', {'name': 'SESSION'})
    if session3:
        session3 = session3['value']
        
        # Try to download
        r4 = s.post(BASE, data={
            'SESSION': session3,
            'MODULE': 'downloadModule',
            'SEQUENCE_NUMBER': '2',
            'next_button.x': '10',
            'next_button.y': '10',
        })
        ct = r4.headers.get('content-type', '')
        cd = r4.headers.get('content-disposition', '')
        print(f"  Download: {r4.status_code} CT={ct[:40]} CD={cd[:40]}")
        
        if 'csv' in ct.lower() or cd or ('text' in ct.lower() and len(r4.text) > 1000 and ',' in r4.text[:200]):
            lines = r4.text.split('\n')
            print(f"  Lines: {len(lines)}")
            print(f"  Header: {lines[0][:100]}")
            if len(lines) > 1: print(f"  Sample: {lines[1][:100]}")
            
            fname = f"/app/in_{lt.replace(' ','_').lower()}.csv"
            with open(fname, 'w') as f:
                f.write(r4.text)
            
            reader = csv.DictReader(io.StringIO(r4.text))
            for row in reader:
                company = row.get('Business Name', row.get('Company', row.get('Organization', ''))).strip()
                fname_val = row.get('First Name', '').strip()
                lname_val = row.get('Last Name', '').strip()
                contact = f"{fname_val} {lname_val}".strip()
                phone = row.get('Phone', row.get('Business Phone', '')).strip()
                city = row.get('City', '').strip()
                state_val = row.get('State', 'IN').strip() or 'IN'
                address = row.get('Address', row.get('Street Address', '')).strip()
                
                key = f"{(company or contact).lower()}|{''.join(c for c in phone if c.isdigit())}"
                if key not in seen_keys and (company or contact):
                    seen_keys.add(key)
                    all_contacts.append({
                        'Company Name': company, 'Contact Name': contact,
                        'Trade': lt, 'State': state_val, 'City': city,
                        'Address': address, 'Phone': phone,
                        'Email': row.get('Email', ''), 'Website': '',
                        'Notes': f"Source: Indiana PLA | License: {row.get('License Number','')} | Status: {row.get('Status','')}"
                    })
        else:
            print(f"  Got HTML: {soup3.get_text(strip=True)[:200]}")
    
    time.sleep(1)

print(f"\nTotal: {len(all_contacts)}")
if all_contacts:
    with open('/app/in_new_contacts.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['Company Name','Contact Name','Trade','State','City','Address','Phone','Email','Website','Notes'])
        w.writeheader()
        w.writerows(all_contacts)
    print("Saved: /app/in_new_contacts.csv")

