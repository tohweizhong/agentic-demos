#!/bin/bash
set -e

# Move to the directory of the script
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "❌ Error: .env file not found in deploy_ge_ae directory!"
  echo "Please copy .env.example to .env and fill in your SharePoint and GCP credentials."
  exit 1
fi

# Load env file
# Using export to ensure loaded variables are visible to the subprocess
while IFS= read -r line || [ -n "$line" ]; do
  # Ignore comments and empty lines
  if [[ ! "$line" =~ ^# ]] && [[ -n "$line" ]]; then
    export "$line"
  fi
done < .env

echo "🚀 Deploying SharePoint File Lister ADK Agent to Gemini Enterprise Agent Engine..."

# Check if adk CLI is available, otherwise try ../.venv/bin/adk
ADK_CMD="adk"
if ! command -v adk &> /dev/null; then
  if [ -f "../.venv/bin/adk" ]; then
    ADK_CMD="../.venv/bin/adk"
  else
    echo "❌ Error: ADK CLI ('adk') not found in PATH or ../.venv/bin/adk!"
    echo "Please ensure the virtual environment is activated or google-adk is installed."
    exit 1
  fi
fi

# Execute deployment
$ADK_CMD deploy agent_engine \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_LOCATION" \
  --display_name="SharePoint_ADK_Agent" \
  --description="SharePoint Document Listing and Access Auditing Assistant" \
  --adk_app="agent_engine_app" \
  --adk_app_object="root_agent" \
  --env_file="$(pwd)/.env" \
  --requirements_file="$(pwd)/requirements.txt" \
  --validate-agent-import \
  "$(pwd)"
