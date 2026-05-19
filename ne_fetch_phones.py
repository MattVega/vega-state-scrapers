import requests
from bs4 import BeautifulSoup
import csv, re, time, json

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

with open('/app/ne_contractors_raw.csv', newline='', encoding='utf-8') as f:
    records = list(csv.DictReader(f))

print(f"Fetching phones for {len(records):,} records...", flush=True)

phones = {}
errors = 0

for i, rec in enumerate(records):
    detail_id = rec.get('Detail ID', '')
    if not detail_id:
        continue
    try:
        url = f'https://dol.nebraska.gov/conreg/Contractor/Details/{detail_id}'
        r = s.get(url, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text(separator='\n')
        m = re.search(r'Telephone\s*\n\s*(\d[\d\s\-\(\)\.]{7,14})', text)
        if m:
            raw = m.group(1).strip()
            digits = re.sub(r'\D','',raw)
            if len(digits) == 10:
                phones[detail_id] = digits
            elif len(digits) == 11 and digits.startswith('1'):
                phones[detail_id] = digits[1:]
            else:
                phones[detail_id] = raw
        else:
            phones[detail_id] = ''
        if (i+1) % 1000 == 0:
            filled = len([v for v in phones.values() if v])
            print(f"  {i+1:,}/{len(records):,} done - {filled:,} phones found", flush=True)
            with open('/app/ne_phones.json','w') as f2:
                json.dump(phones, f2)
        time.sleep(0.08)
    except Exception as e:
        errors += 1
        phones[detail_id] = ''
        time.sleep(0.3)

filled = len([v for v in phones.values() if v])
print(f"\nDone! {filled:,}/{len(records):,} phones. Errors: {errors}", flush=True)
with open('/app/ne_phones.json','w') as f2:
    json.dump(phones, f2)
print("Saved ne_phones.json", flush=True)
