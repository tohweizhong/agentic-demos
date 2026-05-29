# SharePoint File Lister ADK Agent

This project implements an Agent Development Kit (ADK) agent that allows listing all files and folders in a given SharePoint site.

## 📁 File Structure

- `config.json`: Configuration file for credentials, SharePoint site host, site path, and model selection.
- `sharepoint_client.py`: Python helper utilizing Microsoft Graph API and `msal` for token acquisition and file traversal.
- `agent.py`: The main ADK agent and tool definition.
- `runner.py`: Interactive and command-line runner.

## 🚀 Setup & Usage

Please follow the step-by-step instructions inside [sharepoint_lister_walkthrough.md](sharepoint_lister_walkthrough.md) to:
1. Register an application in Azure Active Directory.
2. Retrieve the client IDs and secrets.
3. Grant the necessary SharePoint API Graph permissions (`Sites.Read.All` and `Files.Read.All`).
4. Edit `config.json` with the credentials.
5. Run the agent!

### Run Example:

```bash
# Make sure you set your Gemini API Key
export GEMINI_API_KEY="your-gemini-api-key"

# Run the interactive agent CLI
.venv/bin/python3 runner.py
```
