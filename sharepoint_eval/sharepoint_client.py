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

def parse_file_via_bash(file_bytes: bytes, ext: str) -> str:
    """Spawns local bash-native parsers to extract text from file bytes if available in the environment."""
    import subprocess
    import tempfile
    import shutil
    
    # Check if bash-native parser is available in path
    if ext == "pdf" and shutil.which("pdftotext"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name
            result = subprocess.run(["pdftotext", temp_path, "-"], capture_output=True, text=True, check=True)
            os.remove(temp_path)
            print(" -> Successfully parsed PDF via bash-native 'pdftotext'")
            return result.stdout
        except Exception as e:
            print(f" ⚠️ pdftotext bash parser failed: {e}. Falling back to Python reader.")
            
    elif ext == "docx" and shutil.which("docx2txt"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name
            result = subprocess.run(["docx2txt", temp_path], capture_output=True, text=True, check=True)
            txt_path = temp_path.replace(".docx", ".txt")
            if os.path.exists(txt_path):
                with open(txt_path, "r") as f:
                    extracted = f.read()
                os.remove(txt_path)
            else:
                extracted = result.stdout
            os.remove(temp_path)
            print(" -> Successfully parsed DOCX via bash-native 'docx2txt'")
            return extracted
        except Exception as e:
            print(f" ⚠️ docx2txt bash parser failed: {e}. Falling back to Python reader.")
            
    elif ext in ["png", "jpg", "jpeg", "mp3", "mp4"] and shutil.which("exiftool"):
        try:
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name
            result = subprocess.run(["exiftool", temp_path], capture_output=True, text=True, check=True)
            os.remove(temp_path)
            print(" -> Successfully parsed EXIF tags via bash-native 'exiftool'")
            return result.stdout
        except Exception as e:
            print(f" ⚠️ exiftool bash parser failed: {e}.")
            
    return None

def chunk_text_semantically(text: str, chunk_size: int = 1500, overlap: int = 300) -> list:
    """Splits raw text into overlapping semantic paragraphs/sections."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = len(para)
        
        if current_size + para_len > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            overlap_candidates = []
            overlap_size = 0
            for c_para in reversed(current_chunk):
                if overlap_size + len(c_para) < overlap:
                    overlap_candidates.insert(0, c_para)
                    overlap_size += len(c_para)
                else:
                    break
            current_chunk = overlap_candidates
            current_size = overlap_size
            
        current_chunk.append(para)
        current_size += para_len
        
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def select_relevant_chunks(chunks: list, query: str, top_n: int = 3) -> str:
    """Ranks semantic chunks by keyword/query match density and returns the top N chunks with visual boundaries."""
    if not query or not chunks:
        return "\n\n".join(chunks)
        
    query_words = [w.lower() for w in query.split() if len(w) > 2]
    if not query_words:
        return "\n\n".join(chunks[:top_n])
        
    chunk_scores = []
    for i, chunk in enumerate(chunks):
        chunk_lower = chunk.lower()
        score = 0
        for word in query_words:
            score += chunk_lower.count(word) * 2
            if query.lower() in chunk_lower:
                score += 10
        chunk_scores.append((score, i, chunk))
        
    chunk_scores.sort(key=lambda x: (-x[0], x[1]))
    
    selected = []
    top_selections = chunk_scores[:top_n]
    has_positive_scores = any(s[0] > 0 for s in top_selections)
    if has_positive_scores:
        top_selections = [s for s in top_selections if s[0] > 0]
        
    top_selections.sort(key=lambda x: x[1])
    
    for score, idx, chunk in top_selections:
        selected.append(f"=== [Section {idx+1} (Relevance Score: {score})] ===\n{chunk}")
        
    if not selected:
        return "[No direct matches found for your query within the document context.]"
        
    header = f"💡 [Note: Document context optimized. Displaying top {len(selected)} most relevant sections for query: '{query}']\n\n"
    return header + "\n\n".join(selected)

def read_sharepoint_file_api(item_id: str, query: str = "", drive_id: str = None) -> str:
    """Downloads and returns the text content of a file from SharePoint, optionally filtering relevant chunks."""
    config = load_config()
    token = get_access_token(config)
    
    if not drive_id:
        site_id = get_site_id(token, config["SHAREPOINT_SITE_HOST"], config["SHAREPOINT_SITE_PATH"])
        drive_id = get_default_drive_id(token, site_id)
    
    metadata_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
    headers = {"Authorization": f"Bearer {token}"}
    metadata_response = requests.get(metadata_url, headers=headers)
    
    if metadata_response.status_code != 200:
        raise Exception(f"Failed to fetch file metadata: {metadata_response.status_code} - {metadata_response.text}")
        
    metadata = metadata_response.json()
    if "folder" in metadata:
        return "[Error: The requested item is a folder, not a file.]"
        
    name = metadata.get("name", "")
    
    content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
    content_response = requests.get(content_url, headers=headers)
    
    if content_response.status_code != 200:
        raise Exception(f"Failed to download file content: {content_response.status_code} - {content_response.text}")
        
    file_bytes = content_response.content
    
    ext = name.split(".")[-1].lower() if "." in name else ""
    
    # 1. Try Upgrade A (Bash-Native subprocess parsing)
    raw_text = parse_file_via_bash(file_bytes, ext)
    
    # 2. Fallback to Python-native parsers if bash parsers are not present or fail
    if raw_text is None:
        if ext == "docx":
            raw_text = extract_text_from_docx(file_bytes)
        elif ext == "pdf":
            raw_text = extract_text_from_pdf(file_bytes)
        elif ext == "pptx":
            raw_text = extract_text_from_pptx(file_bytes)
        elif ext == "xlsx":
            raw_text = extract_text_from_xlsx(file_bytes)
        elif ext in ["txt", "md", "json", "csv", "xml", "html", "sh", "py", "js", "css"]:
            raw_text = file_bytes.decode("utf-8", errors="replace")
        else:
            raw_text = f"[File type .{ext} is not directly readable as text. File Name: {name}, Size: {len(file_bytes)} bytes.]"
            
    # 3. Apply Upgrade B (Smart semantic chunking and context relevance routing)
    if query and not raw_text.startswith("[Error") and not raw_text.startswith("[File type"):
        chunks = chunk_text_semantically(raw_text)
        return select_relevant_chunks(chunks, query)
        
    return raw_text

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts clean text pages from a PDF binary stream using pypdf."""
    import pypdf
    from io import BytesIO
    try:
        reader = pypdf.PdfReader(BytesIO(file_bytes))
        text_pages = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_pages.append(f"--- Page {i+1} ---\n{page_text}")
        return "\n\n".join(text_pages)
    except Exception as e:
        return f"[Error parsing PDF file: {str(e)}]"

def extract_text_from_pptx(file_bytes: bytes) -> str:
    """Extracts clean text from a PPTX binary stream slide-by-slide using standard libraries."""
    import zipfile
    import xml.etree.ElementTree as ET
    from io import BytesIO
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as pptx:
            slide_files = [name for name in pptx.namelist() if name.startswith('ppt/slides/slide') and name.endswith('.xml')]
            slide_files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))
            
            ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
            slides_text = []
            
            for i, slide_file in enumerate(slide_files):
                xml_content = pptx.read(slide_file)
                root = ET.fromstring(xml_content)
                
                slide_runs = []
                for p in root.findall('.//a:p', ns):
                    texts = [t.text for t in p.findall('.//a:t', ns) if t.text]
                    if texts:
                        slide_runs.append("".join(texts))
                        
                if slide_runs:
                    slides_text.append(f"--- Slide {i+1} ---\n" + "\n".join(slide_runs))
                    
            return "\n\n".join(slides_text)
    except Exception as e:
        return f"[Error parsing PPTX file: {str(e)}]"

