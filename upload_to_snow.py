import os
import requests
import pandas as pd
import io
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

INSTANCE = os.getenv("SNOW_INSTANCE", "").replace("https://", "").replace("http://", "").strip("/")
USER = os.getenv("SNOW_USER")
PWD = os.getenv("SNOW_PASSWORD")
BASE_URL = f"https://{INSTANCE}/api/now/table"

# ==========================================
# 1. YOUR ROSTER DATA (Hardcoded for easy upload)
# ==========================================
ROSTER_DATA = """Name	Email	Team	Role	Workload	Manager	Manager_Email
Alice	alice@demo.com	SAP_Support	L2	High	Mr. Kumar	kumar@demo.com
Bob	bob@demo.com	SAP_Support	L2	Low	Mr. Kumar	kumar@demo.com
Charlie	charlie@demo.com	Database_Admin	L3	Medium	Ms. Sharma	sharma@demo.com
David	david@demo.com	Network_Ops	L1	Low	Mr. Patel	patel@demo.com
Eve	eve@demo.com	Network_Ops	L2	Low	Mr. Patel	patel@demo.com
Frank	frank@demo.com	Network_Ops	L1	Medium	Mr. Patel	patel@demo.com
Grace	grace@demo.com	Database_Admin	L2	Low	Ms. Sharma	sharma@demo.com
Henry	henry@demo.com	Database_Admin	L1	Medium	Ms. Sharma	sharma@demo.com
Irene	irene@demo.com	SAP_Support	L1	Low	Mr. Kumar	kumar@demo.com
Jack	jack@demo.com	SAP_Support	L3	Medium	Mr. Kumar	kumar@demo.com
Karen	vijethfernandes23@gmail.com	Software_Support	L1	Low	Ms. Nair	vijethfernandes21@gmail.com
Leo	leo@demo.com	Software_Support	L1	Medium	Ms. Nair	vijethfernandes21@gmail.com
Mia	mia@demo.com	Software_Support	L2	Low	Ms. Nair	vijethfernandes21@gmail.com
Nathan	nathan@demo.com	Software_Support	L2	High	Ms. Nair	vijethfernandes21@gmail.com
Olivia	olivia@demo.com	Software_Support	L3	Medium	Ms. Nair	vijethfernandes21@gmail.com
Paul	paul@demo.com	Hardware_Support	L1	Low	Mr. Verma	verma@demo.com
Quinn	quinn@demo.com	Hardware_Support	L1	High	Mr. Verma	verma@demo.com
Rachel	rachel@demo.com	Hardware_Support	L2	Low	Mr. Verma	verma@demo.com
Sam	sam@demo.com	Hardware_Support	L2	Medium	Mr. Verma	verma@demo.com
Tina	tina@demo.com	Hardware_Support	L3	Low	Mr. Verma	verma@demo.com
Uma	uma@demo.com	Cloud_Ops	L1	Low	Mr. Reddy	reddy@demo.com
Victor	victor@demo.com	Cloud_Ops	L1	Medium	Mr. Reddy	reddy@demo.com
Wendy	wendy@demo.com	Cloud_Ops	L2	Low	Mr. Reddy	reddy@demo.com
Xander	xander@demo.com	Cloud_Ops	L2	High	Mr. Reddy	reddy@demo.com
Yara	yara@demo.com	Cloud_Ops	L3	Medium	Mr. Reddy	reddy@demo.com
Zoe	zoe@demo.com	Cloud_Ops	L3	Low	Mr. Reddy	reddy@demo.com
Jhon	jhon@demo.com	Procurement	L3	Low	Mr. Tom	tom@demo.com
"""

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_sys_id(table, query):
    """Check if record exists and return SysID."""
    url = f"{BASE_URL}/{table}?sysparm_query={query}&sysparm_fields=sys_id&sysparm_limit=1"
    res = requests.get(url, auth=HTTPBasicAuth(USER, PWD))
    data = res.json().get("result",[])
    return data[0]["sys_id"] if data else None

