import pandas as pd
import re

_df_map = None
_df_roster = None

# Role and workload priority
ROLE_PRIORITY = {"L1": 1, "L2": 2, "L3": 3}  # adjust as needed
WORKLOAD_ORDER = {"Low": 1, "Medium": 2, "High": 3}

def _load_data():
    """Load and normalize Excel data."""
    global _df_map, _df_roster
    if _df_map is None or _df_roster is None:
        _df_map = pd.read_excel("data/teams_mapping.xlsx")
        _df_roster = pd.read_excel("data/roster.xlsx")
        _df_map["Keyword"] = _df_map["Keyword"].astype(str).str.lower().str.strip()
        _df_map["Target_Team"] = _df_map["Target_Team"].astype(str).str.lower().str.strip()
        _df_roster["Team"] = _df_roster["Team"].astype(str).str.lower().str.strip()
        _df_roster["Role"] = _df_roster["Role"].astype(str).str.upper().str.strip()
        _df_roster["Workload"] = _df_roster["Workload"].astype(str).str.capitalize().str.strip()

def find_best_assignee(issue_description: str) -> dict:
    """
    Return JSON/dict with agent info for MCP tool.
    """
    try:
        _load_data()
        df_map = _df_map.copy()
        df_roster = _df_roster.copy()
        desc_lower = issue_description.lower()

        matched_teams = []

        for _, row in df_map.iterrows():
            keywords = []

            # Add keywords from Excel if present
            if row["Keyword"]:
                keywords.extend([kw.strip() for kw in row["Keyword"].split(",") if kw.strip()])

            # Add words from Target_Team (split by _ or space)
            keywords.extend([kw.strip() for kw in re.split(r'[_\s]+', row["Target_Team"]) if kw.strip()])

            # Match any keyword in description
            for kw in keywords:
                if kw in desc_lower:
                    matched_teams.append(row["Target_Team"])

        if not matched_teams:
            return {"error": f"No team matched for '{issue_description}'", "email": "helpdesk@demo.com"}

        # Pick the team with most keyword hits
        target_team = max(set(matched_teams), key=matched_teams.count)

        # Filter roster to that team
        team_members = df_roster[df_roster["Team"] == target_team].copy()
        if team_members.empty:
            return {"error": f"No agents in team '{target_team}'", "email": "helpdesk@demo.com"}

        # Score by role + workload
        team_members["Role_Score"] = team_members["Role"].map(ROLE_PRIORITY).fillna(99)
        team_members["Workload_Score"] = team_members["Workload"].map(WORKLOAD_ORDER).fillna(99)

        # Sort: role first, workload second, name third
        best_agent = team_members.sort_values(["Role_Score", "Workload_Score", "Name"]).iloc[0]

        # Return only JSON/dict
        return {
            "agent_name":    best_agent["Name"],
            "agent_email":   best_agent["Email"],
            "team":          best_agent["Team"],
            "role":          best_agent["Role"],
            "workload":      best_agent["Workload"],
            "manager_name":  best_agent["Manager"],
            "manager_email": best_agent["Manager_Email"],
        }

    except Exception as e:
        return {"error": str(e), "email": "helpdesk@demo.com"}