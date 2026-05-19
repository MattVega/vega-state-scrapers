import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# All states except TX and FL
STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "Georgia", "Hawaii",
    "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
    "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
    "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming"
]

STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}

TRADES = [
    ("drywall+contractors", "Drywall"),
    ("painting+contractors", "Paint"),
    ("flooring+contractors", "Flooring"),
]

def clean(s):
    if not s:
        return ""
    return re.sub(r'\s+', ' ', str(s)).strip()

def parse_phone(text):
    m = re.search(r'\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}', text)
    return m.group().strip() if m else ""

def scrape_yp_page(trade_query, state_name, page=1):
    """Scrape one page of Yellow Pages results"""
    url = f"https://www.yellowpages.com/search"
    params = {
        "search_terms": trade_query.replace("+", " "),
        "geo_location_terms": state_name,
        "page": page
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return [], False
        
        soup = BeautifulSoup(r.text, 'lxml')
        listings = []
        
        # Find all business result cards
        cards = soup.find_all('div', class_=re.compile(r'result|v-card', re.I))
        if not cards:
            cards = soup.find_all('article') or soup.find_all('div', {'class': lambda x: x and 'listing' in x.lower()})
        
        # Parse each card
        for card in cards:
            text = card.get_text(separator=' ')
            
            # Company name
            name_el = card.find(['h2', 'h3', 'a'], class_=re.compile(r'business-name|name|title', re.I))
            if not name_el:
                name_el = card.find('a', class_=re.compile(r'business|listing', re.I))
            name = clean(name_el.get_text()) if name_el else ""
            
            # Skip non-contractor entries
            if not name or len(name) < 3:
                continue
            
            # Phone
            phone_el = card.find(class_=re.compile(r'phone|tel|contact', re.I))
            phone = clean(phone_el.get_text()) if phone_el else parse_phone(text)
            
            # Address
            addr_el = card.find(class_=re.compile(r'address|street|locality', re.I))
            address = clean(addr_el.get_text()) if addr_el else ""
            
            # City/State from address or locality
            city = ""
            locality_el = card.find(class_=re.compile(r'locality|city', re.I))
            if locality_el:
                city = clean(locality_el.get_text()).split(',')[0]
            
            # Website
            web_el = card.find('a', string=re.compile(r'website|www', re.I))
            website = web_el.get('href', '') if web_el else ""
            
            if name:
                listings.append({
                    "Company Name": name,
                    "Contact Name": "",
                    "Trade": "",  # filled by caller
                    "State": STATE_CODES.get(state_name, state_name),
                    "City": city,
                    "Address": address,
                    "Phone": phone,
                    "Email": "",
                    "Website": website,
                    "Source": "YellowPages"
                })
        
        # Check if there's a next page
        next_btn = soup.find('a', class_=re.compile(r'next', re.I))
        has_next = next_btn is not None and page < 5  # Max 5 pages per query
        
        return listings, has_next
        
    except Exception as e:
        print(f"  Error: {e}")
        return [], False


results = []
seen_phones = set()
total = 0

# Load existing phones for dedup
print("Loading existing contacts for dedup...")
try:
    with open('/app/master_subcontractors_v2.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            phone = re.sub(r'\D', '', row.get('Phone', ''))
            if phone:
                seen_phones.add(phone)
    print(f"Loaded {len(seen_phones)} existing phones")
except Exception as e:
    print(f"Could not load existing: {e}")

output_file = '/app/yp_new_contacts.csv'
fieldnames = ["Company Name","Contact Name","Trade","State","City","Address","Phone","Email","Website","Source"]

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for state in STATES:
        state_count = 0
        for trade_query, trade_label in TRADES:
            page = 1
            has_next = True
            while has_next and page <= 5:
                listings, has_next = scrape_yp_page(trade_query, state, page)
                
                for listing in listings:
                    listing["Trade"] = trade_label
                    phone_digits = re.sub(r'\D', '', listing.get("Phone", ""))
                    
                    # Skip if no phone or already in DB
                    if not phone_digits or phone_digits in seen_phones:
                        continue
                    
                    seen_phones.add(phone_digits)
                    results.append(listing)
                    writer.writerow(listing)
                    state_count += 1
                    total += 1
                
                page += 1
                time.sleep(random.uniform(0.8, 1.5))
        
        print(f"{state}: +{state_count} new | Running total: {total}")
        time.sleep(random.uniform(0.5, 1.0))

print(f"\n✅ Done! Total new contacts: {total}")
print(f"Saved to {output_file}")
