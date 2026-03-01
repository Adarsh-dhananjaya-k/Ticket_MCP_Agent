import pandas as pd

def find_best_assignee(issue_description: str) -> str:
    """
    Analyzes the description to find the correct Team, 
    then checks the Roster to find the member with the LOWEST workload.
    """
    try:
        # Load Data
        df_map = pd.read_excel("data/teams_mapping.xlsx")
        df_roster = pd.read_excel("data/roster.xlsx")
        
        # 1. Determine Team based on Keywords
        desc_lower = issue_description.lower()
        target_team = "General_Support" # Default
        
        for index, row in df_map.iterrows():
            if row['Keyword'] in desc_lower:
                target_team = row['Target_Team']
                break
        
        print(f"📊 [Roster] Map '{issue_description}' -> Team: {target_team}")

        # 2. Filter Roster by Team
        team_members = df_roster[df_roster['Team'] == target_team]
        
        if team_members.empty:
            return "helpdesk@demo.com" # Fallback

        # 3. Sort by Workload (Low=1, Medium=2, High=3)
        workload_map = {"Low": 1, "Medium": 2, "High": 3}
        # Create a temporary column for sorting
        team_members = team_members.copy()
        team_members['Load_Score'] = team_members['Workload'].map(workload_map)
        
        # Get the person with min score
        best_agent = team_members.sort_values('Load_Score').iloc[0]
        
        return best_agent['Email']

    except Exception as e:
        return f"Error finding assignee: {str(e)}"