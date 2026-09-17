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
import time
from datetime import datetime, timedelta
import google.auth
from google.auth.transport.requests import AuthorizedSession

def load_env_file(filepath=".env"):
    """Loads environment variables from a .env file if it exists.

    An unquoted value ends at an inline comment. The line
    `LOCATION=global # or us` therefore gives the value `global`.
    To keep a `#` inside a value, put the whole value in quotes.
    """
    if not os.path.isfile(filepath):
        return
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if value[:1] in ('"', "'"):
                # A quoted value ends at the matching quote. Every character
                # inside the quotes is kept, including a #.
                quote = value[0]
                end = value.find(quote, 1)
                value = value[1:end] if end > 0 else value[1:]
            elif value.startswith("#"):
                value = ""
            else:
                # An unquoted value ends at the first inline comment
                for marker in (" #", "\t#"):
                    if marker in value:
                        value = value.split(marker, 1)[0]
                value = value.strip()
            os.environ[key.strip()] = value

# Load environment from local .env file
load_env_file()





def list_engines(session, project_id, location, timeout=30):
    """Lists all engines in the project for a given location."""
    engines_url = f"https://{location}-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines"
    engines = []
    next_page_token = ""
    while True:
        params = {}
        if next_page_token:
            params["pageToken"] = next_page_token
        try:
            response = session.get(engines_url, params=params, timeout=timeout)
            if response.status_code in [403, 404]:
                # Report this. A silent break makes a wrong project ID, a missing
                # role and an empty location all look like "0 agents found".
                print(
                    f"Warning: cannot list engines in '{location}' (HTTP {response.status_code}). "
                    f"Check the project ID, the IAM roles, and that the Discovery Engine "
                    f"API is enabled.",
                    file=sys.stderr,
                )
                break
            if response.status_code != 200:
                print(
                    f"Warning: engine list failed in '{location}' "
                    f"(HTTP {response.status_code}): {response.text[:200]}",
                    file=sys.stderr,
                )
                break
            data = response.json()
            engines.extend(data.get("engines", []))
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        except Exception as e:
            print(f"Warning: engine list failed in '{location}': {e}", file=sys.stderr)
            break
    return engines

def list_agents(session, project_id, location, engine_id, timeout=30):
    """Lists all agents for a given engine."""
    agents_url = f"https://{location}-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant/agents"
    agents = []
    next_page_token = ""
    while True:
        params = {}
        if next_page_token:
            params["pageToken"] = next_page_token
        try:
            response = session.get(agents_url, params=params, timeout=timeout)
            if response.status_code != 200:
                print(
                    f"Warning: agent list failed for engine '{engine_id}' in '{location}' "
                    f"(HTTP {response.status_code}): {response.text[:200]}",
                    file=sys.stderr,
                )
                break
            data = response.json()
            agents.extend(data.get("agents", []))
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
        except Exception as e:
            print(
                f"Warning: agent list failed for engine '{engine_id}' in '{location}': {e}",
                file=sys.stderr,
            )
            break
    return agents

LOGGING_URL = "https://logging.googleapis.com/v2/entries:list"

# Number of log entries requested for each page.
LOG_PAGE_SIZE = 1000
# Stop the log scan after this many pages.
DEFAULT_MAX_LOG_PAGES = 200
# Stop the log scan after this many seconds.
DEFAULT_LOG_TIME_BUDGET = 300
# Number of attempts for one page when the server fails.
MAX_LOG_ATTEMPTS = 5
# Seconds to wait before the first retry. The wait doubles after each attempt.
FIRST_RETRY_DELAY = 2


