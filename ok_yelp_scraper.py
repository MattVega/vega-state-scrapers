"""
Oklahoma contractor scraper using Yelp API
Targets all major trades in OK cities
"""
import os, csv, json, re, time, urllib.request, urllib.parse, urllib.error

YELP_API_KEY = os.environ.get('YELP_API_KEY', '')
OUTPUT_CSV = '/app/ok_yelp_raw.csv'
MASTER_CSV = '/app/master_subcontractors_v2.csv'

def norm_phone(p):
    if not p: return ''
    return re.sub(r'\D','',str(p))[-10:]
def norm_company(c):
    if not c: return ''
    return re.sub(r'[^a-z0-9]','',c.strip().lower())

# Load existing master to dedup
existing_phones, existing_companies = set(), set()
if os.path.exists(MASTER_CSV):
    with open(MASTER_CSV, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            ph = norm_phone(row.get('Phone',''))
            co = norm_company(row.get('Company Name',''))
            if ph: existing_phones.add(ph)
            if co: existing_companies.add(co)
    print(f"Master loaded: {len(existing_phones):,} phones, {len(existing_companies):,} companies")

TRADES = [
    ('drywall contractor','Drywall'),
    ('painting contractor','Painting'),
    ('flooring contractor','Flooring'),
    ('roofing contractor','Roofing'),
    ('plumbing contractor','Plumbing'),
    ('electrical contractor','Electrical'),
    ('hvac contractor','HVAC'),
    ('framing contractor','Framing'),
    ('concrete contractor','Concrete'),
    ('general contractor','General'),
    ('insulation contractor','Insulation'),
    ('masonry contractor','Masonry'),
    ('tile contractor','Tile'),
    ('landscaping contractor','Landscaping'),
    ('demolition contractor','Demolition'),
]

# Oklahoma cities to pull from
OK_CITIES = [
    'Oklahoma City, OK', 'Tulsa, OK', 'Norman, OK', 'Broken Arrow, OK',
    'Lawton, OK', 'Edmond, OK', 'Moore, OK', 'Midwest City, OK',
    'Enid, OK', 'Stillwater, OK', 'Muskogee, OK', 'Bartlesville, OK',
    'Owasso, OK', 'Shawnee, OK', 'Ponca City, OK', 'Ardmore, OK',
    'Duncan, OK', 'Durant, OK', 'Tahlequah, OK', 'Yukon, OK',
    'Bixby, OK', 'Jenks, OK', 'Sand Springs, OK', 'Claremore, OK',
    'Sapulpa, OK', 'McAlester, OK', 'Altus, OK', 'Chickasha, OK',
]

new_contacts = []
seen_in_batch = set()
api_calls = 0

for city in OK_CITIES:
    for trade_term, trade_label in TRADES:
        for offset in [0, 50]:  # 2 pages = 100 per combo
            url = (f"https://api.yelp.com/v3/businesses/search"
                   f"?term={urllib.parse.quote(trade_term)}"
                   f"&location={urllib.parse.quote(city)}"
                   f"&limit=50&offset={offset}")
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {YELP_API_KEY}'})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"  Rate limit hit at {api_calls} calls")
                    time.sleep(2)
                    continue
                continue
            except Exception as e:
                continue
            api_calls += 1
            
            businesses = data.get('businesses', [])
            for biz in businesses:
                name = biz.get('name','').strip()
                if not name: continue
                
                phone = biz.get('phone','').strip().replace('+1','')
                phone_norm = norm_phone(phone)
                company_norm = norm_company(name)
                
                # Dedup
                if phone_norm and phone_norm in existing_phones: continue
                if phone_norm and phone_norm in seen_in_batch: continue
                if company_norm and company_norm in existing_companies: continue
                
                loc = biz.get('location', {})
                address = ' '.join(filter(None, [
                    loc.get('address1',''),
                    loc.get('address2',''),
                ]))
                city_val = loc.get('city','')
                state_val = loc.get('state','OK')
                
                if state_val != 'OK': continue  # only OK results
                
                if phone_norm: seen_in_batch.add(phone_norm)
                if company_norm: existing_companies.add(company_norm)
                
                new_contacts.append({
                    'Company Name': name,
                    'Contact Name': '',
                    'Trade': trade_label,
                    'State': 'OK',
                    'City': city_val,
                    'Address': address,
                    'Phone': phone_norm,
                    'Email': '',
                    'Website': '',
                    'Notes': f"Source: Yelp | City searched: {city}",
                })
            
            if len(businesses) < 50: break  # no more pages
            time.sleep(0.2)
        
        if api_calls % 50 == 0 and api_calls > 0:
            print(f"  {api_calls} API calls, {len(new_contacts):,} new contacts so far...", flush=True)

print(f"\nDone! {api_calls} API calls, {len(new_contacts):,} new unique OK contacts")

# Save
with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['Company Name','Contact Name','Trade','State','City','Address','Phone','Email','Website','Notes'])
    writer.writeheader()
    writer.writerows(new_contacts)

print(f"Saved to {OUTPUT_CSV}")
