import requests, json

# Try to find the right Nashville dataset
for dataset_id in ["qqst-dkzw", "f74b-mthp", "uigu-myar", "rqf6-nsei"]:
    url = f"https://data.nashville.gov/resource/{dataset_id}.json"
    try:
        r = requests.get(url, params={"$limit": 5}, timeout=15)
        print(f"{dataset_id}: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"{dataset_id}: {e}")

# Also try TN open data portal
print("\n=== TN Open Data ===")
for dataset in ["4apk-w6id", "iyzp-hwv9", "f74b-mthp"]:
    url = f"https://data.tn.gov/resource/{dataset}.json"
    try:
        r = requests.get(url, params={"$limit": 5}, timeout=15)
        print(f"{dataset}: {r.status_code} - {r.text[:200]}")
    except Exception as e:
        print(f"{dataset}: {e}")
