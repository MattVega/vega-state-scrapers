import requests, re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
r = requests.get("https://verify.tn.gov/", headers=headers, timeout=15)
ts = re.search(r'ts=(\d+)', r.text).group(1)

# Get the app bundle
url = f"https://verify.tn.gov/_next/static/chunks/pages/_app.js?ts={ts}"
r2 = requests.get(url, headers=headers, timeout=30)
content = r2.text

# Look for commerce/tn/access patterns
patterns_to_check = [
    r'commerce\.tn\.gov[^\s"\']{0,200}',
    r'cloud\.commerce[^\s"\']{0,200}',
    r'entellitrak[^\s"\']{0,200}',
    r'verify\.tn\.gov[^\s"\']{0,200}',
    r'/v1/[a-z][a-zA-Z/]{5,80}',
    r'baseURL[^;]{0,100}',
    r'apiUrl[^;]{0,100}',
    r'API_URL[^;]{0,100}',
    r'baseUrl[^;]{0,100}',
]

for p in patterns_to_check:
    matches = re.findall(p, content)
    if matches:
        # deduplicate and show first 3
        unique = list(dict.fromkeys(matches))[:3]
        print(f"\n{p}:")
        for m in unique:
            print(f"  {m[:150]}")
