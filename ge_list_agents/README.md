# Gemini Enterprise Agent Lister & Identity Resolver

This repository provides tools to list and report on **no-code / low-code / workflow** agents deployed inside your Gemini Enterprise (Discovery Engine) application. 

Since the standard Discovery Engine API metadata does not directly output creator email addresses, these scripts resolve creator identities by scanning **Cloud Audit Logs** (specifically `CreateAgent` log entries).

---

## Architecture Overview

There are two separate execution paths depending on how your users authenticate to Google Cloud:

1. **Standard Flow (`list_agents.py`)**: Designed for standard Google Workspace / Cloud Identity environments. Resolves creators directly to standard email addresses (e.g. `user@yourdomain.com`).
2. **Workforce Identity Federation (WIF) Flow (`list_agents_wif.py` + `resolve_entra_users.py`)**: Designed for federated environments (e.g. users authenticated via Microsoft Entra ID). It exports opaque user UUIDs to a text file, which can then be batch-resolved to readable emails using Microsoft Graph API.

```
                   ┌──────────────────────────────────────┐
                   │   Gemini Enterprise (Discovery Eng)   │
                   └──────────────────┬───────────────────┘
                                      │
                                      ▼
                        [list_agents_wif.py] (WIF)
                                      │
                                      ▼
                           unresolved_uuids.txt
                                      │
                                      ▼
                         [resolve_entra_users.py]
                                      │ (Queries MS Graph API)
                                      ▼
                             resolved_emails.txt
```

---

## Prerequisites

### Google Cloud Platform (GCP)
* **Cloud Audit Logs**: No action needed. `CreateAgent` is a metadata write, so Google Cloud records it in the **Admin Activity** audit log. That log is always on and you cannot disable it. **Data Access** logs are not used.
* **GCP Roles**: The identity running the scanning scripts needs:
  * `roles/discoveryengine.viewer` (or `roles/discoveryengine.admin`)
  * `roles/logging.viewer` (to read creation events from logs)
* **GCP Authentication**: Run standard application credentials auth before starting:
  ```bash
  gcloud auth application-default login
  ```

> [!IMPORTANT]
> **Audit log retention**: Admin Activity logs stay for 400 days. The period is fixed. An agent created before that window has no log entry. The scripts then report the creator as `N/A (No log entry found)`. Low-Code, No-Code, Workflow, Agent Designer and Skill agents often carry the owner in the agent definition. Those agents are not affected.

### Microsoft Entra ID (Azure AD)
For the WIF identity resolver utility (`resolve_entra_users.py`) to successfully resolve user UUIDs, your App Registration must have:
* **API Permissions**: Under **Application Permissions** (not *Delegated permissions*), assign **`User.ReadBasic.All`** or **`User.Read.All`** from Microsoft Graph.
* **Admin Consent**: A Microsoft Entra Tenant Administrator must explicitly click **"Grant admin consent for [Your Organization]"** in the portal to authorize the application permissions.

### Python Dependencies
Install standard dependencies:
```bash
pip install requests google-auth
```

---

## Setup & Configuration

> [!IMPORTANT]
> Run every command from inside this folder. The scripts read `.env` from the current
> working directory. They do not search parent folders.

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in the details:
   * `PROJECT_ID`: Your GCP Project ID.
   * `LOCATION` (Optional): Google Cloud locations to scan (comma-separated, e.g. `global,us,eu`). Defaults to `global,us,eu`. Can also be overridden at runtime via the `--location` CLI flag.
   * **Azure/Entra credentials** (Only required if using the WIF resolver flow):
     * `AZURE_TENANT_ID`
     * `AZURE_CLIENT_ID`
     * `AZURE_CLIENT_SECRET`

### Which project does a run use?

The scripts take the first value they find, in this order:

1. The `--project_id` flag.
2. The `GOOGLE_CLOUD_PROJECT` environment variable.
3. The `PROJECT_ID` value in `.env`.
4. The project attached to your Application Default Credentials.