def build_creator_log_filter(project_id, min_create_time=None):
    """Builds the Cloud Logging filter for CreateAgent audit entries.

    The filter names no agent ID, for two measured reasons. First, a clause on
    an agent ID is not indexed, so it does not reduce the bytes the backend
    reads. Second, it makes the result sparser, and a sparse result raises the
    risk of the backend error "timed out getting cursor token". The caller
    matches the agent IDs in Python instead.

    The logName and timestamp clauses use indexed fields. They let the backend
    skip whole storage blocks. They are the only real speed control here.
    """
    activity_log = f"projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity"
    clauses = [
        f'logName="{activity_log}"',
        'protoPayload.serviceName="discoveryengine.googleapis.com"',
        'protoPayload.methodName:"AgentService.CreateAgent"',
    ]

    # Add a timestamp bound to prevent long scans in large projects
    if min_create_time:
        try:
            # Parse creation time (e.g. 2026-08-01T12:34:56.789Z) and apply a 1-hour buffer
            main_part = min_create_time.rstrip("Z").split(".")[0]
            dt = datetime.strptime(main_part, "%Y-%m-%dT%H:%M:%S")
            dt_buffered = dt - timedelta(hours=1)
            timestamp_filter = dt_buffered.strftime("%Y-%m-%dT%H:%M:%SZ")
            clauses.append(f'timestamp >= "{timestamp_filter}"')
        except Exception as e:
            print(f"Warning: Could not parse min_create_time '{min_create_time}': {e}", file=sys.stderr)

    return " AND ".join(clauses)


