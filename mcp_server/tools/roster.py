# import pandas as pd
# import re
# import traceback

# _df_map = None
# _df_roster = None

# # Role and workload priority
# ROLE_PRIORITY = {"L1": 1, "L2": 2, "L3": 3}
# WORKLOAD_ORDER = {"Low": 1, "Medium": 2, "High": 3}

# def _load_data():
#     """Load and normalize Excel data."""
#     global _df_map, _df_roster
#     if _df_map is None or _df_roster is None:
#         try:
#             _df_map = pd.read_excel("data/teams_mapping.xlsx")
#             _df_roster = pd.read_excel("data/roster.xlsx")
            
#             # Normalize strings to avoid mismatch issues
#             _df_map["Keyword"] = _df_map["Keyword"].astype(str).str.lower().str.strip()
#             _df_map["Target_Team"] = _df_map["Target_Team"].astype(str).str.lower().str.strip()
            
#             _df_roster["Team"] = _df_roster["Team"].astype(str).str.lower().str.strip()
#             _df_roster["Role"] = _df_roster["Role"].astype(str).str.upper().str.strip()
#             _df_roster["Workload"] = _df_roster["Workload"].astype(str).str.capitalize().str.strip()
#         except Exception as e:
#             print(f"❌ Error loading Excel files: {e}")
#             raise e

# def find_best_assignee(issue_description: str) -> dict:
#     """
#     Return JSON/dict with agent info for MCP tool.
#     Guarantees a valid return structure even if no match is found.
#     """
#     try:
#         _load_data()
#         df_map = _df_map.copy()
#         df_roster = _df_roster.copy()
#         desc_lower = issue_description.lower()

#         matched_teams = []

#         # 1. Keyword Matching
#         for _, row in df_map.iterrows():
#             keywords = []
#             if row["Keyword"] and row["Keyword"] != "nan":
#                 keywords.extend([kw.strip() for kw in row["Keyword"].split(",") if kw.strip()])
            
#             # Also match against the Team Name itself
#             keywords.extend([kw.strip() for kw in re.split(r'[_\s]+', row["Target_Team"]) if kw.strip()])

#             for kw in keywords:
#                 if kw in desc_lower:
#                     matched_teams.append(row["Target_Team"])

#         # 2. Determine Target Team (With Fallback)
#         if not matched_teams:
#             print(f"⚠️ No keyword match for '{issue_description}'. Initiating Fallback.")
            
#             # Fallback Strategy: Look for 'Help Desk' or take the first available team
#             unique_teams = df_roster["Team"].unique()
#             if "help desk" in unique_teams:
#                 target_team = "help desk"
#             elif len(unique_teams) > 0:
#                 target_team = unique_teams[0] # Pick the first team found
#             else:
#                 # Absolute panic fallback
#                 return {
#                     "error": "Roster is empty",
#                     "agent_email": "admin@demo.com", 
#                     "manager_email": "admin@demo.com"
#                 }
#         else:
#             # Pick the most frequently matched team
#             target_team = max(set(matched_teams), key=matched_teams.count)

#         # 3. Filter Roster for that Team
#         team_members = df_roster[df_roster["Team"] == target_team].copy()
        
#         if team_members.empty:
#             return {
#                 "error": f"No agents found in team '{target_team}'",
#                 "agent_email": "admin@demo.com", 
#                 "manager_email": "admin@demo.com"
#             }

#         # 4. Score Candidates (L1 > L2, Low Workload > High)
#         team_members["Role_Score"] = team_members["Role"].map(ROLE_PRIORITY).fillna(99)
#         team_members["Workload_Score"] = team_members["Workload"].map(WORKLOAD_ORDER).fillna(99)

#         # Sort values
#         best_agent = team_members.sort_values(["Role_Score", "Workload_Score", "Name"]).iloc[0]

#         # 5. SUCCESS RETURN
#         return {
#             "agent_name":    str(best_agent["Name"]),
#             "agent_email":   str(best_agent["Email"]),
#             "team":          str(best_agent["Team"]),
#             "role":          str(best_agent["Role"]),
#             "workload":      str(best_agent["Workload"]),
#             "manager_name":  str(best_agent["Manager"]),
#             "manager_email": str(best_agent["Manager_Email"]),
#         }

