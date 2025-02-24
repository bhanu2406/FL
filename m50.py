
import requests
import pandas as pd
import re
import datetime
from requests.auth import HTTPBasicAuth
from jira import JIRA
from github import Github

# Jira Credentials
JIRA_SERVER = "https://batchubhanu2406.atlassian.net"
JIRA_USER = "batchubhanu2406@gmail.com"
JIRA_API_TOKEN = "ATATT3xFfGF0OznpKAE6qOIsqg2-TpuScWuEo32Vn6GtByQfQ9PHs-7nU07e4CAEFE-u-VecQQW6pAKoqh7ZOdfKfybvfwykFiihAQaYoxIcCZudXh4QGRt2DShUmEc9PnL8joOOjVw9gdMzr98OR4cDUAs4c0faxqCG025e3RBsT1ui4DicfTw=7C4145EF"


# GitHub Token
GITHUB_TOKEN = ""
g = Github(GITHUB_TOKEN)

# File Paths
EXCEL_FILE_PATH = "Team_mapping_ids.xlsx"

# Jira Filters
FILTER_ID_1 = "10006"  # For Epics
FILTER_ID_3 = "10007"  # For Tickets
CUSTOM_FIELD_ID = "customfield_10001"  # Field for Team Assignment

def get_tickets_from_filter(filter_id):
    """Retrieve Jira issues from a filter."""
    url = f"{JIRA_SERVER}/rest/api/3/filter/{filter_id}"
    auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        jql_query = response.json().get("jql", "")
        search_url = f"{JIRA_SERVER}/rest/api/3/search"
        params = {"jql": jql_query, "maxResults": 100}
        search_response = requests.get(search_url, auth=auth, params=params)
        if search_response.status_code == 200:
            return search_response.json().get("issues", [])
    return []

def get_ticket_details(ticket_key):
    """Retrieve details (fields) of a specific Jira ticket."""
    url = f"{JIRA_SERVER}/rest/api/3/issue/{ticket_key}"
    response = requests.get(url, auth=HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN))
    if response.status_code == 200:
        return response.json().get("fields", {})
    return {}

def assign_epic_to_ticket(epic_key, ticket_key):
    """Assign a ticket to an epic as its parent."""
    url = f"{JIRA_SERVER}/rest/api/3/issue/{ticket_key}"
    payload = {
        "fields": {
            "parent": {
                "key": epic_key
            }
        }
    }
    response = requests.put(
        url,
        json=payload,
        auth=HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN),
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 204:
        print(f"{ticket_key}: Successfully assigned parent {epic_key}")
        return True
    else:
        print(f"{ticket_key}: Failed to assign parent {epic_key}: {response.status_code} {response.text}")
        return False

def get_team_id_from_excel(team_name, excel_file):
    """Look up a team ID from an Excel file by team name."""
    try:
        if "/" in team_name:
            team_name = team_name.split("/")[1].strip()
        data = pd.read_excel(excel_file)
        data.columns = data.columns.str.strip()
        row = data[data['Team Name'].str.strip().str.lower() == team_name.strip().lower()]
        if not row.empty:
            return row["Team ID's"].values[0]
        else:
            print(f"Team name '{team_name}' not found in the Excel file.")
            return None
    except Exception as e:
        print(f"An error occurred while reading the Excel file: {e}")
        return None

def gather_all_urls_from_jira_doc(content_block):
    """Recursively traverse the Atlassian 'doc' format to find all possible URLs."""
    found_urls = []
    if isinstance(content_block, list):
        for item in content_block:
            found_urls.extend(gather_all_urls_from_jira_doc(item))
    elif isinstance(content_block, dict):
        block_type = content_block.get("type")
        if block_type == "inlineCard":
            maybe_url = content_block.get("attrs", {}).get("url", "")
            if maybe_url:
                found_urls.append(maybe_url)
        elif block_type == "link":
            maybe_url = content_block.get("attrs", {}).get("href", "")
            if maybe_url:
                found_urls.append(maybe_url)
        elif block_type == "text":
            text_content = content_block.get("text", "")
            pattern = r"https?://github\.com/[^\s\)]+"
            matches = re.findall(pattern, text_content)
            found_urls.extend(matches)

            marks = content_block.get("marks", [])
            for mark in marks:
                if mark.get("type") == "link":
                    href = mark.get("attrs", {}).get("href", "")
                    if href:
                        found_urls.append(href)

        if "content" in content_block:
            found_urls.extend(gather_all_urls_from_jira_doc(content_block["content"]))
    return found_urls

def extract_github_url(description, company_name):
    """
    Extract the last GitHub URL that starts with the given company name.
    """
    pattern = r"(?:\[[^\]]*\]\()?(https?://github\.com/[^\s\)]+)(?:\))?"
    all_urls = []

    # If description is a plain string
    if isinstance(description, str):
        matches = re.findall(pattern, description)
        all_urls.extend(matches)
    # If description is a dict (Atlassian doc format)
    elif isinstance(description, dict):
        all_urls.extend(gather_all_urls_from_jira_doc(description.get("content", [])))

    prefix = f"https://github.com/{company_name}"
    filtered_urls = [url for url in all_urls if url.startswith(prefix)]
    if not filtered_urls:
        print("No GitHub URL found! (Description might be formatted differently)")
        return None
    return filtered_urls[-1]

