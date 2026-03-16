import pandas as pd
import re
import traceback
from mcp_server.tools.servicenow import get_agent_workload

_df_map = None
_df_roster = None

# Scoring Maps
ROLE_PRIORITY = {"L1": 1, "L2": 2, "L3": 3}
SKILL_PRIORITY = {"High": 1, "Medium": 2, "Low": 3}

def _load_data():
    global _df_map, _df_roster
    if _df_map is None or _df_roster is None:
        _df_map = pd.read_excel("data/teams_mapping.xlsx")
        _df_roster = pd.read_excel("data/roster.xlsx")
        
        _df_map["Keyword"] = _df_map["Keyword"].astype(str).str.lower().str.strip()
        _df_map["Target_Team"] = _df_map["Target_Team"].astype(str).str.lower().str.strip()
        
        _df_roster["Team"] = _df_roster["Team"].astype(str).str.lower().str.strip()
        _df_roster["Role"] = _df_roster["Role"].astype(str).str.upper().str.strip()
        # Normalize the new Skill column
        if "Skill_Level" in _df_roster.columns:
            _df_roster["Skill_Level"] = _df_roster["Skill_Level"].astype(str).str.capitalize().str.strip()

def find_best_assignee(issue_description: str, priority: str = "Standard") -> dict:
    try:
        _load_data()
        df_map = _df_map.copy()
        df_roster = _df_roster.copy()
        desc_lower = issue_description.lower()

        # 1. Keyword Matching (Same as before)
        matched_teams =[]
        for _, row in df_map.iterrows():
            keywords = []
            if row["Keyword"] and row["Keyword"] != "nan":
                keywords.extend([kw.strip() for kw in row["Keyword"].split(",") if kw.strip()])
            keywords.extend([kw.strip() for kw in re.split(r'[_\s]+', row["Target_Team"]) if kw.strip()])
            for kw in keywords:
                if kw in desc_lower:
                    matched_teams.append(row["Target_Team"])

        target_team = max(set(matched_teams), key=matched_teams.count) if matched_teams else "help desk"
        team_members = df_roster[df_roster["Team"] == target_team].copy()
        
        if team_members.empty:
            return {"error": f"No agents found in team '{target_team}'"}

        # 2. Fetch Workload
        for index, row in team_members.iterrows():
            team_members.at[index, "Active_Tickets"] = get_agent_workload(str(row["Email"]).strip())

        # 3. Apply Scoring logic
        team_members["Role_Score"] = team_members["Role"].map(ROLE_PRIORITY).fillna(99)
        
        if "Skill_Level" in team_members.columns:
            team_members["Skill_Score"] = team_members["Skill_Level"].map(SKILL_PRIORITY).fillna(99)
        else:
            team_members["Skill_Score"] = 99 # Fallback if column missing

        # 4. 🔥 THE MAGIC: DYNAMIC SORTING BASED ON PRIORITY 🔥
        if priority.lower() == "critical":
            # For Critical: Find Highest Skill first, then lowest workload
            team_members = team_members.sort_values(["Skill_Score", "Active_Tickets", "Role_Score"])
        else:
            # For Standard: Give it to lowest workload first, save the highly skilled people!
            # Sort Skill_Score DESCENDING (so Low/Medium gets the standard tickets)
            team_members = team_members.sort_values(["Active_Tickets", "Role_Score", "Skill_Score"], ascending=[True, True, False])

        best_agent = team_members.iloc[0]

        team_context =[
            f"{row['Name']} (Skill: {row.get('Skill_Level', 'N/A')}) – {int(row['Active_Tickets'])} active tickets" 
            for _, row in team_members.iterrows()
        ]

        return {
            "suggested_agent_name":  str(best_agent["Name"]),
            "suggested_agent_email": str(best_agent["Email"]),
            "team":                  str(best_agent["Team"]),
            "manager_email":         str(best_agent["Manager_Email"]),
            "active_tickets":        int(best_agent["Active_Tickets"]),
            "skill_level":           str(best_agent.get("Skill_Level", "N/A")),
            "team_workload_context": team_context
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}