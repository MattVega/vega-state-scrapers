import requests, json

# Nashville uses ArcGIS for their datasets
# Try their feature service
urls = [
    "https://services.arcgis.com/pD9eTAH2tGPJa/ArcGIS/rest/services",
    "https://data.nashville.gov/api/views/",
    "https://data.nashville.gov/api/catalog/v1",
    "https://data.nashville.gov/resource/registered-professional-contractors-and-licenses.json"
]

for url in urls:
    try:
        r = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        print(f"\n{url}")
        print(f"Status: {r.status_code}")
        print(r.text[:300])
    except Exception as e:
        print(f"{url}: {e}")
