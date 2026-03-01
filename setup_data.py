# setup_data.py
import pandas as pd
import os

os.makedirs("data", exist_ok=True)

# 1. Create Roster (Who is working and how busy are they?)
roster_data = {
    "Name": ["Alice", "Bob", "Charlie", "David"],
    "Email": ["alice@demo.com", "bob@demo.com", "charlie@demo.com", "david@demo.com"],
    "Team": ["SAP_Support", "SAP_Support", "Database_Admin", "Network_Ops"],
    "Workload": ["High", "Low", "Medium", "Low"] # Bob is the best choice for SAP
}
df_roster = pd.DataFrame(roster_data)
df_roster.to_excel("data/roster.xlsx", index=False)

# 2. Create Teams Mapping (Keyword -> Team)
mapping_data = {
    "Keyword": ["sap", "login", "oracle", "sql", "wifi", "internet"],
    "Category": ["SAP Issue", "Access Issue", "Database", "Database", "Network", "Network"],
    "Target_Team": ["SAP_Support", "SAP_Support", "Database_Admin", "Database_Admin", "Network_Ops", "Network_Ops"]
}
df_mapping = pd.DataFrame(mapping_data)
df_mapping.to_excel("data/teams_mapping.xlsx", index=False)

print("✅ Data files created in /data folder!")