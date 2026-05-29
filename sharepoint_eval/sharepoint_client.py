import os
import json
import requests
import msal

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Config file not found at {CONFIG_PATH}. Please create one from the template.")
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def get_access_token(config):
    """Acquires an access token using client credentials flow."""
    authority = f"https://login.microsoftonline.com/{config['TENANT_ID']}"
    scopes = ["https://graph.microsoft.com/.default"]
    
    app = msal.ConfidentialClientApplication(
        config["CLIENT_ID"],
        authority=authority,
        client_credential=config["CLIENT_SECRET"]
    )
    
    # Try to get token from cache first
    result = app.acquire_token_silent(scopes, account=None)
    
    if not result:
        # Get a new token
        result = app.acquire_token_for_client(scopes=scopes)
        
    if "access_token" in result:
        return result["access_token"]
    else:
        error_description = result.get("error_description", "Unknown authentication error")
        raise Exception(f"Failed to acquire token: {error_description}")

def get_site_id(access_token, host, site_path):
    """Retrieves the SharePoint site ID by resolving the hostname and relative site path."""
    # Ensure the site_path is correctly formatted
    site_path = site_path.strip("/")
    relative_path = f"/sites/{site_path.split('sites/')[-1]}" if "sites/" in site_path else f"/sites/{site_path}"
    if relative_path == "/sites/":
        relative_path = ""
        
    url = f"https://graph.microsoft.com/v1.0/sites/{host}:{relative_path}"
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("id")
    else:
        raise Exception(f"Failed to retrieve site ID: {response.status_code} - {response.text}")

def get_default_drive_id(access_token, site_id):
    """Gets the default document library (drive) ID for the given site."""
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("id")
    else:
        raise Exception(f"Failed to retrieve default drive ID: {response.status_code} - {response.text}")

def list_children(access_token, drive_id, item_id="root"):
    """Retrieves children of a specific drive item with sensitivity labels."""
    url = f"https://graph.microsoft.com/beta/drives/{drive_id}/items/{item_id}/children?$select=id,name,size,lastModifiedDateTime,webUrl,folder,file,sensitivityLabel"
    if item_id == "root":
        url = f"https://graph.microsoft.com/beta/drives/{drive_id}/root/children?$select=id,name,size,lastModifiedDateTime,webUrl,folder,file,sensitivityLabel"
        
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        raise Exception(f"Failed to retrieve children: {response.status_code} - {response.text}")

def resolve_path_to_item_id(access_token, drive_id, folder_path):
    """Resolves a relative folder path (e.g., 'FolderA/FolderB') to its Graph item ID."""
    if not folder_path or folder_path.strip() in ["", "/"]:
        return "root"
        
    # Standardize relative path
    folder_path = folder_path.strip("/")
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{folder_path}"
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("id")
    else:
        raise Exception(f"Failed to resolve folder path '{folder_path}': {response.status_code} - {response.text}")

def get_all_files_recursive(access_token, drive_id, item_id="root", current_path=""):
    """Recursively walks the drive to collect all files and folders."""
    items = list_children(access_token, drive_id, item_id)
    results = []
    
    for item in items:
        # Determine item type and path
        name = item.get("name")
        relative_path = f"{current_path}/{name}" if current_path else name
        is_folder = "folder" in item
        
        sensitivity_label_data = item.get("sensitivityLabel")
        sensitivity_label = None
        if sensitivity_label_data:
            sensitivity_label = sensitivity_label_data.get("displayName")

        item_info = {
            "name": name,
            "path": relative_path,
            "type": "folder" if is_folder else "file",
            "size": item.get("size", 0),
            "last_modified": item.get("lastModifiedDateTime"),
            "web_url": item.get("webUrl"),
            "id": item.get("id"),
            "sensitivity_label": sensitivity_label
        }
        results.append(item_info)
        
        if is_folder:
            # Recurse
            results.extend(get_all_files_recursive(access_token, drive_id, item.get("id"), relative_path))
            
    return results

def list_sharepoint_files_api(folder_path: str = "", recursive: bool = False):
    """Helper function that authenticates and returns files in a SharePoint site."""
    config = load_config()
    
    # Validate placeholders
    placeholders = ["YOUR_TENANT_ID_HERE", "YOUR_CLIENT_ID_HERE", "YOUR_CLIENT_SECRET_HERE"]
    if any(placeholder in [config.get("TENANT_ID"), config.get("CLIENT_ID"), config.get("CLIENT_SECRET")] for placeholder in placeholders):
        raise ValueError("Please edit the 'config.json' file to include your real Azure AD / SharePoint credentials.")
        
    token = get_access_token(config)
    site_id = get_site_id(token, config["SHAREPOINT_SITE_HOST"], config["SHAREPOINT_SITE_PATH"])
    drive_id = get_default_drive_id(token, site_id)
    
    if recursive:
        target_item_id = "root"
        starting_path = ""
        if folder_path:
            target_item_id = resolve_path_to_item_id(token, drive_id, folder_path)
            starting_path = folder_path.strip("/")
        return get_all_files_recursive(token, drive_id, target_item_id, starting_path)
    else:
        target_item_id = "root"
        if folder_path:
            target_item_id = resolve_path_to_item_id(token, drive_id, folder_path)
        
        items = list_children(token, drive_id, target_item_id)
        results = []
        for item in items:
            name = item.get("name")
            relative_path = f"{folder_path.strip('/')}/{name}" if folder_path else name
            is_folder = "folder" in item
            
            sensitivity_label_data = item.get("sensitivityLabel")
            sensitivity_label = None
            if sensitivity_label_data:
                sensitivity_label = sensitivity_label_data.get("displayName")

            results.append({
                "name": name,
                "path": relative_path,
                "type": "folder" if is_folder else "file",
                "size": item.get("size", 0),
                "last_modified": item.get("lastModifiedDateTime"),
                "web_url": item.get("webUrl"),
                "id": item.get("id"),
                "sensitivity_label": sensitivity_label
            })
        return results