#     except Exception as e:
#         traceback.print_exc()
#         return {
#             "error": str(e),
#             "agent_email": "error_fallback@demo.com",
#             "manager_email": "manager_fallback@demo.com"
#         }





import pandas as pd
import re
import traceback

# Import our new real-time workload function
from mcp_server.tools.servicenow import get_agent_workload

_df_map = None
_df_roster = None

ROLE_PRIORITY = {"L1": 1, "L2": 2, "L3": 3}

def _load_data():
    """Load and normalize Excel data."""
    global _df_map, _df_roster
    if _df_map is None or _df_roster is None:
        try:
            _df_map = pd.read_excel("data/teams_mapping.xlsx")
            _df_roster = pd.read_excel("data/roster.xlsx")
            
            _df_map["Keyword"] = _df_map["Keyword"].astype(str).str.lower().str.strip()
            _df_map["Target_Team"] = _df_map["Target_Team"].astype(str).str.lower().str.strip()
            
            _df_roster["Team"] = _df_roster["Team"].astype(str).str.lower().str.strip()
            _df_roster["Role"] = _df_roster["Role"].astype(str).str.upper().str.strip()
        except Exception as e:
            print(f"❌ Error loading Excel files: {e}")
            raise e

def find_best_assignee(issue_description: str) -> dict:
    """
    Finds the target team based on keywords, queries ServiceNow for real-time 
    workloads of team members, and returns the best candidate + full team context.
    """
    try:
        _load_data()
        df_map = _df_map.copy()
        df_roster = _df_roster.copy()
        desc_lower = issue_description.lower()

        matched_teams =[]

        # 1. Keyword Matching
        for _, row in df_map.iterrows():
            keywords = []
            if row["Keyword"] and row["Keyword"] != "nan":
                keywords.extend([kw.strip() for kw in row["Keyword"].split(",") if kw.strip()])
            
            keywords.extend([kw.strip() for kw in re.split(r'[_\s]+', row["Target_Team"]) if kw.strip()])

            for kw in keywords:
                if kw in desc_lower:
                    matched_teams.append(row["Target_Team"])

        # 2. Determine Target Team
        if not matched_teams:
            unique_teams = df_roster["Team"].unique()
            target_team = "help desk" if "help desk" in unique_teams else (unique_teams[0] if len(unique_teams) > 0 else None)
        else:
            target_team = max(set(matched_teams), key=matched_teams.count)

        if not target_team:
            return {"error": "Roster is empty"}

        # 3. Filter Roster for that Team
        team_members = df_roster[df_roster["Team"] == target_team].copy()
        
        if team_members.empty:
            return {"error": f"No agents found in team '{target_team}'"}

        # 4. Fetch Real-Time Workload from ServiceNow
        for index, row in team_members.iterrows():
            email = str(row["Email"]).strip()
            # Hit ServiceNow API for active incidents
            active_count = get_agent_workload(email)
            team_members.at[index, "Active_Tickets"] = active_count

        # 5. Score Candidates (L1 > L2, lowest active tickets > highest)
        team_members["Role_Score"] = team_members["Role"].map(ROLE_PRIORITY).fillna(99)
        team_members = team_members.sort_values(["Role_Score", "Active_Tickets", "Name"])

        best_agent = team_members.iloc[0]

        # 6. Generate Team Workload Context for the Manager Email
        # This creates the exact list you requested: "Karen - 5 active incidents"
        team_context = [
            f"{row['Name']} – {int(row['Active_Tickets'])} active incidents" 
            for _, row in team_members.iterrows()
        ]

        # 7. SUCCESS RETURN
        return {
            "suggested_agent_name":  str(best_agent["Name"]),
            "suggested_agent_email": str(best_agent["Email"]),
            "team":                  str(best_agent["Team"]),
            "manager_email":         str(best_agent["Manager_Email"]),
            "active_tickets":        int(best_agent["Active_Tickets"]),
            "team_workload_context": team_context # Pass this array back to the AI!
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}