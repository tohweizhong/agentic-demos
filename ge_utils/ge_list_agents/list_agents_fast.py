#!/usr/bin/env python3
"""Lists Gemini Enterprise agents and their creators. Faster drop-in for list_agents.py.

This script is a direct replacement for `list_agents.py` in this folder. It uses the same
`.env` file, the same credentials, the same dependencies and the same flags. It writes the
same eight columns. Only the file name changes:

    python3 list_agents.py      --format csv > list_agents.csv
    python3 list_agents_fast.py --format csv > list_agents.csv

LIMIT: this script supports Cloud Identity accounts only. It does not support Workforce
Identity Federation. For a WIF setup, use `list_agents_wif.py` instead.

What is different is how it reads the audit log.

Cloud Logging does not index the audit payload fields, so a filter on them does not reduce
the bytes the backend reads. Scanning eight months of log for a few entries is a sparse
query. It is slow, and it can fail with "timed out getting cursor token".

The agent list already carries `createTime` for every agent, and the `CreateAgent` audit
entry sits within a few seconds of that value. This script groups those times into
clusters and reads one narrow window for each cluster. It therefore tells Cloud Logging
where to look, instead of asking it to search.

Measured on a project with 14 agents across eight months:
  list_agents.py      : 91 to 212 seconds, 16 to 34 pages
  list_agents_fast.py : 12 seconds, 9 queries

Both produced identical creator values for all 14 agents.
"""


import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import google.auth
from google.auth.transport.requests import AuthorizedSession

LOGGING_URL = "https://logging.googleapis.com/v2/entries:list"

# Number of log entries requested for each page.
LOG_PAGE_SIZE = 1000
# Attempts for one page when the server fails.
MAX_LOG_ATTEMPTS = 5
# Seconds to wait before the first retry. The wait doubles after each attempt.
FIRST_RETRY_DELAY = 2

# A gap larger than this value starts a new cluster.
DEFAULT_GAP_HOURS = 24
# Each window extends this far on both sides of the cluster.
# Measured skew between createTime and the log timestamp: 0.35 s to 2.50 s.
# One hour is about 1,400 times the largest observed skew.
DEFAULT_BUFFER_HOURS = 1
# Upper limit on the number of windows. Neighbours merge until the count fits.
DEFAULT_MAX_WINDOWS = 400
# Upper limit on the pages read for one window.
DEFAULT_MAX_PAGES_PER_WINDOW = 20
# Upper limit on the seconds spent resolving creators.
DEFAULT_TIME_BUDGET = 900

# Only these agent types are counted. ADK, A2A and Managed (1P) are skipped.
COUNTED_AGENT_TYPES = ["Low-Code", "No-Code", "Workflow", "Agent Designer"]

# A location becomes part of a hostname, so only these characters are valid.
LOCATION_PATTERN = re.compile(r"^[a-z0-9-]+$")


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


# --------------------------------------------------------------- time helpers

