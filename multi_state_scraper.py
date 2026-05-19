"""
Multi-state contractor license scraper
Hits multiple state databases in parallel
"""
import requests, csv, time, re, os, io, json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

session_lock = threading.Lock()
results = {}

def scrape_michigan():
    """Michigan BCC - contractor licenses via LARA"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        # Michigan has a licensee search - try the bulk export
        url = "https://aca3.accela.com/MILARA/GeneralProperty/LicenseeSearch.aspx"
        # Actually let me try the LARA API
        url2 = "https://www.michigan.gov/api/v1/licensees/download?type=contractor"
        r = s.get(url2, timeout=15)
        if r.status_code == 200 and len(r.text) > 1000:
            return 'MI', r.text, 'api'
    except Exception as e:
        pass
    return 'MI', None, None

def scrape_wisconsin():
    """Wisconsin DSPS contractor licenses"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        # Try DSPS open data
        url = "https://licensesearch.wi.gov/api/Download/DownloadCsv?licenseType=contractor&status=active"
        r = s.get(url, timeout=20)
        ct = r.headers.get('content-type','')
        if 'csv' in ct or (len(r.text) > 1000 and ',' in r.text[:200]):
            return 'WI', r.text, 'csv'
    except: pass
    return 'WI', None, None

def scrape_tennessee():
    """Tennessee TDCI contractor roster"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    urls = [
        "https://www.tn.gov/content/dam/tn/commerce/documents/regboards/contractors/Roster_Unlimited_License.xls",
        "https://www.tn.gov/content/dam/tn/commerce/documents/regboards/contractors/contractor_roster.csv",
        "https://www.tn.gov/content/dam/tn/commerce/documents/regboards/contractors/Active_Licensees.xlsx",
    ]
    for url in urls:
        try:
            r = s.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 5000:
                ext = url.split('.')[-1].lower()
                return 'TN', r.content, ext
        except: pass
    return 'TN', None, None

def scrape_north_carolina():
    """NC LBGC - general contractors"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        # NCLBGC has a CSV download
        r = s.get("https://www.nclbgc.org/licensee-export.csv", timeout=20)
        if r.status_code == 200 and 'csv' in r.headers.get('content-type',''):
            return 'NC', r.text, 'csv'
        # Try their API
        r2 = s.get("https://www.nclbgc.org/api/licensees?format=csv", timeout=20)
        if r2.status_code == 200:
            return 'NC', r2.text, 'csv'
    except: pass
    return 'NC', None, None

def scrape_georgia():
    """Georgia Secretary of State contractor licenses"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        # Georgia SOS has downloadable lists
        url = "https://verify.sos.ga.gov/verification/DownloadContractors.aspx"
        r = s.get(url, timeout=20)
        if r.status_code == 200 and len(r.content) > 5000:
            return 'GA', r.content, 'csv'
    except: pass
    return 'GA', None, None

def scrape_illinois():
    """Illinois IDFPR license data"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    # IDFPR publishes CSV dumps on data.illinois.gov
    endpoints = [
        "https://data.illinois.gov/api/views/xkcr-r83s/rows.csv?accessType=DOWNLOAD",  # contractors
        "https://idfpr.illinois.gov/licenselookup/",
    ]
    for url in endpoints:
        try:
            r = s.get(url, timeout=30)
            ct = r.headers.get('content-type','')
            if ('csv' in ct or 'text' in ct) and len(r.text) > 5000 and ',' in r.text[:100]:
                return 'IL', r.text, 'csv'
        except: pass
    return 'IL', None, None

def scrape_minnesota_add():
    """Minnesota - additional trades beyond what we have"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        # MN DLI has CSV exports
        url = "https://www.dli.mn.gov/sites/default/files/csv/licensed_contractors.csv"
        r = s.get(url, timeout=30)
        if r.status_code == 200 and len(r.text) > 1000:
            return 'MN2', r.text, 'csv'
    except: pass
    return 'MN2', None, None

def scrape_kentucky():
    """Kentucky contractors"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        url = "https://secure.kentucky.gov/LicenseeSearch/DownloadContractors.aspx"
        r = s.get(url, timeout=20)
        if r.status_code == 200 and len(r.content) > 5000:
            return 'KY', r.content, 'csv'
    except: pass
    return 'KY', None, None

def scrape_new_mexico():
    """New Mexico Construction Industries Division"""
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0'})
    try:
        url = "https://www.rld.nm.gov/construction/contractor-search/download-licensees/"
        r = s.get(url, timeout=20)
        if r.status_code == 200 and len(r.content) > 5000:
            return 'NM', r.content, 'csv'
    except: pass
    return 'NM', None, None

scrapers = [
    scrape_michigan, scrape_wisconsin, scrape_tennessee, scrape_north_carolina,
    scrape_georgia, scrape_illinois, scrape_kentucky, scrape_new_mexico,
]

print("Running parallel state scrapers...")
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = {executor.submit(fn): fn.__name__ for fn in scrapers}
    for future in as_completed(futures):
        fn_name = futures[future]
        try:
            state, data, fmt = future.result()
            if data:
                size = len(data) if isinstance(data, str) else len(data)
                print(f"  ✓ {state}: got {size:,} bytes ({fmt})")
                results[state] = (data, fmt)
            else:
                print(f"  ✗ {state}: no data")
        except Exception as e:
            print(f"  ✗ {fn_name}: error - {e}")

print(f"\nSuccessful: {list(results.keys())}")