def extract_text_from_xlsx(file_bytes: bytes) -> str:
    """Extracts clean text from a XLSX spreadsheet sheet-by-sheet using standard libraries."""
    import zipfile
    import xml.etree.ElementTree as ET
    from io import BytesIO
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as xlsx:
            # 1. Load Shared Strings table
            shared_strings = []
            if 'xl/sharedStrings.xml' in xlsx.namelist():
                ss_content = xlsx.read('xl/sharedStrings.xml')
                ss_root = ET.fromstring(ss_content)
                ns_ss = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in ss_root.findall('.//ns:si', ns_ss):
                    t_el = si.find('ns:t', ns_ss)
                    shared_strings.append(t_el.text if t_el is not None and t_el.text else "")
            
            # 2. Find sheet XMLs
            sheet_files = [name for name in xlsx.namelist() if name.startswith('xl/worksheets/sheet') and name.endswith('.xml')]
            sheet_files.sort()
            
            sheets_text = []
            ns_s = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            for i, sheet_file in enumerate(sheet_files):
                sheet_content = xlsx.read(sheet_file)
                root = ET.fromstring(sheet_content)
                
                rows = []
                for r in root.findall('.//ns:row', ns_s):
                    row_cells = []
                    for c in r.findall('ns:c', ns_s):
                        t = c.get('t')
                        v_el = c.find('ns:v', ns_s)
                        val = ""
                        if v_el is not None and v_el.text:
                            val = v_el.text
                            if t == 's':
                                try:
                                    idx = int(val)
                                    val = shared_strings[idx]
                                except Exception:
                                    pass
                        row_cells.append(val)
                    if any(row_cells):
                        rows.append(" | ".join(row_cells))
                
                if rows:
                    sheets_text.append(f"--- Sheet {i+1} ---\n" + "\n".join(rows))
            
            return "\n\n".join(sheets_text)
    except Exception as e:
        return f"[Error parsing XLSX file: {str(e)}]"

def get_file_permissions_api(item_id: str, drive_id: str = None) -> list:
    """Retrieves access permissions for a specific file in SharePoint Document Library."""
    config = load_config()
    token = get_access_token(config)
    
    if not drive_id:
        site_id = get_site_id(token, config["SHAREPOINT_SITE_HOST"], config["SHAREPOINT_SITE_PATH"])
        drive_id = get_default_drive_id(token, site_id)
        
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/permissions"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        permissions = response.json().get("value", [])
        results = []
        for perm in permissions:
            granted_to = perm.get("grantedTo", {})
            user = granted_to.get("user", {})
            group = granted_to.get("group", {})
            
            principal_name = "Unknown"
            principal_email = "-"
            principal_type = "Unknown"
            
            if user:
                principal_name = user.get("displayName", "Unknown User")
                principal_email = user.get("email", "-")
                principal_type = "User"
            elif group:
                principal_name = group.get("displayName", "Unknown Group")
                principal_type = "Group"
                
            link = perm.get("link", {})
            link_url = "-"
            link_scope = "-"
            if link:
                link_url = link.get("webUrl", "-")
                link_scope = link.get("scope", "-")
                principal_name = f"Sharing Link ({link.get('type', 'view')})"
                principal_type = "Link"
                
            results.append({
                "id": perm.get("id"),
                "name": principal_name,
                "email": principal_email,
                "type": principal_type,
                "roles": perm.get("roles", []),
                "link_url": link_url,
                "link_scope": link_scope
            })
        return results
    else:
        raise Exception(f"Failed to retrieve file permissions: {response.status_code} - {response.text}")