def search_sharepoint_files_api(query: str):
    """Searches for files and folders in the SharePoint site document library using Graph API."""
    config = load_config()
    
    # Validate placeholders
    placeholders = ["YOUR_TENANT_ID_HERE", "YOUR_CLIENT_ID_HERE", "YOUR_CLIENT_SECRET_HERE"]
    if any(placeholder in [config.get("TENANT_ID"), config.get("CLIENT_ID"), config.get("CLIENT_SECRET")] for placeholder in placeholders):
        raise ValueError("Please edit the 'config.json' file to include your real Azure AD / SharePoint credentials.")
        
    token = get_access_token(config)
    
    # 1. Search using the /search/query POST endpoint
    search_url = "https://graph.microsoft.com/v1.0/search/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "requests": [
            {
                "entityTypes": ["driveItem"],
                "query": {
                    "queryString": query
                },
                "region": "APC"
            }
        ]
    }
    response = requests.post(search_url, headers=headers, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"Failed to search files: {response.status_code} - {response.text}")
        
    hits_containers = response.json().get("value", [])[0].get("hitsContainers", [])
    hits = hits_containers[0].get("hits", []) if hits_containers else []
    results = []
    
    # 2. For each hit, fetch detailed metadata including sensitivity labels using direct GET endpoint
    for hit in hits:
        resource = hit.get("resource", {})
        item_id = resource.get("id")
        drive_id = resource.get("parentReference", {}).get("driveId")
        name = resource.get("name")
        
        if not item_id or not drive_id:
            continue
            
        detail_url = f"https://graph.microsoft.com/beta/drives/{drive_id}/items/{item_id}?$select=id,name,size,lastModifiedDateTime,webUrl,folder,file,sensitivityLabel,parentReference"
        detail_response = requests.get(detail_url, headers={"Authorization": f"Bearer {token}"})
        
        if detail_response.status_code == 200:
            item = detail_response.json()
            sensitivity_label_data = item.get("sensitivityLabel")
            sensitivity_label = sensitivity_label_data.get("displayName") if sensitivity_label_data else None
            
            parent_path = item.get("parentReference", {}).get("path", "")
            relative_path = name
            if "root:" in parent_path:
                sub_path = parent_path.split("root:")[-1].strip("/")
                relative_path = f"{sub_path}/{name}" if sub_path else name
                
            is_folder = "folder" in item

            results.append({
                "name": name,
                "path": relative_path,
                "type": "folder" if is_folder else "file",
                "size": item.get("size", 0),
                "last_modified": item.get("lastModifiedDateTime"),
                "web_url": item.get("webUrl"),
                "id": item_id,
                "sensitivity_label": sensitivity_label
            })
            
    return results

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts clean text paragraphs from a DOCX binary stream without external libraries."""
    import zipfile
    import xml.etree.ElementTree as ET
    from io import BytesIO
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            paragraphs = []
            for p in root.findall('.//w:p', ns):
                texts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n".join(paragraphs)
    except Exception as e:
        return f"[Error parsing DOCX file: {str(e)}]"

def read_sharepoint_file_api(item_id: str, drive_id: str = None) -> str:
    """Downloads and returns the text content of a file from SharePoint."""
    config = load_config()
    token = get_access_token(config)
    
    if not drive_id:
        site_id = get_site_id(token, config["SHAREPOINT_SITE_HOST"], config["SHAREPOINT_SITE_PATH"])
        drive_id = get_default_drive_id(token, site_id)
    
    # Verify item metadata
    metadata_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
    headers = {"Authorization": f"Bearer {token}"}
    metadata_response = requests.get(metadata_url, headers=headers)
    
    if metadata_response.status_code != 200:
        raise Exception(f"Failed to fetch file metadata: {metadata_response.status_code} - {metadata_response.text}")
        
    metadata = metadata_response.json()
    if "folder" in metadata:
        return "[Error: The requested item is a folder, not a file.]"
        
    name = metadata.get("name", "")
    
    # Download file stream
    content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
    content_response = requests.get(content_url, headers=headers)
    
    if content_response.status_code != 200:
        raise Exception(f"Failed to download file content: {content_response.status_code} - {content_response.text}")
        
    file_bytes = content_response.content
    
    # Parse content
    ext = name.split(".")[-1].lower() if "." in name else ""
    if ext == "docx":
        return extract_text_from_docx(file_bytes)
    elif ext in ["txt", "md", "json", "csv", "xml", "html", "sh", "py", "js", "css"]:
        return file_bytes.decode("utf-8", errors="replace")
    else:
        return f"[File type .{ext} is not directly readable as text. File Name: {name}, Size: {len(file_bytes)} bytes.]"


