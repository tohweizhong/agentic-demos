#!/usr/bin/env python3
"""
Script to list all Gemini Enterprise (Discovery Engine) no-code agents and their creators.
Designed for Workforce Identity Federation (WIF) setups: scans the "us" location and extracts WIF subject IDs / user UUIDs (instead of emails) from audit logs and definitions.
Combines fast payload metadata extraction with targeted Cloud Audit Log lookups.
"""


import argparse
import csv
import sys
import os
from datetime import datetime
import google.auth
from google.auth.transport.requests import AuthorizedSession

def load_env_file(filepath=".env"):
    """Loads environment variables from a .env file if it exists."""
    if os.path.isfile(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Load environment from local .env file
load_env_file()

# Locations to scan (can be overridden by LOCATION or LOCATIONS env var)
env_locations = os.getenv("LOCATION") or os.getenv("LOCATIONS")
if env_locations:
    LOCATIONS = [loc.strip() for loc in env_locations.split(",") if loc.strip()]
else:
    LOCATIONS = ["global"]



def list_engines(session, project_id, location):
    """Lists all engines in the project for a given location."""
    engines_url = f"https://{location}-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines"
    engines = []
    next_page_token = ""
    while True:
        params = {}
        if next_page_token:
            params["pageToken"] = next_page_token
        try:
            response = session.get(engines_url, params=params)
            if response.status_code in [403, 404]:
                break
            if response.status_code != 200:
                break
            data = response.json()
            engines.extend(data.get("engines", []))
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        except Exception:
            break
    return engines

def list_agents(session, project_id, location, engine_id):
    """Lists all agents for a given engine."""
    agents_url = f"https://{location}-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant/agents"
    agents = []
    next_page_token = ""
    while True:
        params = {}
        if next_page_token:
            params["pageToken"] = next_page_token
        try:
            response = session.get(agents_url, params=params)
            if response.status_code != 200:
                break
            data = response.json()
            agents.extend(data.get("agents", []))
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        except Exception:
            break
    return agents

def extract_creator_identity(auth_info):
    """Extracts the best identification string for the creator from authenticationInfo (supports WIF)."""
    email = auth_info.get("principalEmail")
    if email:
        return email
        
    subject = auth_info.get("principalSubject")
    if subject:
        # If it's a workforce pool federated identity:
        # e.g., principal://iam.googleapis.com/locations/global/workforcePools/pool-id/subject/user-id
        if subject.startswith("principal://"):
            parts = subject.split("/")
            if len(parts) > 0:
                return parts[-1]
        # If it's a service account identity:
        # e.g., serviceAccount:email@project.iam.gserviceaccount.com
        elif subject.startswith("serviceAccount:"):
            return subject.split(":")[-1]
        return subject
    return None

def get_agent_creators(session, project_id, agent_ids):
    """Retrieves agent creator emails or identities from Cloud Audit Logs for specific agent IDs."""
    if not agent_ids:
        return {}

    logging_url = "https://logging.googleapis.com/v2/entries:list"
    creators = {}
    
    # Construct targeted filter matching only the unresolved agent IDs
    id_filter_str = " OR ".join(f'"{aid}"' for aid in agent_ids)
    log_filter = (
        'protoPayload.serviceName="discoveryengine.googleapis.com" AND '
        'protoPayload.methodName:"AgentService.CreateAgent" AND '
        f'(protoPayload.response.name:({id_filter_str}) OR protoPayload.resourceName:({id_filter_str}))'
    )

    next_page_token = ""
    while True:
        payload = {
            "resourceNames": [f"projects/{project_id}"],
            "filter": log_filter,
            "pageSize": 1000
        }
        if next_page_token:
            payload["pageToken"] = next_page_token
        try:
            response = session.post(logging_url, json=payload)
            if response.status_code != 200:
                print(f"Error fetching logs (HTTP {response.status_code}): {response.text}", file=sys.stderr)
                break
            data = response.json()
            entries = data.get("entries", [])
            for entry in entries:
                proto_payload = entry.get("protoPayload", {})
                response_obj = proto_payload.get("response", {})
                agent_name = response_obj.get("name") if response_obj else None
                if not agent_name:
                    agent_name = proto_payload.get("resourceName", "")
                auth_info = proto_payload.get("authenticationInfo", {})
                creator = extract_creator_identity(auth_info)
                if agent_name and creator:
                    # Match by agent ID (last part of resource name path)
                    agent_id = agent_name.split("/")[-1]
                    if agent_id and agent_id != "default_assistant" and agent_id not in creators:
                        creators[agent_id] = creator
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        except Exception as e:
            print(f"Exception while fetching logs: {e}", file=sys.stderr)
            break
    return creators

def get_agent_type(agent):
    """Determines the type of the agent based on its definition field."""
    if "adkAgentDefinition" in agent:
        return "ADK"
    elif "a2aAgentDefinition" in agent:
        return "A2A"
    elif "managedAgentDefinition" in agent:
        return "Managed (1P)"
    elif "lowCodeAgentDefinition" in agent:
        return "Low-Code"
    elif "noCodeAgentDefinition" in agent:
        return "No-Code"
    elif "workflowAgentDefinition" in agent:
        return "Workflow"
    elif "skillAgentDefinition" in agent:
        return "Skill"
    elif "agentDesignerAgentDefinition" in agent:
        return "Agent Designer"
    elif "dialogflowAgentDefinition" in agent:
        return "Dialogflow"
    elif "iframeAgentDefinition" in agent:
        return "Iframe"
    elif "httpAgentDefinition" in agent:
        return "HTTP"
    elif "appAgentDefinition" in agent:
        return "App"
    elif "longRunningAgentDefinition" in agent:
        return "Long-Running"
    else:
        return "Unknown"

def get_payload_email(agent, agent_type):
    """Retrieves creator email directly from agent definition if available."""
    payload_author = None
    if agent_type == "Low-Code" and "lowCodeAgentDefinition" in agent:
        payload_author = agent["lowCodeAgentDefinition"].get("ownerName")
    elif agent_type == "Agent Designer" and "agentDesignerAgentDefinition" in agent:
        chat_def = agent["agentDesignerAgentDefinition"].get("chatAgentDefinition", {})
        payload_author = chat_def.get("owner")
    elif agent_type == "Workflow" and "workflowAgentDefinition" in agent:
        payload_author = agent["workflowAgentDefinition"].get("owner")
    elif agent_type == "Skill" and "skillAgentDefinition" in agent:
        payload_author = agent["skillAgentDefinition"].get("owner")
    elif agent_type == "No-Code" and "noCodeAgentDefinition" in agent:
        payload_author = agent["noCodeAgentDefinition"].get("owner")

    # Return if it is present and not a SPIFFE ID (allow non-emails like WIF UUIDs)
    if payload_author and not payload_author.startswith("SPIFFE"):
        return payload_author
    return None

def format_datetime(dt_str):
    """Formats ISO 8601 datetime string to YYYY-MM-DD HH:MM:SS format."""
    if not dt_str or dt_str == "N/A":
        return "N/A"
    try:
        main_part = dt_str.rstrip("Z").split(".")[0]
        dt = datetime.strptime(main_part, "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str

def main():
    parser = argparse.ArgumentParser(description="List Gemini Enterprise agents and their creator emails.")
    parser.add_argument("--project_id", help="Google Cloud Project ID. Defaults to detecting from environment.")
    parser.add_argument("--format", choices=["table", "csv"], default="table", help="Output format (default: table).")
    parser.add_argument("--output_uuids", default="unresolved_uuids.txt", help="Path to write unresolved WIF user UUIDs (default: unresolved_uuids.txt).")
    args = parser.parse_args()

    # Authenticate and detect project
    try:
        credentials, auto_project_id = google.auth.default()
        session = AuthorizedSession(credentials)
    except Exception as e:
        print(f"Authentication Error: {e}", file=sys.stderr)
        print("Please run 'gcloud auth application-default login' first.", file=sys.stderr)
        sys.exit(1)

    project_id = args.project_id or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID") or auto_project_id
    if not project_id:
        print("Error: Project ID could not be detected. Please specify using --project_id <PROJECT_ID>.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning project: {project_id} ...", file=sys.stderr)
    
    # 1. Scan locations for engines and agents
    all_agents_info = []
    unresolved_agent_ids = []
    
    for loc in LOCATIONS:
        print(f"Scanning location: {loc} ...", file=sys.stderr)
        engines = list_engines(session, project_id, loc)
        for engine in engines:
            engine_name = engine.get("name", "")
            engine_id = engine_name.split("/")[-1]
            agents = list_agents(session, project_id, loc, engine_id)
            for agent in agents:
                agent_name = agent.get("name", "")
                agent_id = agent_name.split("/")[-1]
                
                # Check if it's code-based or no-code
                agent_type = get_agent_type(agent)
                
                # Exclude ADK, A2A, Managed (1P), and other developer/integration agents
                allowed_types = ["Low-Code", "No-Code", "Workflow", "Agent Designer"]
                if agent_type not in allowed_types:
                    continue
                
                # Try to get creator email from payload first
                creator = get_payload_email(agent, agent_type)
                
                agent_info = {
                    "agent_id": agent_id,
                    "display_name": agent.get("displayName", ""),
                    "description": agent.get("description", ""),
                    "type": agent_type,
                    "engine_id": engine_id,
                    "location": loc,
                    "creator": creator,
                    "create_time": format_datetime(agent.get("createTime", "N/A"))
                }
                
                all_agents_info.append(agent_info)
                
                if not creator:
                    unresolved_agent_ids.append(agent_id)

    # 2. Resolve creator emails from Cloud Audit Logs for unresolved agents
    print(f"Found {len(all_agents_info)} no-code/low-code agents.", file=sys.stderr)
    if unresolved_agent_ids:
        print(f"Resolving {len(unresolved_agent_ids)} creator emails from Cloud Audit Logs...", file=sys.stderr)
        creators_map = get_agent_creators(session, project_id, unresolved_agent_ids)
        for info in all_agents_info:
            if not info["creator"]:
                info["creator"] = creators_map.get(info["agent_id"], "N/A (No log entry found)")
    else:
        print("All creator emails resolved from agent definitions. Skipping Cloud Logging query.", file=sys.stderr)

    # 3. Output results
    if not all_agents_info:
        print("No no-code agents found.", file=sys.stderr)
        return

    if args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=["agent_id", "display_name", "description", "type", "engine_id", "location", "creator", "create_time"])
        writer.writeheader()
        for info in all_agents_info:
            writer.writerow(info)
    else:
        # Table format
        template = "{:<22} | {:<30} | {:<50} | {:<25} | {:<30}"
        print(template.format("Agent ID", "Agent Name", "Description", "Create Time", "Creator Email"))
        print("-" * 170)
        for info in all_agents_info:
            desc = info["description"]
            if len(desc) > 47:
                desc = desc[:44] + "..."
            print(template.format(
                info["agent_id"],
                info["display_name"],
                desc,
                info["create_time"],
                info["creator"]
            ))

    # 4. Write unique WIF UUIDs to be resolved to a text file
    import re
    uuid_pattern = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    uuids_to_resolve = set()
    for info in all_agents_info:
        creator = info["creator"]
        if creator and uuid_pattern.match(creator):
            uuids_to_resolve.add(creator)
            
    if uuids_to_resolve:
        try:
            with open(args.output_uuids, "w") as f:
                for uuid in sorted(uuids_to_resolve):
                    f.write(f"{uuid}\n")
            print(f"\nWrote {len(uuids_to_resolve)} unresolved WIF user UUIDs to {args.output_uuids}", file=sys.stderr)
        except Exception as e:
            print(f"\nError writing UUIDs to file: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
