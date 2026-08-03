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
* **Cloud Audit Logs**: Ensure that **Admin Activity** and **Data Access** audit logs are enabled in your Google Cloud Project for `discoveryengine.googleapis.com`.
* **GCP Roles**: The identity running the scanning scripts needs:
  * `roles/discoveryengine.viewer` (or `roles/discoveryengine.admin`)
  * `roles/logging.viewer` (to read creation events from logs)
* **GCP Authentication**: Run standard application credentials auth before starting:
  ```bash
  gcloud auth application-default login
  ```

> [!IMPORTANT]
> **Audit Logs Requirement**: The creator resolution relies entirely on Cloud Logging data. If **Data Access** logs were not enabled at the time the agents were created, the scripts will not find creation events and will label the creator as `N/A (No log entry found)`.

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