Every run prints the project it chose on the first line. Check that line.


---

## Execution Guide

### Option A: Standard Flow (Non-WIF)

Use this if your creators login using standard Google Accounts.

1. **List all agents and creators:**
   ```bash
   python3 list_agents.py --format table
   ```
   *   *Note: You can override the locations to scan using `--location <locations>` (e.g. `--location global,us`). Defaults to `global,us,eu`.*
2. **Export to CSV:**
   ```bash
   python3 list_agents.py --format csv > list_agents.csv
   ```

---

### Option B: Workforce Identity Federation (WIF) Flow

Use this if your creators login via external Identity Providers (like Microsoft Entra ID) and show up as UUID subjects in Google Cloud.

#### Step 1: Scan and export WIF UUIDs
Run the WIF-specific scanner. It will output a table/CSV, and automatically write all unresolved creator UUIDs into a text file:
```bash
python3 list_agents_wif.py --format table
```
*   **Outputs**: Generates `unresolved_uuids.txt` (by default) listing all unique external subject UUIDs.
*   *Note: You can override the output text file using `--output_uuids <path>`.*
*   *Note: You can override the locations to scan using `--location <locations>` (e.g. `--location global,us`). Defaults to `global,us,eu`.*

#### Step 2: Resolve WIF UUIDs to Emails against Entra ID
Run the Entra resolver script pointing to the text file generated in Step 1:
```bash
./resolve_entra_users.py unresolved_uuids.txt
```
*   **Outputs**: Resolves the UUIDs using Microsoft Graph API client credentials and writes them line-by-line into `resolved_emails.txt`.
*   *Note: You can override the output file name using `--output <path>`.*

---

## How creator resolution works

Listing the agents is fast. Resolving the creators is the slow part, and it is the part
that can fail. Read this before you run against a large project.

The scripts read the `CreateAgent` entries in the Admin Activity audit log. Cloud Logging
does not index the audit payload fields, so the backend must scan the time window. The
scan returns small, uneven pages. Each page costs a few seconds.

The scripts print one line for each page:

```
Resolving 14 creator emails from Cloud Audit Logs...
  Page 1: resolved 0 of 14 agents (6s elapsed).
  Page 3: resolved 3 of 14 agents (18s elapsed).
  Page 16: resolved 14 of 14 agents (91s elapsed).
Log scan stopped because every agent was resolved. 14 resolved, 0 unresolved, 16 pages, 91s.
```

An early page with zero matches is normal. Do not stop the run.

The scan stops on the first of four conditions.

| Stop reason | Meaning |
|---|---|
| every agent was resolved | Best case. The scan ended early. |
| the log history ended | The window holds no more entries. Any remaining agent has no log entry. |
| the page limit of N pages was reached | The `--log_max_pages` guard fired. |
| the time budget of Ns was spent | The `--log_time_budget` guard fired. |

The last two guards exist because the scan cannot always finish. An agent created before
the 400-day retention window has no log entry, so the early exit never fires.

### Scan guard flags

| Flag | Default | Use |
|---|---|---|
| `--log_max_pages` | 200 | Raise it for a project with thousands of agents. Lower it for a quick look. |
| `--log_time_budget` | 300 | Seconds. Raise it when the scan stops before every agent resolves. |

Example for a large project:

```bash
python3 list_agents.py --format csv --location global \
  --log_max_pages 2000 --log_time_budget 3600 > list_agents.csv
```

A partial result is still useful. Every agent that did not resolve carries
`N/A (No log entry found)`.

---

## Troubleshooting

### `Failed to resolve 'global%20...'` or `is not a valid location`

Your `.env` holds a comment on the same line as the value:

```
LOCATION=global #or e.g. global, us     <- wrong
```

The whole text after `=` became the location, so it became part of the hostname. Write the
comment on its own line:

```
# or e.g. global,us
LOCATION=global                          <- correct
```

