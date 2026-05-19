import requests, json, time
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# Check what the TN contractor board lookup returns
url = "https://verify.tn.gov/"
r = requests.get(url, headers=headers, timeout=15)
print(f"verify.tn.gov: {r.status_code}")

# Find Next.js API routes in the page source
import re
api_routes = re.findall(r'["\'](/api/[^"\']+)["\']', r.text)
print(f"Found API routes: {set(api_routes)}")

# Check page source for any hints
scripts = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', r.text)
print(f"\nJS files: {scripts[:5]}")

# Fetch the main.js to find API routes
for js_file in ['/_next/static/chunks/main.js', '/_next/static/chunks/pages/index.js']:
    url2 = f"https://verify.tn.gov{js_file.split('?')[0]}"
    r2 = requests.get(url2, headers=headers, timeout=15)
    # Find API routes
    apis = re.findall(r'["\']/(api/[^"\'?]{3,50})["\']', r2.text)
    print(f"\n{js_file}: found {len(apis)} API refs: {set(apis)}")
    # Also look for fetch/axios calls
    fetches = re.findall(r'fetch\(["\']([^"\']+)["\']', r2.text)
    print(f"fetch calls: {fetches[:10]}")