def fetch_log_page(session, payload, timeout=30):
    """Sends one entries.list request and returns the parsed body.

    Retries on HTTP 5xx and on a network error, with an exponential wait. A
    Cloud Logging scan over a sparse result set can return HTTP 500 with the
    message "timed out getting cursor token". That error is transient.

    Returns None when the request failed for good.
    """
    delay = FIRST_RETRY_DELAY
    for attempt in range(1, MAX_LOG_ATTEMPTS + 1):
        try:
            response = session.post(LOGGING_URL, json=payload, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            if response.status_code < 500:
                # A client error will not improve on a retry
                print(
                    f"Error fetching logs (HTTP {response.status_code}): {response.text}",
                    file=sys.stderr,
                )
                return None
            error = f"HTTP {response.status_code}"
        except Exception as e:
            error = str(e)

        if attempt < MAX_LOG_ATTEMPTS:
            print(
                f"  Log request failed ({error}). Waiting {delay}s, "
                f"then attempt {attempt + 1} of {MAX_LOG_ATTEMPTS}...",
                file=sys.stderr,
            )
            time.sleep(delay)
            delay *= 2
        else:
            print(
                f"Error: log request failed after {MAX_LOG_ATTEMPTS} attempts. "
                f"Last error: {error}",
                file=sys.stderr,
            )
    return None


def get_agent_creators(session, project_id, agent_ids, min_create_time=None, timeout=30,
                       max_pages=DEFAULT_MAX_LOG_PAGES,
                       time_budget=DEFAULT_LOG_TIME_BUDGET):
    """Retrieves agent creator emails or identities from Cloud Audit Logs.

    The scan stops on the first of these conditions: every agent is resolved,
    the log history ends, the page limit is reached, or the time budget is
    spent. The last two guards matter because an agent created outside the
    400-day audit log retention never resolves. Without them the scan runs to
    the end of the time window.
    """
    if not agent_ids:
        return {}

    wanted_ids = set(agent_ids)
    creators = {}
    log_filter = build_creator_log_filter(project_id, min_create_time)

    started = time.monotonic()
    next_page_token = ""
    page_count = 0
    stop_reason = "the log history ended"

    while True:
        if page_count >= max_pages:
            stop_reason = f"the page limit of {max_pages} pages was reached"
            break
        if time.monotonic() - started >= time_budget:
            stop_reason = f"the time budget of {time_budget}s was spent"
            break

        payload = {
            "resourceNames": [f"projects/{project_id}"],
            "filter": log_filter,
            "pageSize": LOG_PAGE_SIZE,
            "orderBy": "timestamp desc"  # Scan newest logs first
        }
        if next_page_token:
            payload["pageToken"] = next_page_token

        data = fetch_log_page(session, payload, timeout=timeout)
        if data is None:
            stop_reason = "the log query failed"
            break

        page_count += 1
        for entry in data.get("entries", []):
            proto_payload = entry.get("protoPayload", {})
            # Only response.name carries the new agent ID. resourceName names the
            # parent assistant, so it never identifies the agent that was created.
            response_obj = proto_payload.get("response") or {}
            agent_name = response_obj.get("name", "")
            if not agent_name:
                continue
            auth_info = proto_payload.get("authenticationInfo", {})
            creator = extract_creator_identity(auth_info)
            if not creator:
                continue
            # Match by agent ID (last part of resource name path)
            agent_id = agent_name.split("/")[-1]
            if agent_id in wanted_ids and agent_id not in creators:
                creators[agent_id] = creator

        print(
            f"  Page {page_count}: resolved {len(creators)} of {len(wanted_ids)} agents "
            f"({time.monotonic() - started:.0f}s elapsed).",
            file=sys.stderr,
        )

        # Stop as soon as every agent ID has a creator
        if len(creators) >= len(wanted_ids):
            stop_reason = "every agent was resolved"
            break

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    print(
        f"Log scan stopped because {stop_reason}. "
        f"{len(creators)} resolved, {len(wanted_ids) - len(creators)} unresolved, "
        f"{page_count} pages, {time.monotonic() - started:.0f}s.",
        file=sys.stderr,
    )
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

# A location becomes part of a hostname, so only these characters are valid.
LOCATION_PATTERN = re.compile(r"^[a-z0-9-]+$")


def parse_locations(raw_value, source):
    """Splits a comma-separated location list and rejects an invalid entry.

    A location becomes part of the API hostname. An invalid value gives a DNS
    error that hides the real cause, so the script stops here instead.
    """
    locations = []
    for item in raw_value.split(","):
        location = item.strip()
        if not location:
            continue
        if not LOCATION_PATTERN.match(location):
            print(
                f"Error: '{location}' from {source} is not a valid location.",
                file=sys.stderr,
            )
            print(
                "A location uses lower case letters, digits and hyphens only, "
                "for example 'global' or 'us'.",
                file=sys.stderr,
            )
            print(
                "Check for an inline comment or a stray space. Write the comment "
                "on its own line.",
                file=sys.stderr,
            )
            sys.exit(1)
        locations.append(location)
    if not locations:
        print(f"Error: {source} holds no location.", file=sys.stderr)
        sys.exit(1)
    return locations


def main():
    parser = argparse.ArgumentParser(description="List Gemini Enterprise agents and their creator emails.")
    parser.add_argument("--project_id", help="Google Cloud Project ID. Defaults to detecting from environment.")
    parser.add_argument("--format", choices=["table", "csv"], default="table", help="Output format (default: table).")
    parser.add_argument("--location", help="Comma-separated list of GCP locations to scan. Overrides default/env.")
    parser.add_argument("--output_uuids", default="unresolved_uuids.txt", help="Path to write unresolved WIF user UUIDs (default: unresolved_uuids.txt).")
    parser.add_argument("--log_max_pages", type=int, default=DEFAULT_MAX_LOG_PAGES,
                        help=f"Maximum Cloud Logging pages to read when resolving creators (default: {DEFAULT_MAX_LOG_PAGES}).")
    parser.add_argument("--log_time_budget", type=int, default=DEFAULT_LOG_TIME_BUDGET,
                        help=f"Maximum seconds to spend resolving creators from logs (default: {DEFAULT_LOG_TIME_BUDGET}).")
    args = parser.parse_args()

    # Determine locations to scan
    if args.location:
        locations = parse_locations(args.location, "the --location flag")
    else:
        env_locations = os.getenv("LOCATION") or os.getenv("LOCATIONS")
        if env_locations:
            locations = parse_locations(env_locations, "LOCATION in the .env file")
        else:
            locations = ["global", "us", "eu"]  # Broader default to scan common locations

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
    unresolved_agent_create_times = []
    
    for loc in locations:
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
                    if agent.get("createTime"):
                        unresolved_agent_create_times.append(agent.get("createTime"))

    # 2. Resolve creator emails from Cloud Audit Logs for unresolved agents
    print(f"Found {len(all_agents_info)} no-code/low-code agents.", file=sys.stderr)
    if unresolved_agent_ids:
        print(f"Resolving {len(unresolved_agent_ids)} creator emails from Cloud Audit Logs...", file=sys.stderr)
        min_create_time = min(unresolved_agent_create_times) if unresolved_agent_create_times else None
        creators_map = get_agent_creators(
            session,
            project_id,
            unresolved_agent_ids,
            min_create_time=min_create_time,
            max_pages=args.log_max_pages,
            time_budget=args.log_time_budget,
        )
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
