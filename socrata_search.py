"""Search Socrata open data portals for contractor license datasets"""
import requests, json

# Socrata discovery API - search across all portals
def search_socrata(query, limit=20):
    url = "https://api.us.socrata.com/api/catalog/v1"
    params = {
        'q': query,
        'limit': limit,
        'only': 'dataset',
    }
    r = requests.get(url, params=params, timeout=20)
    if r.status_code == 200:
        return r.json().get('results', [])
    return []

queries = [
    "contractor license active",
    "licensed contractors state",
    "contractor license list download",
]

found = {}
for q in queries:
    results = search_socrata(q)
    for r in results:
        name = r.get('resource', {}).get('name', '')
        domain = r.get('metadata', {}).get('domain', '')
        uid = r.get('resource', {}).get('id', '')
        state_abbr = r.get('classification', {}).get('domain_tags', [])
        
        # Filter for state government domains
        if any(gov in domain for gov in ['.gov', 'opendata.', 'data.']):
            if any(k in name.lower() for k in ['contractor', 'builder', 'license', 'electrician', 'plumber', 'hvac']):
                key = f"{domain}_{uid}"
                if key not in found:
                    found[key] = {'name': name, 'domain': domain, 'uid': uid}
                    print(f"Found: [{domain}] {name} (ID: {uid})")

print(f"\nTotal unique datasets: {len(found)}")
for k,v in list(found.items())[:30]:
    download_url = f"https://{v['domain']}/api/views/{v['uid']}/rows.csv?accessType=DOWNLOAD"
    print(f"  {download_url}")
    print(f"    {v['name']}")

