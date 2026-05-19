import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import json
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

results = []

def clean(s):
    if not s:
        return ""
    return re.sub(r'\s+', ' ', str(s)).strip()

# =============================================
# SOURCE 1: BuildZoom - contractor search API
# =============================================
print("=== BuildZoom Scraping ===")
TRADES = ["drywall", "painting", "flooring"]
STATES = ["CA","OR","WA","NV","CO","AZ","UT","ID","MT","WY","NM","NE","KS","OK","MN","IA","MO","WI","IL","IN","MI","OH","KY","TN","AL","GA","SC","NC","VA","WV","MD","DE","PA","NJ","NY","CT","RI","MA","VT","NH","ME","ND","SD","AK","HI","AR","LA"]

bz_count = 0
for state in STATES[:12]:  # Do first batch of states
    for trade in TRADES:
        try:
            url = f"https://www.buildzoom.com/contractors?trade={trade}&state={state}&per_page=50"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'lxml')
                # Look for contractor cards
                cards = soup.find_all('div', class_=re.compile(r'contractor|listing|result', re.I))
                for card in cards[:20]:
                    name = clean(card.find(class_=re.compile(r'name|title|company', re.I)))
                    phone_match = re.search(r'\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}', card.get_text())
                    phone = phone_match.group() if phone_match else ""
                    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', card.get_text())
                    email = email_match.group() if email_match else ""
                    if name and len(name) > 3:
                        results.append({
                            "Company Name": name,
                            "Contact Name": "",
                            "Trade": trade.title(),
                            "State": state,
                            "City": "",
                            "Address": "",
                            "Phone": phone,
                            "Email": email,
                            "Website": "",
                            "Source": "BuildZoom"
                        })
                        bz_count += 1
            time.sleep(0.5)
        except Exception as e:
            pass

print(f"BuildZoom batch 1: {bz_count} records")

# =============================================
# SOURCE 2: Houzz Pro directory
# =============================================
print("=== Houzz Directory ===")
houzz_count = 0
houzz_trades = {
    "painting": ["CA", "NY", "WA", "OR", "CO", "GA", "NC", "VA", "OH", "PA"],
    "drywall": ["CA", "NY", "WA", "OR", "CO", "GA", "NC", "VA", "OH", "PA"],
    "flooring": ["CA", "NY", "WA", "OR", "CO", "GA", "NC", "VA", "OH", "PA"]
}

for trade, states_list in houzz_trades.items():
    for state in states_list[:5]:
        try:
            url = f"https://www.houzz.com/professionals/{trade}-contractors/{state.lower()}"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'lxml')
                # Extract JSON-LD structured data
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            for item in data:
                                if item.get('@type') in ['LocalBusiness', 'HomeAndConstructionBusiness', 'GeneralContractor']:
                                    results.append({
                                        "Company Name": clean(item.get('name', '')),
                                        "Contact Name": "",
                                        "Trade": trade.title(),
                                        "State": state,
                                        "City": clean(item.get('address', {}).get('addressLocality', '') if isinstance(item.get('address'), dict) else ''),
                                        "Address": "",
                                        "Phone": clean(item.get('telephone', '')),
                                        "Email": "",
                                        "Website": clean(item.get('url', '')),
                                        "Source": "Houzz"
                                    })
                                    houzz_count += 1
                    except:
                        pass
                # Also look for pro cards
                pro_cards = soup.find_all('div', {'data-component': re.compile(r'pro|professional', re.I)})
                for card in pro_cards[:20]:
                    name = clean(card.find(class_=re.compile(r'name|title', re.I)))
                    if name and len(name) > 3:
                        phone_match = re.search(r'\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}', card.get_text())
                        results.append({
                            "Company Name": name,
                            "Contact Name": "",
                            "Trade": trade.title(),
                            "State": state,
                            "City": "",
                            "Address": "",
                            "Phone": phone_match.group() if phone_match else "",
                            "Email": "",
                            "Website": "",
                            "Source": "Houzz"
                        })
                        houzz_count += 1
            time.sleep(0.7)
        except Exception as e:
            pass

print(f"Houzz: {houzz_count} records")

# =============================================
# SOURCE 3: Angi / HomeAdvisor directory (public pages)
# =============================================
print("=== Angi Directory ===")
angi_count = 0
angi_cats = {
    "drywall": ["new-york-ny", "los-angeles-ca", "chicago-il", "phoenix-az", "philadelphia-pa", "san-antonio-tx", "san-diego-ca", "dallas-tx", "san-jose-ca", "austin-tx"],
    "painting": ["seattle-wa", "denver-co", "nashville-tn", "louisville-ky", "portland-or", "las-vegas-nv", "memphis-tn", "baltimore-md", "boston-ma", "washington-dc"],
    "flooring": ["atlanta-ga", "raleigh-nc", "miami-fl", "minneapolis-mn", "tucson-az", "fresno-ca", "sacramento-ca", "mesa-az", "kansas-city-mo", "virginia-beach-va"]
}
for trade, cities in angi_cats.items():
    for city_slug in cities[:5]:
        try:
            url = f"https://www.angi.com/companylist/{city_slug}/{trade}-contractors.htm"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'lxml')
                # Parse structured data
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if isinstance(item, dict) and 'name' in item:
                                addr = item.get('address', {})
                                state = addr.get('addressRegion', '') if isinstance(addr, dict) else ''
                                city = addr.get('addressLocality', '') if isinstance(addr, dict) else ''
                                results.append({
                                    "Company Name": clean(item.get('name', '')),
                                    "Contact Name": "",
                                    "Trade": trade.title(),
                                    "State": state,
                                    "City": city,
                                    "Address": clean(addr.get('streetAddress', '') if isinstance(addr, dict) else ''),
                                    "Phone": clean(item.get('telephone', '')),
                                    "Email": "",
                                    "Website": clean(item.get('url', '')),
                                    "Source": "Angi"
                                })
                                angi_count += 1
                    except:
                        pass
            time.sleep(0.5)
        except Exception as e:
            pass

print(f"Angi: {angi_count} records")

# =============================================
# SOURCE 4: Contractors.com directory
# =============================================
print("=== Contractors.com ===")
cont_count = 0
for state in STATES[:20]:
    for trade in ["drywall", "paint", "floor"]:
        try:
            url = f"https://www.contractors.com/{trade}/{state.lower()}/"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'lxml')
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else (data.get('@graph', []) if isinstance(data, dict) else [])
                        for item in items:
                            if isinstance(item, dict) and item.get('name') and '@type' in item:
                                addr = item.get('address', {})
                                results.append({
                                    "Company Name": clean(item.get('name', '')),
                                    "Contact Name": "",
                                    "Trade": trade.title(),
                                    "State": state,
                                    "City": addr.get('addressLocality', '') if isinstance(addr, dict) else '',
                                    "Address": addr.get('streetAddress', '') if isinstance(addr, dict) else '',
                                    "Phone": clean(item.get('telephone', '')),
                                    "Email": "",
                                    "Website": clean(item.get('url', '')),
                                    "Source": "Contractors.com"
                                })
                                cont_count += 1
                    except:
                        pass
            time.sleep(0.4)
        except:
            pass

print(f"Contractors.com: {cont_count} records")

# Save what we have so far
print(f"\nTotal so far: {len(results)} records")
with open('/app/new_batch_raw.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["Company Name","Contact Name","Trade","State","City","Address","Phone","Email","Website","Source"])
    writer.writeheader()
    writer.writerows(results)
print("Saved to /app/new_batch_raw.csv")
