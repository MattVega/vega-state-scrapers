import requests, json

# Try to find Nashville contractors via ArcGIS REST API
base = "https://services.arcgis.com"

# Common Nashville GIS service patterns
test_urls = [
    "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services?f=json",
    "https://services1.arcgis.com/pD9eTAH2tGPJa/arcgis/rest/services?f=json",
    "https://gis.nashville.gov/arcgis/rest/services?f=json",
    "https://maps.nashville.gov/arcgis/rest/services?f=json",
]

for url in test_urls:
    try:
        r = requests.get(url, timeout=15)
        print(f"\n{url}")
        print(f"Status: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"{url}: {e}")

print("\n=== Nashville Codes Services ===")
r = requests.get("https://maps.nashville.gov/arcgis/rest/services/Codes?f=json", timeout=15)
print(r.text[:1000])
