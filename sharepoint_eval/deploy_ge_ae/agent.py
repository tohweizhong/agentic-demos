import json
import os
import sys
from functools import cached_property

# Dynamically add this staged directory to sys.path to resolve sharepoint_client absolute imports in the cloud container
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google import adk
from google.adk.models import Gemini
from google.genai import Client
from sharepoint_client import list_sharepoint_files_api, search_sharepoint_files_api, read_sharepoint_file_api, get_file_permissions_api, load_config

# Global list to log tool calls (used for evaluation harnesses)
_tool_calls_log = []

# Define the tool function that the ADK agent will use
def list_sharepoint_files(folder_path: str = "", recursive: bool = False) -> str:
    """Lists files and folders in the configured SharePoint site document library.
    
    Args:
        folder_path: Optional relative folder path (e.g. 'Invoices/2026' or 'General'). If empty, lists from the root folder.
        recursive: If True, lists all files and folders recursively. If False, only lists direct children.
        
    Returns:
        A JSON formatted string list of files/folders, containing name, type, size, last modified time, path, and web URL.
    """
    try:
        _tool_calls_log.append({"tool": "list_sharepoint_files", "args": {"folder_path": folder_path, "recursive": recursive}})
        files = list_sharepoint_files_api(folder_path=folder_path, recursive=recursive)
        if not files:
            return "No files or folders found."
        return json.dumps(files, indent=2)
    except ValueError as ve:
        return f"Configuration error: {str(ve)}"
    except Exception as e:
        return f"Error listing SharePoint files: {str(e)}"

def search_sharepoint_files(query: str) -> str:
    """Searches for files and folders in the SharePoint site document library matching the query string.
    
    Args:
        query: The search term, filename, or keyword to look for (e.g. 'test2.docx' or 'SDP').
        
    Returns:
        A JSON formatted string list of matching files/folders, containing name, type, size, last modified time, path, web URL, and sensitivity label.
    """
    try:
        _tool_calls_log.append({"tool": "search_sharepoint_files", "args": {"query": query}})
        files = search_sharepoint_files_api(query=query)
        if not files:
            return f"No files or folders found matching '{query}'."
        return json.dumps(files, indent=2)
    except ValueError as ve:
        return f"Configuration error: {str(ve)}"
    except Exception as e:
        return f"Error searching SharePoint files: {str(e)}"

def read_sharepoint_file(item_id: str, query: str = "", drive_id: str = None) -> str:
    """Downloads and reads the text/paragraphs content of a specific file on SharePoint, optionally optimizing standard context footprint.
    
    Args:
        item_id: The unique identifier of the file/item (can be obtained from file metadata).
        query: Optional search term or question you are looking for inside the document (e.g., 'LCR variance limit'). If provided, the tool returns only the top 3 most relevant sections to prevent context window overflow.
        drive_id: Optional unique identifier of the SharePoint drive. If omitted, the default drive will be used automatically.
        
    Returns:
        The extracted text contents of the file.
    """
    try:
        _tool_calls_log.append({"tool": "read_sharepoint_file", "args": {"item_id": item_id, "query": query, "drive_id": drive_id}})
        return read_sharepoint_file_api(item_id=item_id, query=query, drive_id=drive_id)
    except ValueError as ve:
        return f"Configuration error: {str(ve)}"
    except Exception as e:
        return f"Error reading SharePoint file content: {str(e)}"

def list_file_permissions(item_id: str, drive_id: str = None) -> str:
    """Retrieves and lists the access permissions, sharing settings, and users who can access a specific file.
    
    Args:
        item_id: The unique identifier of the file (can be obtained from file metadata).
        drive_id: Optional unique identifier of the SharePoint drive containing the file.
        
    Returns:
        A JSON formatted string list of permissions, users, groups, roles, and sharing links.
    """
    try:
        _tool_calls_log.append({"tool": "list_file_permissions", "args": {"item_id": item_id, "drive_id": drive_id}})
        perms = get_file_permissions_api(item_id=item_id, drive_id=drive_id)
        if not perms:
            return "No access permissions found for this file."
        return json.dumps(perms, indent=2)
    except ValueError as ve:
        return f"Configuration error: {str(ve)}"
    except Exception as e:
        return f"Error listing file permissions: {str(e)}"

