import os, json, requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()
INSTANCE = os.getenv("SNOW_INSTANCE", "").replace("https://", "").replace("http://", "").strip("/")
USER = os.getenv("SNOW_USER")
PWD = os.getenv("SNOW_PASSWORD")

print(f"Connecting to: {INSTANCE}")

# Test 1: Stats API (grouped by state)
url = f"https://{INSTANCE}/api/now/stats/incident"
res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params={"sysparm_count": "true", "sysparm_group_by": "state"}, timeout=15)
print(f"\n=== Stats API - Status: {res.status_code} ===")
print(json.dumps(res.json(), indent=2))

# Test 2: Table API - check raw state values with display values
url2 = f"https://{INSTANCE}/api/now/table/incident"
res2 = requests.get(url2, auth=HTTPBasicAuth(USER, PWD), params={
    "sysparm_fields": "number,state,short_description",
    "sysparm_limit": 20,
    "sysparm_display_value": "all"
}, timeout=15)
print(f"\n=== Table API (raw+display) - Status: {res2.status_code} ===")
for r in res2.json().get("result", []):
    state_raw = r.get("state", {})
    print(f"  {r.get('number', {}).get('value', '?')} | state.value={state_raw.get('value')} | state.display={state_raw.get('display_value')}")
