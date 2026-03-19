import os
import requests
import json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()
INSTANCE = os.getenv("SNOW_INSTANCE", "").replace("https://", "").replace("http://", "").strip("/")
USER = os.getenv("SNOW_USER")
PWD = os.getenv("SNOW_PASSWORD")
BASE_URL = f"https://{INSTANCE}/api/now/table"

def run_brute_force():
    print(f"🚀 Starting Brute Force Diagnostic as: {USER}\n")
    
    ticket_number = "INC0010110" 
    
    # 1. FETCH IDs
    print(f"🔍 Fetching IDs...")
    inc_res = requests.get(f"{BASE_URL}/incident?sysparm_query=number={ticket_number}", auth=HTTPBasicAuth(USER, PWD))
    inc_sys_id = inc_res.json().get("result",[])[0]["sys_id"]
    
    mgr_res = requests.get(f"{BASE_URL}/sys_user?sysparm_query=user_name=intern_3", auth=HTTPBasicAuth(USER, PWD))
    mgr_sys_id = mgr_res.json().get("result",[])[0]["sys_id"]
    print(f"   ✅ Incident: {inc_sys_id} | Manager (intern_3): {mgr_sys_id}\n")

    # 2. BRUTE FORCE PAYLOADS
    print("\n⚙️ Testing Method 5: The 'Not Requested' State Bypass...")
    approval_url = f"{BASE_URL}/sysapproval_approver?sysparm_input_display_value=false"
    
    # 1. Insert it silently without triggering the Approval Engine
    insert_payload = {
        "approver": str(mgr_sys_id).strip(),
        "sysapproval": str(inc_sys_id).strip(),
        "state": "not_requested"   # <--- THE MAGIC BYPASS KEY
    }
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    res = requests.post(approval_url, auth=HTTPBasicAuth(USER, PWD), headers=headers, json=insert_payload)
    
    if res.status_code == 201:
        result = res.json().get("result", {})
        sys_id = result.get("sys_id")
        appr = result.get('approver', '')
        
        # Did it keep the fields?
        if appr:
            print(f"   ✅ SUCCESS on Insert! It kept the fields when state was 'not_requested'.")
            print("   ↳ Now updating state to 'requested' to trigger your email...")
            
            # 2. Now patch it to requested to fire the email
            patch_url = f"{approval_url}/{sys_id}"
            requests.patch(patch_url, auth=HTTPBasicAuth(USER, PWD), headers=headers, json={"state": "requested"})
            print("   ✅ Update complete. Check ServiceNow!")
        else:
            print(f"   ❌ FAILED: Still wiped the fields even on 'not_requested'.")

if __name__ == "__main__":
    run_brute_force()