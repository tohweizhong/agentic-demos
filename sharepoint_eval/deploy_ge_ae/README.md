# SharePoint File Lister Agent - Cloud Deployment Guide

This folder has all the scripts to deploy the **SharePoint File Lister ADK Agent** to Google Cloud's **Gemini Enterprise Agent Engine** (Vertex AI Reasoning Engine).

## Package Contents
* **`agent.py`**: Main agent code with instructions, models, and tools.
* **`sharepoint_client.py`**: Helper code for Microsoft Graph API (uses environment variables in the cloud).
* **`requirements.txt`**: List of library dependencies for the cloud container.
* **`.ae_ignore`**: Rules to ignore local files, logs, or secrets during build.
* **`deploy.sh`**: Simple shell script to deploy the agent in one click.

---

## Deployment Steps

### Step 1: Set Up Environment Settings
Create your `.env` file using the template:
```bash
cp .env.example .env
```

Edit the new `.env` file and add your settings:
```ini
# SharePoint & MSAL Authentication Credentials
TENANT_ID=your-sharepoint-tenant-id
CLIENT_ID=your-sharepoint-client-id
CLIENT_SECRET=your-sharepoint-client-secret

# SharePoint Target Configuration
SHAREPOINT_HOST=yourcompany.sharepoint.com
SHAREPOINT_SITE_PATH=your-site-name
SHAREPOINT_FOLDER_PATH=Mock data Jun26

# Google Cloud Deployment Settings
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=us-central1
MODEL_NAME=gemini-2.5-flash
```

---

### Step 2: Log In to Google Cloud
Log in to your Google Cloud account with access to Vertex AI:
```bash
gcloud auth login
gcloud auth application-default login
```

---

### Step 3: Run the Deploy Script
Run the deployment script from this folder:
```bash
./deploy.sh
```

When the script finishes:
1. The ADK framework registers your SharePoint tools.
2. It uploads the package to **Vertex AI Reasoning Engines** in Google Cloud.
3. The script prints a direct link to the **Vertex AI Playground** in the Cloud Console. You can open this link to test your agent live!

---

## How Cloud Deployment Works
* **Smart Settings Check**: The agent reads credentials from environment variables in the cloud, falling back to `config.json` only when running locally.
* **Lightweight Staging**: The `.ae_ignore` file filters out local temporary files, tests, mock files, and large logs to make uploads fast.
* **Safe Code Fallback**: All tools use Python libraries to read documents so parsing works even if native tools (like `pdftotext`) are missing in the cloud container.
