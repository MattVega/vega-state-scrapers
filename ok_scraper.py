"""
Oklahoma contractor scraper:
1. CIB system - electrical, plumbing, mechanical licensees (A-Z lastname search)
2. Roofing - CIB roofing registry via alphabetical search
3. General contractors - Yelp API supplement
"""
import requests, csv, json, re, time, string, os
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

OUTPUT_CSV = '/app/ok_contractors_raw.csv'
YELP_API_KEY = os.environ.get('YELP_API_KEY', '')

# Load master to dedup
MASTER_CSV = '/app/master_subcontractors_v2.csv'
def norm_phone(p):
    if not p: return ''
    return re.sub(r'\D','',str(p))[-10:]
def norm_company(c):
    if not c: return ''
    return re.sub(r'[^a-z0-9]','',c.strip().lower())

existing_phones, existing_companies = set(), set()
if os.path.exists(MASTER_CSV):
    with open(MASTER_CSV, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            ph = norm_phone(row.get('Phone',''))
            co = norm_company(row.get('Company Name',''))
            if ph: existing_phones.add(ph)
            if co: existing_companies.add(co)
    print(f"Master loaded: {len(existing_phones):,} phones, {len(existing_companies):,} companies")

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})
CIB_BASE = 'https://okcibv7prod.glsuite.us/GLSuiteWeb/Clients/OKCIB/Public/LicenseeSearch/LicenseeSearch.aspx'

def get_viewstate():
    r = s.get(CIB_BASE, timeout=20)
    soup = BeautifulSoup(r.text, 'html.parser')
    return {
        '__VIEWSTATE': soup.find('input', {'id':'__VIEWSTATE'})['value'],
        '__VIEWSTATEGENERATOR': soup.find('input', {'id':'__VIEWSTATEGENERATOR'})['value'],
        '__EVENTVALIDATION': soup.find('input', {'id':'__EVENTVALIDATION'})['value'],
    }

def search_cib(last_name='', trade=''):
    try:
        vs = get_viewstate()
        r = s.post(CIB_BASE, data={
            **vs, '__EVENTTARGET': '', '__EVENTARGUMENT': '',
            'ObjectTypeID': '5430', 'ObjectID': '40',
            'qFirstName': '', 'qLastName': last_name,
            'qBusinessName': '', 'qLicenseNumber': '', 'Trade': trade,
            'btnSubmit': 'Submit',
        }, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        for t in soup.find_all('table'):
            if 'Licensee Name' in t.get_text():
                rows = t.find_all('tr')[1:]
                results = []
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cells) >= 3 and 'No Results' not in cells[0] and cells[0]:
                        results.append({
                            'name': cells[0],
                            'city': cells[1] if len(cells) > 1 else '',
                            'license_type': cells[2] if len(cells) > 2 else '',
                            'license_number': cells[3] if len(cells) > 3 else '',
                            'status': cells[4] if len(cells) > 4 else '',
                        })
                return results
    except Exception as e:
        print(f"  CIB error ({last_name}): {e}")
    return []

# Scrape CIB: all trades, all lastname prefixes AA*-AZ*, BA*-BZ*, etc.
all_contacts = []
trades = ['Electrical', 'Plumbing', 'Mechanical', 'Building Inspector', 'Home Inspector']

print("=== Scraping CIB electrical/plumbing/mechanical/inspector licensees ===")
cib_found = 0
for trade in trades:
    print(f"\nTrade: {trade}")
    for letter1 in string.ascii_uppercase:
        for letter2 in string.ascii_uppercase:
            prefix = f"{letter1}{letter2}a*"
            results = search_cib(last_name=prefix, trade=trade)
            if results:
                cib_found += len(results)
                print(f"  {prefix} [{trade}]: {len(results)} results")
                for rec in results:
                    # Parse name: could be "LastName FirstName" or "Business Name"
                    name = rec['name']
                    city = rec['city']
                    lic_type = rec['license_type']
                    lic_num = rec['license_number']
                    status = rec['status']
                    if status and 'active' not in status.lower() and 'current' not in status.lower():
                        continue  # skip inactive
                    all_contacts.append({
                        'Company Name': name,
                        'Contact Name': '',
                        'Trade': trade,
                        'State': 'OK',
                        'City': city,
                        'Address': '',
                        'Phone': '',
                        'Email': '',
                        'Website': '',
                        'Notes': f"License: {lic_num} | Type: {lic_type} | Status: {status}"
                    })
            time.sleep(0.3)
        if cib_found > 5000:
            break
    if cib_found > 5000:
        break

print(f"\nCIB total: {cib_found:,} contacts (active licenses)")

# Save progress
with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['Company Name','Contact Name','Trade','State','City','Address','Phone','Email','Website','Notes'])
    writer.writeheader()
    writer.writerows(all_contacts)

print(f"\nSaved {len(all_contacts):,} contacts to {OUTPUT_CSV}")
