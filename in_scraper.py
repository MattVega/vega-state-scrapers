"""
Indiana PLA license scraper - fixed pagination
Posts to SearchResults.aspx for page navigation
"""
import requests, re, time, csv
from bs4 import BeautifulSoup

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
BASE = "https://mylicense.in.gov/everification/"
RESULTS_URL = "https://mylicense.in.gov/everification/SearchResults.aspx"
DETAILS_PAT = re.compile(r'Details\.aspx')
JS_PAT = re.compile(r'javascript')

BOARDS = [
    'Plumbing Commission',
    'Manufactured Home Installers',
    'Home Inspectors Board',
]
LICENSE_TYPES = [
    'Registered Home Builder',
    'Registered Home Remodeler',
    'Asbestos Contractor',
    'Lead Contractor',
]

def get_form_fields(soup):
    fields = {}
    for inp in soup.find_all('input'):
        name = inp.get('name', '')
        val = inp.get('value', '')
        if name:
            fields[name] = val
    return fields

def parse_grid(soup):
    contacts = []
    detail_links = soup.find_all('a', href=DETAILS_PAT)
    for a in detail_links:
        name = a.get_text(strip=True)
        # Walk up to find the outer TR with columns
        parent = a.find_parent('td')
        outer_tr = parent
        row_data = []
        for _ in range(6):
            if outer_tr:
                outer_tr = outer_tr.find_parent('tr')
                if outer_tr:
                    tds = outer_tr.find_all('td', recursive=False)
                    if len(tds) >= 6:
                        row_data = [td.get_text(strip=True) for td in tds]
                        break
        
        lic_no = row_data[2] if len(row_data) > 2 else ''
        profession = row_data[3] if len(row_data) > 3 else ''
        lic_type = row_data[4] if len(row_data) > 4 else ''
        status = row_data[5] if len(row_data) > 5 else 'Active'
        city_state_zip = row_data[6] if len(row_data) > 6 else ''
        
        city, state_val, zipcode = '', 'IN', ''
        m = re.match(r'^(.*?)\s+([A-Z]{2})\s+(\d{5})', city_state_zip)
        if m:
            city, state_val, zipcode = m.group(1).strip(), m.group(2), m.group(3)
        
        contacts.append({
            'Company Name': '', 'Contact Name': name,
            'Trade': lic_type or profession, 'State': state_val,
            'City': city, 'Zip': zipcode, 'Address': '',
            'Phone': '', 'Email': '', 'Website': '',
            'Notes': f"IN PLA | Lic: {lic_no} | {status}",
        })
    return contacts

def collect_all_pages(soup, search_url):
    all_contacts = []
    page = 1
    current_url = search_url
    
    while True:
        contacts = parse_grid(soup)
        all_contacts.extend(contacts)
        print(f"  Page {page}: {len(contacts)} records (total: {len(all_contacts)})")
        
        if len(contacts) == 0 and page > 1:
            break
        
        form = get_form_fields(soup)
        
        # Find next page link
        next_target = None
        for l in soup.find_all('a', href=JS_PAT):
            if l.get_text(strip=True) == str(page + 1):
                m = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", l['href'])
                if m:
                    next_target = (m.group(1), m.group(2))
                break
        
        if not next_target:
            # Check for "..." next block
            ellipsis_links = [l for l in soup.find_all('a', href=JS_PAT) if l.get_text(strip=True) == '...']
            if ellipsis_links:
                m = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", ellipsis_links[-1]['href'])
                if m:
                    next_target = (m.group(1), m.group(2))
        
        if not next_target:
            print(f"  No next page - done at page {page}")
            break
        
        form['__EVENTTARGET'] = next_target[0]
        form['__EVENTARGUMENT'] = next_target[1]
        form.pop('sch_button', None)
        
        r_next = s.post(current_url, data=form, timeout=30,
                        headers={'Referer': current_url})
        soup = BeautifulSoup(r_next.text, 'html.parser')
        page += 1
        time.sleep(0.3)
    
    return all_contacts

all_contacts = []
seen = set()

for board in BOARDS:
    print(f"\n=== Board: {board} ===")
    r = s.get(BASE, timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')
    form = get_form_fields(soup)
    
    r2 = s.post(BASE, data={**form,
        't_web_lookup__profession_name': board,
        't_web_lookup__license_status_name': 'Active',
        'sch_button': 'Search',
    }, timeout=30)
    soup2 = BeautifulSoup(r2.text, 'html.parser')
    contacts = collect_all_pages(soup2, r2.url)
    
    for c in contacts:
        key = (c['Contact Name'].lower(), c.get('Zip',''))
        if key not in seen:
            seen.add(key)
            all_contacts.append(c)
    print(f"  Board subtotal: {len(contacts)}")
    time.sleep(1)

for lt in LICENSE_TYPES:
    print(f"\n=== License Type: {lt} ===")
    r = s.get(BASE, timeout=15)
    soup = BeautifulSoup(r.text, 'html.parser')
    form = get_form_fields(soup)
    
    r2 = s.post(BASE, data={**form,
        't_web_lookup__license_type_name': lt,
        't_web_lookup__license_status_name': 'Active',
        'sch_button': 'Search',
    }, timeout=30)
    soup2 = BeautifulSoup(r2.text, 'html.parser')
    contacts = collect_all_pages(soup2, r2.url)
    
    for c in contacts:
        key = (c['Contact Name'].lower(), c.get('Zip',''))
        if key not in seen:
            seen.add(key)
            all_contacts.append(c)
    print(f"  Type subtotal: {len(contacts)}")
    time.sleep(1)

print(f"\nGRAND TOTAL: {len(all_contacts)}")
if all_contacts:
    out = '/app/in_new_contacts.csv'
    fieldnames = ['Company Name','Contact Name','Trade','State','City','Zip','Address','Phone','Email','Website','Notes']
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        w.writerows(all_contacts)
    print(f"Saved: {out}")
