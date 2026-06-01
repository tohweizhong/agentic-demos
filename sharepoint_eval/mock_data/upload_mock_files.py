import os
import json
import requests
import sys

# Add root folder to python path to import sharepoint_client helpers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sharepoint_client import (
    load_config,
    get_access_token,
    get_site_id,
    get_default_drive_id
)

MOCK_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_CONFIG_PATH = os.path.join(MOCK_DIR, "mock_upload_config.json")

def load_upload_config():
    if not os.path.exists(UPLOAD_CONFIG_PATH):
        raise FileNotFoundError(f"Mock upload configuration not found at {UPLOAD_CONFIG_PATH}")
    with open(UPLOAD_CONFIG_PATH, "r") as f:
        return json.load(f)

def create_folder_if_not_exists(access_token, drive_id, folder_name) -> str:
    """Verifies if the target folder already exists in the SharePoint Document Library root. Returns its ID."""
    check_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children?$select=id,name,folder"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(check_url, headers=headers)
    if response.status_code == 200:
        items = response.json().get("value", [])
        for item in items:
            if item.get("name") == folder_name and "folder" in item:
                print(f"Target folder '{folder_name}' verified in SharePoint. ID: {item.get('id')}")
                return item.get("id")
                
    raise Exception(f"Target folder '{folder_name}' was not found in the SharePoint library. Please create it manually before running this script.")

def upload_file_to_sharepoint(access_token, drive_id, parent_folder_name, filename, local_filepath):
    """Uploads a file to the designated folder path in SharePoint default drive."""
    # Format PUT URL for simple item upload (< 4MB)
    # Format: /drives/{drive-id}/root:/{parent-path}/{filename}:/content
    import urllib.parse
    safe_filename = urllib.parse.quote(filename)
    safe_folder = urllib.parse.quote(parent_folder_name)
    
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{safe_folder}/{safe_filename}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }
    
    with open(local_filepath, "rb") as f:
        file_data = f.read()
        
    response = requests.put(url, headers=headers, data=file_data)
    if response.status_code in [200, 201]:
        print(f" -> Successfully uploaded '{filename}'")
        return response.json().get("id")
    else:
        print(f" ❌ Failed to upload '{filename}': {response.status_code} - {response.text}")
        return None

def main():
    # 1. Load configurations
    print("Loading configurations...")
    main_config = load_config()  # Mapped automatically from root config.json
    upload_config = load_upload_config()
    
    target_folder = upload_config["TARGET_FOLDER_NAME"]
    
    # 2. Authenticate with Azure AD forcing fresh token acquisition (bypassing cache)
    print("Authenticating with Microsoft Graph API (acquiring fresh token)...")
    import msal
    authority = f"https://login.microsoftonline.com/{main_config['TENANT_ID']}"
    scopes = ["https://graph.microsoft.com/.default"]
    app = msal.ConfidentialClientApplication(
        main_config["CLIENT_ID"],
        authority=authority,
        client_credential=main_config["CLIENT_SECRET"]
    )
    # Explicitly bypass Silent Cache to fetch upgraded roles
    result = app.acquire_token_for_client(scopes=scopes)
    if "access_token" not in result:
        raise Exception(f"Failed to acquire fresh token: {result.get('error_description', 'Unknown error')}")
    token = result["access_token"]
    
    site_id = get_site_id(token, main_config["SHAREPOINT_SITE_HOST"], main_config["SHAREPOINT_SITE_PATH"])
    drive_id = get_default_drive_id(token, site_id)
    
    # 3. Resolve/Create target folder in SharePoint library
    create_folder_if_not_exists(token, drive_id, target_folder)
    
    # 4. Scan local mock files
    local_files = [f for f in os.listdir(MOCK_DIR) if f.split(".")[-1] in ["docx", "pptx", "xlsx", "pdf"] and not f.startswith("Bank_File_")]
    local_files.sort()
    
    print(f"\nReady to upload {len(local_files)} descriptive mock files to SharePoint...")
    
    success_count = 0
    for i, filename in enumerate(local_files):
        local_filepath = os.path.join(MOCK_DIR, filename)
        print(f"[{i+1}/{len(local_files)}] Uploading '{filename}' to '{target_folder}'...")
        file_id = upload_file_to_sharepoint(token, drive_id, target_folder, filename, local_filepath)
        if file_id:
            success_count += 1
            
    print(f"\n========================================")
    print(f"         Upload Run Complete!")
    print(f"========================================")
    print(f"Total Attempted: {len(local_files)}")
    print(f"Successfully Uploaded: {success_count}")
    print(f"All files reside inside SharePoint folder '{target_folder}'!")

if __name__ == "__main__":
    main()
