import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_server.tools import servicenow as sn

load_dotenv()

def sync_roster():
    print("🔄 Starting ServiceNow to Excel Roster Sync...")
    
    if not sn.is_configured():
        print("❌ ServiceNow is not configured in .env. Sync aborted.")
        return

    # 1. Fetch all assignment groups
    groups = sn.get_all_groups()
    if not groups:
        print("❌ No groups found in ServiceNow.")
        return
    
    print(f"📂 Found {len(groups)} groups. Fetching members...")
    
    all_members = []
    
    # 2. For each group, fetch members
    for group in groups:
        group_name = group.get("name")
        group_id = group.get("sys_id")
        
        print(f"  ↪ Fetching members for '{group_name}'...")
        members = sn.get_group_members(group_id)
        
        for m in members:
            # Map ServiceNow attributes to our Roster structure
            all_members.append({
                "Name": m.get("name"),
                "Email": m.get("email"),
                "Team": group_name,
                "Assignment_Group": group_name,
                "Role": "L1", # Default role
                "Workload": "Low", # Default workload
                "Manager": m.get("manager_name", "Support Manager"),
                "Manager_Email": m.get("manager_email", "softmgr@demo.com")
            })
    
    if not all_members:
        print("⚠️ No members found in any group. Excel not updated.")
        return

    # 3. Create DataFrame and Save
    df_new = pd.DataFrame(all_members)
    
    # Remove duplicates (a user might be in multiple groups)
    df_new = df_new.drop_duplicates(subset=["Email", "Team"])
    
    os.makedirs("data", exist_ok=True)
    output_path = "data/roster.xlsx"
    
    try:
        df_new.to_excel(output_path, index=False)
        print(f"✅ SUCCESSFULLY SYNCED! {len(df_new)} records saved to '{output_path}'.")
    except Exception as e:
        print(f"❌ Error saving Excel file: {e}")

if __name__ == "__main__":
    sync_roster()
