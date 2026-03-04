# setup_data.py
import pandas as pd
import os

os.makedirs("data", exist_ok=True)

# 1. Create Roster (Who is working and how busy are they?)
roster_data = {
    "Name": ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"],
    "Email": ["alice@demo.com", "bob@demo.com", "charlie@demo.com", "david@demo.com", "eve@demo.com", "frank@demo.com"],
    "Team": ["SAP_Support", "SAP_Support", "Database_Admin", "Network_Ops", "Software", "Hardware"],
    "Workload": ["High", "Low", "Medium", "Low", "Low", "Low"],
    "Role": ["L1", "L1", "L2", "L1", "L1", "L1"], # Added Role column as roster.py expects it
    "Manager": ["Mgr1", "Mgr1", "Mgr2", "Mgr3", "SoftMgr", "HardMgr"],
    "Manager_Email": ["mgr1@demo.com", "mgr1@demo.com", "mgr2@demo.com", "mgr3@demo.com", "softmgr@demo.com", "hardmgr@demo.com"]
}
df_roster = pd.DataFrame(roster_data)
df_roster.to_excel("data/roster.xlsx", index=False)

# 2. Create Teams Mapping (Keyword -> Team)
mapping_data = {
    "Keyword": ["sap", "login", "oracle", "sql", "wifi", "internet", "software", "bug", "hardware", "laptop"],
    "Category": ["SAP Issue", "Access Issue", "Database", "Database", "Network", "Network", "Software", "Software", "Hardware", "Hardware"],
    "Target_Team": ["SAP_Support", "SAP_Support", "Database_Admin", "Database_Admin", "Network_Ops", "Network_Ops", "Software", "Software", "Hardware", "Hardware"],
    "Manager_Email": [
        "mgr1@demo.com", "mgr1@demo.com", "mgr2@demo.com", "mgr2@demo.com", "mgr3@demo.com", "mgr3@demo.com",
        "softmgr@demo.com", "softmgr@demo.com", "hardmgr@demo.com", "hardmgr@demo.com"
    ]
}
df_mapping = pd.DataFrame(mapping_data)
df_mapping.to_excel("data/teams_mapping.xlsx", index=False)

print("✅ Data files created in /data folder!") 