def get_repo_name(github_url):
    """Extract 'owner/repo' from a GitHub URL."""
    try:
        repo_path = github_url.split("github.com/")[1]
        repo_parts = repo_path.split("/")
        if len(repo_parts) >= 2:
            repo_full_name = f"{repo_parts[0]}/{repo_parts[1]}"
            print(f"Extracted Repo Full Name: {repo_full_name}")
            return repo_full_name
        else:
            print(f"Invalid GitHub URL format: {github_url}")
            return None
    except Exception as e:
        print(f"Error extracting repo name: {e}")
        return None

def fetch_codeowners_file(github_url):
    """Try to fetch a CODEOWNERS file from known locations in the GitHub repo."""
    repo_name = get_repo_name(github_url)
    if not repo_name:
        return None
    try:
        repo = g.get_repo(repo_name)
        for location in ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"]:
            try:
                content = repo.get_contents(location)
                return content.decoded_content.decode()
            except Exception:
                continue
    except Exception as e:
        print(f"Error fetching CODEOWNERS file: {e}")
    return None

def parse_codeowners(content):
    """Parse the CODEOWNERS file to extract team or user owners."""
    owners_set = set()
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            parts = line.split()
            if "*" in parts:
                owners = [
                    owner.rsplit("/", 1)[-1].lstrip('@').replace('-', ' ')
                    for owner in parts[1:]
                    if owner != '*'
                ]
                owners_set.update(owners)
    return list(owners_set)

def assign_team_to_ticket(ticket_id, team_id):
    """Assign a team (by team_id) to a Jira ticket."""
    url = f"{JIRA_SERVER}/rest/api/3/issue/{ticket_id}"
    payload = {"fields": {CUSTOM_FIELD_ID: team_id}}
    response = requests.put(
        url,
        json=payload,
        auth=HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN),
        headers={"Content-Type": "application/json"}
    )
    return response.status_code == 204

def set_due_date(ticket_key, days_from_now=15):
    """Set the due date of a Jira ticket to `days_from_now` days from today."""
    due_date_str = (datetime.datetime.now() + datetime.timedelta(days=days_from_now)).strftime('%Y-%m-%d')
    url = f"{JIRA_SERVER}/rest/api/3/issue/{ticket_key}"
    payload = {
        "fields": {
            "duedate": due_date_str
        }
    }
    response = requests.put(
        url,
        json=payload,
        auth=HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN),
        headers={"Content-Type": "application/json"}
    )
    if response.status_code == 204:
        print(f"{ticket_key}: Due date set to {due_date_str}")
    else:
        print(f"{ticket_key}: Failed to set due date: {response.status_code} {response.text}")

def process_tickets():
    """Main workflow:
       1. Retrieve epics & tickets
       2. Assign epic if ticket has no parent
       3. Assign team if not already assigned
       4. Only set due date if the ticket has no parent
    """
    epics = get_tickets_from_filter(FILTER_ID_1)
    latest_epic = max(epics, key=lambda e: e["fields"]["created"], default=None)
    tickets = get_tickets_from_filter(FILTER_ID_3)

    for ticket in tickets:
        ticket_key = ticket["key"]
        details = get_ticket_details(ticket_key)
        parent = details.get("parent")

        # 1) Assign epic if no parent
        if not parent and latest_epic:
            assign_epic_to_ticket(latest_epic["key"], ticket_key)
        else:
            if parent:
                print(f"{ticket_key}: Parent is already assigned -> {parent.get('key')}")

        # 2) Assign team if not already assigned
        team_assigned = details.get(CUSTOM_FIELD_ID)
        if not team_assigned:
            description = details.get("description", "")
            github_url = extract_github_url(description, "bhanu2406")  # Adjust org if needed
            if github_url:
                codeowners_content = fetch_codeowners_file(github_url)
                if codeowners_content:
                    owners = parse_codeowners(codeowners_content)
                    if owners:
                        team_name = owners[0]
                        team_id = get_team_id_from_excel(team_name, EXCEL_FILE_PATH)
                        if team_id:
                            success_team = assign_team_to_ticket(ticket_key, team_id)
                            if success_team:
                                print(f"{ticket_key}: Team Assigned Successfully -> {team_name}")
                            else:
                                print(f"{ticket_key}: Failed to assign team -> {team_name}")
                    else:
                        print(f"{ticket_key}: No owners found in CODEOWNERS, skipping team assignment.")
                else:
                    print(f"{ticket_key}: No CODEOWNERS file found, skipping team assignment.")
            else:
                print(f"ERROR: {ticket_key} - No GitHub URL found! (Description might be formatted differently)")
        else:
            print(f"{ticket_key}: Team already assigned, skipping team assignment.")

        # 3) Only set due date if ticket has NO parent
        if not parent:
            set_due_date(ticket_key, 15)
        else:
            print(f"{ticket_key}: Skipping due date because parent is already assigned.")

if __name__ == "__main__":
    process_tickets()
