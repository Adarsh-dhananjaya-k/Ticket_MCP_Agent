import pandas as pd
import re
import traceback
from . import servicenow as sn # Import ServiceNow tools

DEFAULT_MANAGER_EMAIL = "softmgr@demo.com"
DEFAULT_MANAGER_NAME = "Support Manager"

_df_map = None
_df_roster = None

# Role and workload priority
ROLE_PRIORITY = {"L1": 1, "L2": 2, "L3": 3}
WORKLOAD_ORDER = {"Low": 1, "Medium": 2, "High": 3}

def _load_data():
    """Load and normalize Excel data."""
    global _df_map, _df_roster
    if _df_map is None or _df_roster is None:
        try:
            _df_map = pd.read_excel("data/teams_mapping.xlsx")
            _df_roster = pd.read_excel("data/roster.xlsx")
            
            # Normalize strings to avoid mismatch issues
            _df_map["Keyword"] = _df_map["Keyword"].astype(str).str.lower().str.strip()
            _df_map["Target_Team"] = _df_map["Target_Team"].astype(str).str.lower().str.strip()
            if "Manager_Email" in _df_map.columns:
                _df_map["Manager_Email"] = _df_map["Manager_Email"].astype(str).str.lower().str.strip()
            
            _df_roster["Team"] = _df_roster["Team"].astype(str).str.lower().str.strip()
            if "Assignment_Group" not in _df_roster.columns:
                _df_roster["Assignment_Group"] = _df_roster["Team"]
            _df_roster["Assignment_Group"] = _df_roster["Assignment_Group"].astype(str).str.strip()
            _df_roster["Role"] = _df_roster["Role"].astype(str).str.upper().str.strip()
            _df_roster["Workload"] = _df_roster["Workload"].astype(str).str.capitalize().str.strip()
        except Exception as e:
            print(f"❌ Error loading Excel files: {e}")
            raise e

def find_best_assignee(issue_description: str) -> dict:
    """
    Return JSON/dict with agent info for MCP tool.
    Guarantees a valid return structure even if no match is found.
    """
    try:
        _load_data()
        df_map = _df_map.copy()
        df_roster = _df_roster.copy()
        desc_lower = issue_description.lower()

        matched_teams = []

        # 1. KEYWORD MATCHING (USING MAPPING EXCEL)
        # Still use Excel for initial intent-to-team mapping
        target_team_name = None
        for _, row in df_map.iterrows():
            keywords = [kw.strip() for kw in str(row["Keyword"]).split(",") if kw.strip()]
            for kw in keywords:
                if kw in desc_lower:
                    matched_teams.append(str(row["Target_Team"]))

        if not matched_teams:
            target_team_name = "Service Desk" # Default common ServiceNow group
        else:
            target_team_name = max(set(matched_teams), key=matched_teams.count)

        print(f"🔍 Dynamic Lookup: Searching ServiceNow for Group '{target_team_name}'...")

        # 2. FETCH DATA FROM SERVICENOW
        group_id = sn.get_sysid_by_query("sys_user_group", f"name={target_team_name}")
        
        # Fuzzy match if exact name fails
        if not group_id:
            all_groups = sn.get_all_groups()
            for g in all_groups:
                if target_team_name.lower() in str(g.get("name", "")).lower():
                    group_id = g["sys_id"]
                    target_team_name = g["name"]
                    break

        # 3. GET TEAM MEMBERS (Real-time)
        members = []
        if group_id:
            members = sn.get_group_members(group_id)
            print(f"✅ Found {len(members)} specialists in ServiceNow group '{target_team_name}'")

        # 4. FALLBACK TO EXCEL (If ServiceNow unreachable or group empty)
        if not members:
            print("⚠️ Group not found in ServiceNow. Using Excel Roster fallback.")
            team_members = df_roster[df_roster["Team"].str.lower() == target_team_name.lower()].copy()
            if team_members.empty:
                # Last resort: take any agent
                team_members = df_roster.copy()
            
            for _, m in team_members.iterrows():
                members.append({
                    "name": str(m["Name"]),
                    "email": str(m["Email"]),
                    "manager_name": str(m.get("Manager", DEFAULT_MANAGER_NAME)),
                    "manager_email": str(m.get("Manager_Email", DEFAULT_MANAGER_EMAIL)),
                    "assignment_group": str(m.get("Assignment_Group", target_team_name))
                })

        def _roster_match(email: str):
            if not email:
                return None
            match = df_roster[df_roster["Email"].str.lower() == str(email).lower()]
            if match.empty:
                return None
            return match.iloc[0]

        def _member_sort_key(member: dict):
            roster_row = _roster_match(member.get("email"))
            workload_rank = WORKLOAD_ORDER.get(str(roster_row["Workload"]).capitalize(), 50) if roster_row is not None else 50
            role_rank = ROLE_PRIORITY.get(str(roster_row["Role"]).upper(), 50) if roster_row is not None else 50
            return (workload_rank, role_rank)

        # 5. SELECT BEST AGENT (prefer Excel workload/role ordering when available)
        members.sort(key=_member_sort_key)
        selected = members[0]
        assignment_group_name = str(selected.get("assignment_group", target_team_name))
        assignment_group_sys_id = group_id

        # Override manager if specified in the mapping file
        manager_email = (selected.get("manager_email") or "").strip()
        manager_name = selected.get("manager_name") or DEFAULT_MANAGER_NAME
        roster_row = _roster_match(selected.get("email"))
        if roster_row is not None:
            if not manager_name or manager_name == DEFAULT_MANAGER_NAME:
                manager_name = str(roster_row.get("Manager", DEFAULT_MANAGER_NAME))
            roster_mgr = str(roster_row.get("Manager_Email", "")).strip()
            if roster_mgr:
                manager_email = roster_mgr
            if not selected.get("name"):
                selected["name"] = str(roster_row.get("Name", selected.get("name")))
            roster_group = str(roster_row.get("Assignment_Group", "")).strip()
            if roster_group:
                assignment_group_name = roster_group

        map_match = df_map[df_map["Target_Team"].str.lower() == target_team_name.lower()]
        if not map_match.empty:
            override_mgr = str(map_match.iloc[0].get("Manager_Email", ""))
            if override_mgr and override_mgr != "nan":
                manager_email = override_mgr

        if not manager_email:
            manager_email = DEFAULT_MANAGER_EMAIL

        # 6. RETURN
        return {
            "agent_name":    str(selected.get("name")),
            "agent_email":   str(selected.get("email")),
            "team":          target_team_name,
            "assignment_group": assignment_group_name,
            "assignment_group_sys_id": assignment_group_sys_id,
            "manager_name":  str(manager_name),
            "manager_email": manager_email,
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "error": str(e),
            "agent_email": "error_fallback@demo.com",
            "manager_email": "manager_fallback@demo.com"
        }
