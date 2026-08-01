#!/usr/bin/env python3
"""
Utility script to resolve Entra ID (Azure AD) user UUIDs to human-readable emails
using Microsoft Graph API with Client Credentials.
"""

import sys
import argparse
import requests

import os

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

# ---------------------------------------------------------
# Configure your Azure AD / Entra ID Client Credentials here:
# ---------------------------------------------------------
TENANT_ID = os.getenv("AZURE_TENANT_ID") or os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID") or os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")
# ---------------------------------------------------------


def get_access_token(tenant_id, client_id, client_secret):
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }
    try:
        res = requests.post(token_url, data=token_data)
        if res.status_code != 200:
            print(f"Error fetching token (HTTP {res.status_code}): {res.text}", file=sys.stderr)
            return None
        return res.json().get("access_token")
    except Exception as e:
        print(f"Exception during token fetch: {e}", file=sys.stderr)
        return None

def resolve_uuid(access_token, uuid):
    headers = {"Authorization": f"Bearer {access_token}"}
    graph_url = f"https://graph.microsoft.com/v1.0/users/{uuid}"
    try:
        res = requests.get(graph_url, headers=headers)
        if res.status_code == 404:
            return None, "User not found"
        if res.status_code != 200:
            return None, f"HTTP Error {res.status_code}: {res.text}"
        data = res.json()
        email = data.get("mail") or data.get("userPrincipalName") or "N/A"
        name = data.get("displayName") or "N/A"
        return email, name
    except Exception as e:
        return None, f"Exception: {e}"

def main():
    import os
    parser = argparse.ArgumentParser(description="Resolve Entra ID user UUIDs using Microsoft Graph API.")
    parser.add_argument("uuids", nargs="+", help="One or more User UUIDs to resolve, or a path to a text file containing UUIDs (one per line).")
    parser.add_argument("--output", default="resolved_emails.txt", help="Path to write resolved email addresses (default: resolved_emails.txt).")
    args = parser.parse_args()
    
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]) or "YOUR_" in str(TENANT_ID) or "YOUR_" in str(CLIENT_ID) or "YOUR_" in str(CLIENT_SECRET):
        print("Error: Azure credentials must be configured in a .env file or set as environment variables.", file=sys.stderr)
        print("Required variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET", file=sys.stderr)
        sys.exit(1)
        
    uuids = []
    # If the single argument is a file that exists, load UUIDs from it
    if len(args.uuids) == 1 and os.path.isfile(args.uuids[0]):
        try:
            with open(args.uuids[0], "r") as f:
                uuids = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(uuids)} UUIDs from file: {args.uuids[0]}", file=sys.stderr)
        except Exception as e:
            print(f"Error reading file {args.uuids[0]}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        uuids = args.uuids

    if not uuids:
        print("No UUIDs to resolve.", file=sys.stderr)
        sys.exit(0)

    print("Acquiring Microsoft Graph API access token...", file=sys.stderr)
    token = get_access_token(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    if not token:
        print("Error: Failed to obtain access token.", file=sys.stderr)
        sys.exit(1)
        
    resolved_emails = []
    print(f"Resolving {len(uuids)} identities...", file=sys.stderr)
    print("-" * 80, file=sys.stderr)
    for uuid in uuids:
        email, name = resolve_uuid(token, uuid)
        if email and email != "N/A":
            print(f"{uuid} -> {email} ({name})", file=sys.stderr)
            resolved_emails.append(email)
        else:
            print(f"{uuid} -> Failed ({name})", file=sys.stderr)

    if resolved_emails:
        try:
            with open(args.output, "w") as f:
                for email in sorted(set(resolved_emails)):
                    f.write(f"{email}\n")
            print(f"\nWrote {len(resolved_emails)} resolved emails to {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"\nError writing emails to file: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