Current versions strip an inline comment and reject an invalid location with a clear
message. Older copies of `.env.example` shipped the wrong line. Copy the template again.

To keep a `#` inside a value, put the value in quotes.

### `Found 0 no-code/low-code agents.`


Look for a warning line above it. The scripts now report the reason.

```
Warning: cannot list engines in 'global' (HTTP 403). Check the project ID, the IAM
roles, and that the Discovery Engine API is enabled.
```

Common causes, in order:

1. The credentials are wrong. On a Compute Engine instance or a cloudtop, Application
   Default Credentials use the machine service account, which usually has no access. Run
   `gcloud auth application-default login`.
2. The project has no agent in that location. Try `--location global,us,eu`.
3. The Discovery Engine API is off in that project.

### `Filter cannot be longer than 20000 characters.`

You are running an old copy of the script. The current version never names an agent ID in
the filter, so the filter length does not grow with the agent count. Update the script.

### `Internal error encountered` with `timed out getting cursor token`

This is a transient Cloud Logging error on a sparse scan. The current version retries five
times with an exponential wait. If it still fails, lower the scan cost by giving a
narrower location list, or accept a partial result with a smaller `--log_time_budget`.

### The run appears to hang

Check the per-page progress lines. If you piped `stderr` into another command, the shell
may hold the output in a buffer. Run without a pipe to watch the progress.

### `UserWarning: ... without a quota project`

Harmless. To remove it, run:

```bash
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### Every creator shows `N/A (No log entry found)`

Two possible causes:

1. The agents are older than the 400-day Admin Activity retention window.
2. The scan stopped early. Read the stop reason and raise the guard that fired.

---

## Output Formats & Examples


### 1. CSV Agent Export (`list_agents.csv`)
The CSV output contains the following 8 columns:
*   `agent_id`: Unique numerical identifier of the agent.
*   `display_name`: The user-facing display name of the agent.
*   `description`: Summary of the agent's purpose.
*   `type`: Agent type (e.g. `Low-Code`, `No-Code`, `Workflow`, `Agent Designer`).
*   `engine_id`: ID of the parent engine/application.
*   `location`: GCP location region (e.g. `global`, `us`).
*   `creator`: Creator identifier. Can be a standard Workspace email, an opaque federated user UUID, or a Google Cloud Principal Identifier (CPI, e.g. `0x1000...#`). Note that CPIs are internal Google structures generated for federated login events and cannot be resolved via Entra ID.
*   `create_time`: Creation timestamp formatted as `YYYY-MM-DD HH:MM:SS`.

**Example Rows:**
```csv
agent_id,display_name,description,type,engine_id,location,creator,create_time
12345678901234567890,My Agent,Agent to help interact with enterprise data.,Workflow,my-engine_123456789,us,0x100000abcdef:AEjPq6...#,2026-07-08 07:33:11
23456789012345678901,My Agent,Agent to help interact with enterprise data.,Low-Code,my-engine_123456789,us,194eb298-758e-4da3-bf63-3ae52e7b98fc,2026-07-08 08:47:41
```

### 2. Unresolved WIF UUIDs File (`unresolved_uuids.txt`)
Contains a unique list of raw external identity pool user UUIDs extracted from logs/metadata (one per line):
```text
194eb298-758e-4da3-bf63-3ae52e7b98fc
```

### 3. Resolved Entra Emails File (`resolved_emails.txt`)
Contains a sorted, unique list of corporate email addresses resolved from Entra ID via Graph API (one per line):
```text
alice@yourdomain.com
```

---

## File Structure

*   `list_agents.py`: Scanning script for standard Workspace Google accounts.
*   `list_agents_wif.py`: Scanning script for Workforce Identity Federation (WIF) setups.
*   `resolve_entra_users.py`: Entra ID/Azure AD identity resolver utility.
*   `.env`: Local environment configurations (ignored by git).
*   `.env.example`: Configuration template for onboarding new users.
*   `.gitignore`: Prevents checking in private credentials or data exports.
