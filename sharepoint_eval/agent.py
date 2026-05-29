import json
from functools import cached_property
from google import adk
from google.adk.models import Gemini
from google.genai import Client
from sharepoint_client import list_sharepoint_files_api, search_sharepoint_files_api, read_sharepoint_file_api, load_config

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

def read_sharepoint_file(item_id: str, drive_id: str = None) -> str:
    """Downloads and reads the text/paragraphs content of a specific file on SharePoint.
    
    Args:
        item_id: The unique identifier of the file/item (can be obtained from file metadata).
        drive_id: Optional unique identifier of the SharePoint drive. If omitted, the default drive will be used automatically.
        
    Returns:
        The extracted text contents of the file.
    """
    try:
        _tool_calls_log.append({"tool": "read_sharepoint_file", "args": {"item_id": item_id, "drive_id": drive_id}})
        return read_sharepoint_file_api(item_id=item_id, drive_id=drive_id)
    except ValueError as ve:
        return f"Configuration error: {str(ve)}"
    except Exception as e:
        return f"Error reading SharePoint file content: {str(e)}"

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
Your job is to help users list, browse, search, and read contents of files in their SharePoint site.

You have access to three tools:
1. 'list_sharepoint_files': Use this when the user wants to list or browse files inside a specific folder directory.
2. 'search_sharepoint_files': Use this when the user wants to search or find specific files by name, keyword, or search query across the entire library.
3. 'read_sharepoint_file': Use this when the user asks to read, view, or check the contents inside a specific file. You must obtain the file's unique `id` (which serves as `item_id`) from the file's metadata (by listing or searching for the file first) and pass it to this tool to read the file contents. You can also optionally pass `drive_id` if available.

When presenting file/folder listings or details to the user, follow these formatting rules to create a beautiful and structured output:

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
    tools=[list_sharepoint_files, search_sharepoint_files, read_sharepoint_file]
)