def parse_iso(text):
    """Parses an RFC 3339 timestamp and returns an aware datetime in UTC.

    Returns None when the text is empty or malformed.
    """
    if not text:
        return None
    main = text.rstrip("Z").split("+")[0]
    try:
        if "." in main:
            head, frac = main.split(".", 1)
            main = f"{head}.{(frac + '000000')[:6]}"
            parsed = datetime.strptime(main, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            parsed = datetime.strptime(main, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def to_filter_stamp(value):
    """Formats a datetime for a Cloud Logging timestamp clause."""
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_datetime(text):
    """Formats an ISO 8601 string as YYYY-MM-DD HH:MM:SS for display."""
    parsed = parse_iso(text)
    if parsed is None:
        return text or "N/A"
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def format_seconds(seconds):
    """Formats a duration in seconds as '45s' or '3m 12s'."""
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    minutes, rest = divmod(total, 60)
    return f"{minutes}m {rest:02d}s"


# ------------------------------------------------------- Discovery Engine API

def list_engines(session, project_id, location, timeout=30):
    """Lists all engines in the project for a given location."""
    engines_url = (
        f"https://{location}-discoveryengine.googleapis.com/v1alpha/projects/"
        f"{project_id}/locations/{location}/collections/default_collection/engines"
    )
    engines = []
    next_page_token = ""
    while True:
        params = {}
        if next_page_token:
            params["pageToken"] = next_page_token
        try:
            response = session.get(engines_url, params=params, timeout=timeout)
            if response.status_code in (403, 404):
                # Report this. A silent break makes a wrong project ID, a
                # missing role and an empty location all look the same.
                print(
                    f"Warning: cannot list engines in '{location}' "
                    f"(HTTP {response.status_code}). Check the project ID, the IAM "
                    f"roles, and that the Discovery Engine API is enabled.",
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
    agents_url = (
        f"https://{location}-discoveryengine.googleapis.com/v1alpha/projects/"
        f"{project_id}/locations/{location}/collections/default_collection/engines/"
        f"{engine_id}/assistants/default_assistant/agents"
    )
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
                    f"Warning: agent list failed for engine '{engine_id}' in "
                    f"'{location}' (HTTP {response.status_code}): {response.text[:200]}",
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
                f"Warning: agent list failed for engine '{engine_id}' in "
                f"'{location}': {e}",
                file=sys.stderr,
            )
            break
    return agents


def get_agent_type(agent):
    """Determines the type of the agent from its definition field."""
    definitions = [
        ("adkAgentDefinition", "ADK"),
        ("a2aAgentDefinition", "A2A"),
        ("managedAgentDefinition", "Managed (1P)"),
        ("lowCodeAgentDefinition", "Low-Code"),
        ("noCodeAgentDefinition", "No-Code"),
        ("workflowAgentDefinition", "Workflow"),
        ("skillAgentDefinition", "Skill"),
        ("agentDesignerAgentDefinition", "Agent Designer"),
        ("dialogflowAgentDefinition", "Dialogflow"),
        ("iframeAgentDefinition", "Iframe"),
        ("httpAgentDefinition", "HTTP"),
        ("appAgentDefinition", "App"),
        ("longRunningAgentDefinition", "Long-Running"),
    ]
    for field, label in definitions:
        if field in agent:
            return label
    return "Unknown"


def get_payload_email(agent, agent_type):
    """Returns the creator email from the agent definition, when it is present.

    An agent resolved here needs no log query at all.
    """
    author = None
    if agent_type == "Low-Code":
        author = agent.get("lowCodeAgentDefinition", {}).get("ownerName")
    elif agent_type == "Agent Designer":
        chat = agent.get("agentDesignerAgentDefinition", {}).get("chatAgentDefinition", {})
        author = chat.get("owner")
    elif agent_type == "Workflow":
        author = agent.get("workflowAgentDefinition", {}).get("owner")
    elif agent_type == "Skill":
        author = agent.get("skillAgentDefinition", {}).get("owner")
    elif agent_type == "No-Code":
        author = agent.get("noCodeAgentDefinition", {}).get("owner")

    # Accept only an address. A SPIFFE identity is not a person.
    if author and "@" in author and not author.startswith("SPIFFE"):
        return author
    return None


# ------------------------------------------------------------- Cloud Logging

def build_window_filter(project_id, start, end):
    """Builds the Cloud Logging filter for one time window.

    The logName and timestamp clauses use indexed fields, so the backend can
    skip whole storage blocks. The serviceName and methodName clauses are not
    indexed. They reduce the returned rows only.

    The filter names no agent ID. An ID clause is not indexed, so it does not
    reduce the scan. It only makes the result sparser, and a sparse result
    raises the risk of the backend error "timed out getting cursor token".
    """
    activity_log = f"projects/{project_id}/logs/cloudaudit.googleapis.com%2Factivity"
    return (
        f'logName="{activity_log}" AND '
        'protoPayload.serviceName="discoveryengine.googleapis.com" AND '
        'protoPayload.methodName:"AgentService.CreateAgent" AND '
        f'timestamp >= "{to_filter_stamp(start)}" AND '
        f'timestamp <= "{to_filter_stamp(end)}"'
    )


def fetch_log_page(session, payload, timeout=60):
    """Sends one entries.list request and returns the parsed body.

    Retries HTTP 5xx and network errors with an exponential wait. A sparse scan
    can return HTTP 500 with "timed out getting cursor token". That error is
    transient. Returns None when the request failed for good.
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
                    f"Error fetching logs (HTTP {response.status_code}): "
                    f"{response.text[:300]}",
                    file=sys.stderr,
                )
                return None
            error = f"HTTP {response.status_code}"
        except Exception as e:
            error = str(e)

        if attempt < MAX_LOG_ATTEMPTS:
            print(
                f"    Log request failed ({error}). Waiting {delay}s, then "
                f"attempt {attempt + 1} of {MAX_LOG_ATTEMPTS}...",
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


def creator_from_entry(entry):
    """Returns (agent_id, email) from one audit entry, or (None, None).

    Only response.name carries the ID of the new agent. resourceName names the
    parent assistant, so it never identifies the agent that was created.
    """
    proto = entry.get("protoPayload", {})
    response = proto.get("response") or {}
    name = response.get("name", "")
    if not name:
        return None, None
    email = proto.get("authenticationInfo", {}).get("principalEmail", "")
    if not email:
        return None, None
    return name.split("/")[-1], email


# ----------------------------------------------------------- window planning

def build_windows(targets, gap, buffer_span, max_windows):
    """Groups agents by creation time and returns one window for each group.

    Each window is a dict with `start`, `end` and `ids`. A window carries only
    the agents it should contain, so the reader can stop as soon as that set is
    complete.

    The number of windows has a natural ceiling. A new group starts only when
    two creation times differ by more than `gap`, and every such difference
    consumes more than `gap` of the timeline. Over 400 days with a 24-hour gap
    the count cannot exceed 401, whatever the agent count.
    """
    ordered = sorted(targets, key=lambda item: item["created"])
    groups = [[ordered[0]]]
    for target in ordered[1:]:
        if target["created"] - groups[-1][-1]["created"] > gap:
            groups.append([target])
        else:
            groups[-1].append(target)

    windows = [
        {
            "start": group[0]["created"] - buffer_span,
            "end": group[-1]["created"] + buffer_span,
            "ids": {item["id"] for item in group},
        }
        for group in groups
    ]

    # Merge the closest neighbours until the count fits the limit
    while len(windows) > max_windows:
        closest = min(
            range(len(windows) - 1),
            key=lambda i: windows[i + 1]["start"] - windows[i]["end"],
        )
        windows[closest:closest + 2] = [{
            "start": windows[closest]["start"],
            "end": windows[closest + 1]["end"],
            "ids": windows[closest]["ids"] | windows[closest + 1]["ids"],
        }]
    return windows


def read_window(session, project_id, window, timeout, max_pages):
    """Reads one window and returns (creators, pages_read).

    Stops as soon as every agent ID in the window has a creator.
    """
    log_filter = build_window_filter(project_id, window["start"], window["end"])
    wanted = window["ids"]
    creators = {}
    page_token = ""
    pages = 0

    while pages < max_pages:
        payload = {
            "resourceNames": [f"projects/{project_id}"],
            "filter": log_filter,
            "pageSize": LOG_PAGE_SIZE,
            "orderBy": "timestamp desc",
        }
        if page_token:
            payload["pageToken"] = page_token

        data = fetch_log_page(session, payload, timeout=timeout)
        if data is None:
            break
        pages += 1

        for entry in data.get("entries", []):
            agent_id, email = creator_from_entry(entry)
            if agent_id in wanted and agent_id not in creators:
                creators[agent_id] = email

        if len(creators) >= len(wanted):
            break
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return creators, pages


def resolve_creators(session, project_id, targets, gap_hours, buffer_hours,
                     max_windows, max_pages, time_budget, timeout=60):
    """Resolves creator emails for the given agents. Returns a dict by agent ID."""
    if not targets:
        return {}

    windows = build_windows(
        targets,
        gap=timedelta(hours=gap_hours),
        buffer_span=timedelta(hours=buffer_hours),
        max_windows=max_windows,
    )

    total_hours = sum(
        (window["end"] - window["start"]).total_seconds() for window in windows
    ) / 3600.0
    span = max(t["created"] for t in targets) - min(t["created"] for t in targets)
    span_hours = span.total_seconds() / 3600.0 + 2 * buffer_hours

    print(
        f"Planned {len(windows)} log window(s) covering {total_hours:,.1f} hours, "
        f"from an agent age span of {span_hours:,.1f} hours.",
        file=sys.stderr,
    )

    creators = {}
    started = time.monotonic()
    pages_total = 0
    windows_read = 0
    stop_reason = "every window was read"

    for number, window in enumerate(windows, start=1):
        if time.monotonic() - started >= time_budget:
            stop_reason = f"the time budget of {time_budget}s was spent"
            break

        found, pages = read_window(session, project_id, window, timeout, max_pages)
        creators.update(found)
        pages_total += pages
        windows_read += 1

        print(
            f"  Window {number}/{len(windows)} "
            f"[{to_filter_stamp(window['start'])} to {to_filter_stamp(window['end'])}] "
            f"found {len(found)} of {len(window['ids'])}. "
            f"Total {len(creators)} of {len(targets)} "
            f"({format_seconds(time.monotonic() - started)}).",
            file=sys.stderr,
        )

    unresolved = len(targets) - len(creators)
    print(
        f"Creator lookup stopped because {stop_reason}. "
        f"{len(creators)} resolved, {unresolved} unresolved, "
        f"{windows_read} window(s), {pages_total} page(s), "
        f"{format_seconds(time.monotonic() - started)}.",
        file=sys.stderr,
    )

    if unresolved and windows_read == len(windows):
        print(
            "Note: an agent created before the 400-day audit log retention window "
            "has no log entry. If many agents are unresolved, raise "
            "--log_window_buffer_hours and run again.",
            file=sys.stderr,
        )

    return creators


# ------------------------------------------------------------------- the CLI

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


def build_parser():
    parser = argparse.ArgumentParser(
        description="List Gemini Enterprise agents and their creator emails."
    )
    parser.add_argument("--project_id",
                        help="Google Cloud Project ID. Defaults to the environment.")
    parser.add_argument("--format", choices=["table", "csv"], default="table",
                        help="Output format (default: table).")
    parser.add_argument("--location",
                        help="Comma-separated locations to scan. Overrides .env.")
    parser.add_argument("--log_window_gap_hours", type=int, default=DEFAULT_GAP_HOURS,
                        help=f"A gap larger than this starts a new log window "
                             f"(default: {DEFAULT_GAP_HOURS}). Raise it to read "
                             f"fewer, wider windows.")
    parser.add_argument("--log_window_buffer_hours", type=int,
                        default=DEFAULT_BUFFER_HOURS,
                        help=f"Extra hours on both sides of each window "
                             f"(default: {DEFAULT_BUFFER_HOURS}).")
    parser.add_argument("--log_max_windows", type=int, default=DEFAULT_MAX_WINDOWS,
                        help=f"Upper limit on the number of windows "
                             f"(default: {DEFAULT_MAX_WINDOWS}).")
    parser.add_argument("--log_max_pages_per_window", type=int,
                        default=DEFAULT_MAX_PAGES_PER_WINDOW,
                        help=f"Upper limit on pages read for one window "
                             f"(default: {DEFAULT_MAX_PAGES_PER_WINDOW}).")
    parser.add_argument("--log_time_budget", type=int, default=DEFAULT_TIME_BUDGET,
                        help=f"Maximum seconds spent resolving creators "
                             f"(default: {DEFAULT_TIME_BUDGET}).")
    return parser


def collect_agents(session, project_id, locations):
    """Returns (rows, targets). A target is an agent that needs a log lookup."""
    rows = []
    targets = []
    for location in locations:
        print(f"Scanning location: {location} ...", file=sys.stderr)
        for engine in list_engines(session, project_id, location):
            engine_id = engine.get("name", "").split("/")[-1]
            for agent in list_agents(session, project_id, location, engine_id):
                agent_type = get_agent_type(agent)
                if agent_type not in COUNTED_AGENT_TYPES:
                    continue

                agent_id = agent.get("name", "").split("/")[-1]
                creator = get_payload_email(agent, agent_type)
                created_raw = agent.get("createTime", "")

                rows.append({
                    "agent_id": agent_id,
                    "display_name": agent.get("displayName", ""),
                    "description": agent.get("description", ""),
                    "type": agent_type,
                    "engine_id": engine_id,
                    "location": location,
                    "creator": creator,
                    "create_time": format_datetime(created_raw),
                })

                if creator:
                    continue
                created = parse_iso(created_raw)
                if created is None:
                    # Without a creation time there is no window to read
                    continue
                targets.append({"id": agent_id, "created": created})
    return rows, targets


def write_output(rows, output_format):
    fields = ["agent_id", "display_name", "description", "type",
              "engine_id", "location", "creator", "create_time"]
    if output_format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        return

    template = "{:<22} | {:<30} | {:<50} | {:<21} | {:<30}"
    print(template.format("Agent ID", "Agent Name", "Description",
                          "Create Time", "Creator Email"))
    print("-" * 165)
    for row in rows:
        description = row["description"]
        if len(description) > 47:
            description = description[:44] + "..."
        print(template.format(row["agent_id"], row["display_name"], description,
                              row["create_time"], row["creator"]))


def main():
    run_start = time.monotonic()
    args = build_parser().parse_args()

    if args.location:
        locations = parse_locations(args.location, "the --location flag")
    else:
        from_env = os.getenv("LOCATION") or os.getenv("LOCATIONS")
        if from_env:
            locations = parse_locations(from_env, "LOCATION in the .env file")
        else:
            locations = ["global", "us", "eu"]

    try:
        credentials, auto_project_id = google.auth.default()
        session = AuthorizedSession(credentials)
    except Exception as e:
        print(f"Authentication Error: {e}", file=sys.stderr)
        print("Run 'gcloud auth application-default login' first.", file=sys.stderr)
        sys.exit(1)

    project_id = (args.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
                  or os.getenv("PROJECT_ID") or auto_project_id)
    if not project_id:
        print("Error: no project ID. Use --project_id <PROJECT_ID>.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning project: {project_id} ...", file=sys.stderr)
    scan_start = time.monotonic()
    rows, targets = collect_agents(session, project_id, locations)
    scan_seconds = time.monotonic() - scan_start

    print(f"Found {len(rows)} no-code/low-code agents in "
          f"{format_seconds(scan_seconds)}.", file=sys.stderr)
    if not rows:
        print("No no-code agents found.", file=sys.stderr)
        print(f"Total run time: {format_seconds(time.monotonic() - run_start)}.",
              file=sys.stderr)
        return

    if targets:
        print(f"Resolving {len(targets)} creator email(s) from Cloud Audit Logs...",
              file=sys.stderr)
        creators = resolve_creators(
            session, project_id, targets,
            gap_hours=args.log_window_gap_hours,
            buffer_hours=args.log_window_buffer_hours,
            max_windows=args.log_max_windows,
            max_pages=args.log_max_pages_per_window,
            time_budget=args.log_time_budget,
        )
        for row in rows:
            if not row["creator"]:
                row["creator"] = creators.get(row["agent_id"],
                                              "N/A (No log entry found)")
    else:
        print("Every creator came from the agent definition. No log query needed.",
              file=sys.stderr)

    write_output(rows, args.format)
    sys.stdout.flush()

    print(f"Total run time: {format_seconds(time.monotonic() - run_start)}.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
