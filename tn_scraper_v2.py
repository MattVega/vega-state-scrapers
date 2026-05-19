"""Tennessee TDCI full contractor scraper - with frequent token refresh"""
import requests, json, time, csv, os

TOKEN_B64 = "NzY0MDk0YTktNmNmMi00ZTY4LTgxMTItMjdjNDk1MWI3NmM0OjYwMjgwYjQxLTFjNjgtNDBjZi05MWM0LWY0ODEyYTdkNmUyMQ=="
AUTH_URL = "https://access.cloud.commerce.tn.gov/entellitrak/auth/oauth/token?grant_type=client_credentials"
API_BASE = "https://access.cloud.commerce.tn.gov/entellitrak/api/endpoints/v1"
OUT_FILE = "/app/tn_contractors.csv"

def get_token():
    r = requests.post(AUTH_URL, 
        headers={"Authorization": f"Basic {TOKEN_B64}", "Content-Type": "application/x-www-form-urlencoded"}, 
        timeout=15)
    if r.status_code == 200:
        return r.json()['access_token']
    print(f"Token error: {r.status_code} {r.text[:100]}")
    return None

def get_headers():
    tok = get_token()
    return {"Authorization": f"Bearer {tok}", "Accept": "application/json", "Content-Type": "application/json"}

def parse_record(rec):
    name = rec.get('title', '')
    entity_type = rec.get('subtitle', '')
    license_type = license_num = status = expiry = address = ''
    
    for detail in rec.get('details', []):
        label = detail.get('label', '')
        vals = [v for v in detail.get('values', []) if v is not None]
        
        if label == 'License Details' and vals:
            license_type = vals[0] if len(vals) > 0 else ''
            license_num = vals[2] if len(vals) > 2 else ''
            status = vals[3] if len(vals) > 3 else ''
            expiry = vals[4] if len(vals) > 4 else ''
        elif label == 'Primary Contact Information':
            for v in vals:
                v = str(v).strip()
                if ',' in v and len(v) > 5 and 'United States' not in v and 'County' not in v:
                    address = v
                    break
    
    city = state = zip_code = ''
    if address:
        parts = address.split(',')
        city = parts[0].strip()
        if len(parts) > 1:
            sp = parts[1].strip().split()
            state = sp[0] if sp else ''
            zip_code = sp[1] if len(sp) > 1 else ''
    
    return {
        'company_name': name, 'entity_type': entity_type,
        'license_type': license_type, 'license_num': license_num,
        'status': status, 'expiry': expiry,
        'city': city, 'state': state, 'zip': zip_code,
        'full_address': address, 'phone': '', 'email': '',
        'source_state': 'TN', 'trade': '',
    }

CONTRACTOR_KEYWORDS = ['contractor', 'plumb', 'electr', 'home improvement', 'hvac', 
    'heat', 'cool', 'air condition', 'roof', 'mason', 'drywall', 'floor', 'paint', 
    'cabinet', 'tile', 'stucco', 'framing', 'siding', 'insulat', 'window', 'door', 
    'landscape', 'concrete', 'excavat', 'well', 'septic', 'alarm', 'fire', 'sprinkler']

BATCH_SIZE = 200
MAX_START = 9800

print("Starting TN TDCI contractor pull...")
all_ids = set()
total = 0

# Refresh token every letter (short TTL on this API)
letters = list('abcdefghijklmnopqrstuvwxyz0123456789')

with open(OUT_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['company_name','entity_type','license_type','license_num','status','expiry','city','state','zip','full_address','phone','email','source_state','trade'])
    writer.writeheader()
    
    for letter in letters:
        hdrs = get_headers()  # Fresh token per letter
        if not hdrs:
            print(f"  Could not get token for letter '{letter}', skipping")
            time.sleep(3)
            continue
        
        letter_count = 0
        start = 0
        
        while start <= MAX_START:
            payload = {
                "lookupString": letter,
                "rows": BATCH_SIZE, "start": start,
                "type": "credential", "highlight": "true",
                "appliedFilters": None, "formRequest": None
            }
            
            try:
                r = requests.post(f"{API_BASE}/portal/search", headers=hdrs, json=payload, timeout=30)
                
                if r.status_code == 401:
                    hdrs = get_headers()  # Refresh mid-letter
                    time.sleep(1)
                    continue
                    
                if r.status_code != 200:
                    print(f"  Letter '{letter}' start={start}: HTTP {r.status_code}")
                    break
                
                results = r.json().get('results', [])
                if not results:
                    break
                
                for rec in results:
                    rec_id = rec.get('id', '')
                    if rec_id and rec_id not in all_ids:
                        parsed = parse_record(rec)
                        lt = parsed['license_type'].lower()
                        if any(kw in lt for kw in CONTRACTOR_KEYWORDS):
                            all_ids.add(rec_id)
                            writer.writerow(parsed)
                            letter_count += 1
                            total += 1
                
                if len(results) < BATCH_SIZE:
                    break
                    
                start += BATCH_SIZE
                time.sleep(0.3)
                
            except Exception as e:
                print(f"  Error at letter='{letter}' start={start}: {e}")
                time.sleep(2)
                break
        
        print(f"Letter '{letter}': {letter_count} new records | Running total: {total}")

print(f"\nFINISHED - Total TN contractor records: {total}")
print(f"Saved to: {OUT_FILE}")