# Load model name from config, defaulting to gemini-2.5-flash
try:
    config = load_config()
    model_name = config.get("MODEL_NAME", "gemini-2.5-flash")
except Exception:
    model_name = "gemini-2.5-flash"

class VertexGemini(Gemini):
    @cached_property
    def api_client(self) -> Client:
        try:
            config = load_config()
            project = config.get("GCP_PROJECT_ID")
            location = config.get("GCP_LOCATION")
        except Exception:
            project = None
            location = None

        kwargs = {"vertexai": True}
        if project:
            kwargs["project"] = project
        if location:
            kwargs["location"] = location
            
        return Client(**kwargs)

# Define the ADK Agent
root_agent = adk.Agent(
    model=VertexGemini(model=model_name),
    name="sharepoint_file_lister",
    instruction="""You are a SharePoint File Lister assistant. 
Your job is to help users list, browse, search, read contents of files, and audit access permissions in their SharePoint site.

You have access to four tools:
1. 'list_sharepoint_files': Use this when the user wants to list or browse files inside a specific folder directory.
2. 'search_sharepoint_files': Use this when the user wants to search or find specific files by name, keyword, or search query across the entire library.
3. 'read_sharepoint_file': Use this when the user asks to read, view, or check the contents inside a specific file. You must obtain the file's unique `id` (which serves as `item_id`) from the file's metadata (by listing or searching for the file first) and pass it to this tool to read the file contents. You can also optionally pass `drive_id` if available.
4. 'list_file_permissions': Use this when the user asks who has access to a file, what sharing permissions are set on a file, or wants to audit file access permissions. You must obtain the file's unique `id` (which serves as `item_id`) from metadata first.

When presenting file/folder listings, details, or access permissions to the user, follow these formatting rules to create a beautiful and structured output:

### Formatting Rules for Listings (Multiple Items)
1. Use a **Markdown Table** with the following columns:
   * **Name**: Prefix with an emoji (📁 for folders, 📄 for files). Format the name as a clickable link pointing to the `web_url` (e.g., `[filename.pdf](web_url)`).
   * **Type**: `File` or `Folder`.
   * **Size**: Convert raw bytes into a human-readable format (e.g., `21.2 KB`, `1.5 MB`, or `-` for folders).
   * **Path**: Show the relative path inside an inline code block (e.g., `SDP tests/file.pdf` wrapped in backticks).
   * **Sensitivity**: Highlight the sensitivity label. Use emojis to indicate the level:
     * 🟢 `General` (or containing "General")
     * 🟡 `Confidential` (or containing "Confidential")
     * 🔴 `Highly Confidential` (or containing "Highly Confidential")
     * `-` if no label is set.
   * **Last Modified**: Format as a clean date/time string (e.g., `YYYY-MM-DD HH:MM`).

### Formatting Rules for File Access Permissions (Audits)
If the user asks to check permissions or see who has access to a file, present it in a beautiful **Markdown Table** showing:
*   **Principal**: The display name of the user, group, or sharing link scope (e.g., `Jane Doe`, `Administrators`, or `Sharing Link (view)`).
*   **Type**: The category of the principal (`User`, `Group`, or `Link`).
*   **Roles**: The permission level granted (e.g., `["read"]`, `["write"]`, `["owner"]`).
*   **Email**: The email of the user (or `-` if not applicable/available).
*   **Sharing Details**: The scope of the sharing link (e.g., `organization`, `users`, or `-` if a direct permission).

### Formatting Rules for a Single File's Details
If the user asks for detailed metadata of a specific file, present it in a structured **card-like key-value list**:
* **📄 File Name**: `[filename.docx](web_url)`
* **📁 Relative Path**: `SDP tests/filename.docx` (wrapped in backticks)
* **💾 File Size**: `21.2 KB`
* **🔒 Sensitivity**: 🟡 `Confidential \\ All Employees`
* **📅 Last Modified**: `2026-04-22 02:08`
* **🆔 Unique ID**: `01C6LRSENVG2...` (wrapped in backticks)

If you encounter a configuration error, politely inform the user to set up their 'config.json' file with valid tenant_id, client_id, client_secret, and SharePoint host/path details.
""",
    tools=[list_sharepoint_files, search_sharepoint_files, read_sharepoint_file, list_file_permissions]
)
