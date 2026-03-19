import pandas as pd
import re
import traceback

# Import our new real-time workload function
from mcp_server.tools.servicenow import get_agent_workload

_df_map = None
_df_roster = None

ROLE_PRIORITY = {"L1": 1, "L2": 2, "L3": 3}
# Map the new Expertise Levels to a numerical score (1 is the best)
EXPERTISE_PRIORITY = {"Expert": 1, "Advanced": 2, "Intermediate": 3, "Beginner": 4}

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
            
            if "Expertise_Level" in _df_roster.columns:
                _df_roster["Expertise_Level"] = _df_roster["Expertise_Level"].astype(str).str.capitalize().str.strip()
        except Exception as e:
            print(f"❌ Error loading Excel files: {e}")
            raise e

def find_best_assignee(issue_description: str, priority: str = "Standard", caller_email: str = None) -> dict:
    try:
        _load_data()
        df_map = _df_map.copy()
        df_roster = _df_roster.copy()
        desc_lower = issue_description.lower()

        # 1. Keyword Matching to find the target Team
        matched_teams = []
        for _, row in df_map.iterrows():
            keywords =[]
            if row["Keyword"] and row["Keyword"] != "nan":
                keywords.extend([kw.strip() for kw in row["Keyword"].split(",") if kw.strip()])
            
            keywords.extend([kw.strip() for kw in re.split(r'[_\s]+', row["Target_Team"]) if kw.strip()])

            for kw in keywords:
                if kw in desc_lower:
                    matched_teams.append(row["Target_Team"])

        if not matched_teams:
            unique_teams = df_roster["Team"].unique()
            target_team = "help desk" if "help desk" in unique_teams else (unique_teams[0] if len(unique_teams) > 0 else None)
        else:
            target_team = max(set(matched_teams), key=matched_teams.count)

        if not target_team: return {"error": "Roster is empty"}

        team_members = df_roster[df_roster["Team"] == target_team].copy()
        # 🔥 THE FIX: Remove the caller from the list of possible assignees!
        if caller_email:
            team_members = team_members[team_members["Email"].str.lower() != caller_email.lower()]
        if team_members.empty: 
            return {"error": f"No valid agents found in team '{target_team}' (Caller cannot be assigned to their own ticket)."}

        # 2. Score Candidates based on EXACT SKILLS and Workload
        for index, row in team_members.iterrows():
            # Get real-time workload
            team_members.at[index, "Active_Tickets"] = get_agent_workload(str(row["Email"]).strip())
            
            # --- 🔥 SKILL MATCHING ENGINE 🔥 ---
            skill_match_score = 0
            # Combine Primary and Secondary skills into one string
            skills_text = str(row.get("Primary_Skills", "")) + " " + str(row.get("Secondary_Skills", ""))
            # Split them by commas or spaces
            skills_list =[s.strip().lower() for s in re.split(r'[,/]+', skills_text) if s.strip() and s.strip() != "nan"]
            
            # Check if any of the agent's skills are mentioned in the user's issue!
            for skill in skills_list:
                if skill in desc_lower:
                    skill_match_score += 1 # Boost their score if there is a match!
                    
            team_members.at[index, "Skill_Match_Score"] = skill_match_score
            # -----------------------------------

        # 3. Setup baseline scores
        team_members["Role_Score"] = team_members["Role"].map(ROLE_PRIORITY).fillna(99)
        if "Expertise_Level" in team_members.columns:
            team_members["Expertise_Score"] = team_members["Expertise_Level"].map(EXPERTISE_PRIORITY).fillna(99)
        else:
            team_members["Expertise_Score"] = 99

        # 4. 🔥 DYNAMIC ROUTING RULES 🔥
        if priority.lower() == "critical":
            # For P1s: Pick whoever has the highest Skill Match -> Highest Expertise -> Lowest Workload
            team_members = team_members.sort_values(
                by=["Skill_Match_Score", "Expertise_Score", "Active_Tickets"], 
                ascending=[False, True, True] # False means descending (highest score first)
            )
        else:
            # For P3s: Pick whoever has the highest Skill Match -> Lowest Workload -> Lowest Expertise (Save experts!)
            team_members = team_members.sort_values(
                by=["Skill_Match_Score", "Active_Tickets", "Role_Score", "Expertise_Score"], 
                ascending=[False, True, True, False]
            )

        best_agent = team_members.iloc[0]

        # 5. Generate Context for the Manager's Email
        team_context =[
            f"{row['Name']} (Expertise: {row.get('Expertise_Level', 'N/A')}, Skills: {row.get('Primary_Skills', 'N/A')}) – {int(row['Active_Tickets'])} active tickets" 
            for _, row in team_members.iterrows()
        ]

        return {
            "suggested_agent_name":  str(best_agent["Name"]),
            "suggested_agent_email": str(best_agent["Email"]),
            "team":                  str(best_agent["Team"]),
            "manager_email":         str(best_agent["Manager_Email"]),
            "active_tickets":        int(best_agent["Active_Tickets"]),
            "expertise_level":       str(best_agent.get("Expertise_Level", "N/A")),
            "matched_skills":        str(best_agent.get("Primary_Skills", "N/A")),
            "team_workload_context": team_context
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}