def create_record(table, payload):
    """Create a new record and return SysID."""
    url = f"{BASE_URL}/{table}"
    res = requests.post(url, auth=HTTPBasicAuth(USER, PWD), json=payload)
    if res.status_code == 201:
        return res.json().get("result", {}).get("sys_id")
    print(f"❌ Error creating in {table}: {res.text}")
    return None

def upsert_group(name, manager_sys_id=None):
    """Find or create an Assignment Group, and link the manager."""
    sys_id = get_sys_id("sys_user_group", f"name={name}")
    
    payload = {"name": name}
    if manager_sys_id: 
        payload["manager"] = manager_sys_id

    if sys_id: 
        # Update existing group with manager if it changed
        if manager_sys_id:
            requests.patch(f"{BASE_URL}/sys_user_group/{sys_id}", auth=HTTPBasicAuth(USER, PWD), json=payload)
        return sys_id
        
    print(f"   [+] Creating Group: {name}")
    return create_record("sys_user_group", payload)

def upsert_user(name, email, manager_sys_id=None):
    """Find or create a User."""
    sys_id = get_sys_id("sys_user", f"email={email}")
    if sys_id: 
        # Optionally update manager if they already exist
        if manager_sys_id:
            requests.patch(f"{BASE_URL}/sys_user/{sys_id}", auth=HTTPBasicAuth(USER, PWD), json={"manager": manager_sys_id})
        return sys_id
    
    print(f"   [+] Creating User: {name} ({email})")
    first_name = name.split()[0]
    last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else "User"
    
    payload = {
        "user_name": email, # SNOW login ID
        "email": email,
        "first_name": first_name,
        "last_name": last_name
    }
    if manager_sys_id:
        payload["manager"] = manager_sys_id
        
    return create_record("sys_user", payload)

def link_user_to_group(user_id, group_id):
    """Add user to group in sys_user_grmember."""
    query = f"user={user_id}^group={group_id}"
    sys_id = get_sys_id("sys_user_grmember", query)
    if sys_id: return # Already in group
    create_record("sys_user_grmember", {"user": user_id, "group": group_id})

# ==========================================
# 3. MAIN EXECUTION
# ==========================================
def run_upload():
    if not INSTANCE or not USER:
        print("❌ Missing ServiceNow credentials in .env file.")
        return

    print("🚀 Starting ServiceNow Bulk Upload...")
    df = pd.read_csv(io.StringIO(ROSTER_DATA), sep="\t")
    
    # Clean whitespace
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    # 1. CREATE MANAGERS FIRST
    print("\n👔 1. Setting up Managers...")
    managers = df[["Manager", "Manager_Email"]].drop_duplicates()
    manager_sys_ids = {}
    for _, row in managers.iterrows():
        mgr_sys_id = upsert_user(row["Manager"], row["Manager_Email"])
        manager_sys_ids[row["Manager_Email"]] = mgr_sys_id
        
    print("\n🏢 2. Setting up Teams (Groups)...")
    teams = df["Team"].unique()
    team_sys_ids = {}
    for team in teams:
        # Find the manager email for this specific team from the dataframe
        team_manager_email = df[df["Team"] == team]["Manager_Email"].iloc[0]
        # Get their SysID which we created in Step 1
        mgr_sys_id = manager_sys_ids.get(team_manager_email)
        
        # Pass the mgr_sys_id into the upsert function
        team_sys_ids[team] = upsert_group(team, manager_sys_id=mgr_sys_id)

    # 3. CREATE AGENTS & LINK THEM
    print("\n👷 3. Setting up Agents and linking to Teams...")
    for _, row in df.iterrows():
        name = row["Name"]
        email = row["Email"]
        team = row["Team"]
        mgr_email = row["Manager_Email"]
        
        # Create user (linked to manager)
        user_sys_id = upsert_user(name, email, manager_sys_ids.get(mgr_email))
        
        # Link to team
        if user_sys_id and team in team_sys_ids:
            link_user_to_group(user_sys_id, team_sys_ids[team])

    print("\n✅ UPLOAD COMPLETE! All users, managers, and groups are now in ServiceNow.")
    print("Native approvals will now work flawlessly since managers exist in the system!")

if __name__ == "__main__":
    run_upload()