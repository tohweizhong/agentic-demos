# SharePoint File Lister Agent - Gemini Enterprise Agent Engine Deployment

This directory contains the self-contained deployment package to deploy the **SharePoint File Lister ADK Agent** to Google Cloud's **Gemini Enterprise Agent Engine** (Vertex AI Reasoning Engine).

## Package Contents
* **`agent.py`**: Core ADK agent defining instructions, model definitions, and registered tools.
* **`sharepoint_client.py`**: Underlying Microsoft Graph API integration code (configured to use environment variables for seamless cloud integration).
* **`requirements.txt`**: Complete dependency manifest for the container package.
* **`.ae_ignore`**: Build-time ignore definitions to avoid packaging local virtual environments, logs, or secrets.
* **`deploy.sh`**: One-click automated deployment orchestration script.

---

## Deployment Walkthrough

### Step 1: Prepare Configuration
Create your `.env` file using the template provided:
```bash
cp .env.example .env
```

Edit the new `.env` file and populate it with your credentials:
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

### Step 2: Authenticate with Google Cloud
Ensure your terminal session is authenticated with Google Cloud with permission to access Vertex AI Reasoning Engines:
```bash
gcloud auth login
gcloud auth application-default login
```

---

### Step 3: Run the Deployment Script
Execute the deployment script from this directory:
```bash
./deploy.sh
```

Upon successful packaging, staging, and upload:
1. The ADK framework will register your custom SharePoint tools and metadata context.
2. It will upload the package to **Vertex AI Reasoning Engines** in your Google Cloud Project.
3. The script will print a direct link to your custom agent's **Vertex AI Playground** in the Google Cloud Console where you can test your agent's multi-turn conversational logic live!

---

## Architecture Highlights for Cloud Deployment
* **Dual-Environment Aware Configuration**: The `sharepoint_client.py` uses environment variables dynamically injected by Agent Engine in the cloud, and falls back to `config.json` only when running locally.
* **Lightweight Staging Bundle**: The `.ae_ignore` file automatically filters out local temporary files, tests, mock banking corpuses, and other large assets to speed up cloud staging times.
* **Native Package Fallbacks**: All file tools are equipped with native Python libraries (like `pypdf`, `python-docx`) to ensure that document parsing succeeds even if native system binaries (such as `pdftotext` or `exiftool`) are absent in the serverless cloud environment.
