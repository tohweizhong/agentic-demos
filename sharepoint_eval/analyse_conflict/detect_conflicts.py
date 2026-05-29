import sys
import os
import json
import time
from google.genai import Client

# Add sharepoint_eval to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sharepoint_client import (
    load_config,
    get_access_token,
    get_site_id,
    get_default_drive_id,
    get_all_files_recursive,
    read_sharepoint_file_api
)

# Initialize Gemini Client
try:
    config = load_config()
    project = config.get("GCP_PROJECT_ID")
    location = config.get("GCP_LOCATION")
    model_name = config.get("MODEL_NAME", "gemini-2.5-flash")
except Exception:
    project = None
    location = None
    model_name = "gemini-2.5-flash"

kwargs = {"vertexai": True}
if project:
    kwargs["project"] = project
if location:
    kwargs["location"] = location
    
gemini_client = Client(**kwargs)

def extract_key_statements(filename: str, content: str) -> str:
    """Uses Gemini to extract the core policy statements, guidelines, or key facts from a document snippet."""
    prompt = f"""
    You are an Expert Document Auditor. Extract a bulleted list of the core policy rules, guidelines, operating procedures, or factual commitments outlined in the document '{filename}'.
    Keep your summary extremely concise, focusing exclusively on actionable statements, guidelines, or key factual claims that could potentially conflict with other documents.
    
    Document Content Snippet:
    ---
    {content[:2500]}
    ---
    
    Provide a bulleted list of maximum 4 key statements/rules:
    """
    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error extracting statements: {e}"

def perform_semantic_conflict_audit(document_index: list) -> str:
    """Sends the collated index of all key document statements to Gemini to identify content clusters and contradictions."""
    prompt = f"""
    You are an Enterprise Data Integrity Auditor. Your task is to analyze the following index of document statements collected from a SharePoint site.
    Perform the following audits:
    
    1. **Semantic Content Clustering**: Group the documents into 3-5 logical semantic clusters (topics) based on their contents.
    2. **Contradiction & Conflict Auditing**: Inside each cluster, carefully scan and compare the statements across files. Identify any direct contradictions, conflicting guidelines, or conflicting factual statements (e.g., one policy document stating a rule that another document disagrees with, or differing technical specifications for the same system).
    
    Here is the Document Statement Index:
    {json.dumps(document_index, indent=2)}
    
    Please format your audit report beautifully in Markdown.
    Under the "Contradiction & Conflict Auditing" section, clearly highlight:
    * **Conflict Title**: E.g., "Conflict on Remote Work Policy" or "Discrepancy in Encryption Standards"
    * **Conflicting Files**: A bulleted list of the file paths.
    * **The Conflict**: A clear, concise explanation of the contradiction, quoting or referencing the exact statements.
    * **Recommended Action**: How an organization can resolve this discrepancy.
    
    If absolutely no semantic conflicts or contradictions are found, state that the repository is semantically clean and aligned.
    """
    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Audit analysis failed: {e}"

def main():
    print("Connecting to SharePoint...")
    config = load_config()
    token = get_access_token(config)
    site_id = get_site_id(token, config["SHAREPOINT_SITE_HOST"], config["SHAREPOINT_SITE_PATH"])
    drive_id = get_default_drive_id(token, site_id)
    
    print("Scanning document library recursively...")
    files = get_all_files_recursive(token, drive_id, "root", "")
    files = [f for f in files if f.get("type") == "file"]
    print(f"Found {len(files)} total files to index.")
    
    document_index = []
    processed_count = 0
    # Focus on unencrypted document files for deep semantic analysis
    target_extensions = ["docx", "pptx", "pdf", "txt", "csv"]
    
    for i, file in enumerate(files):
        name = file.get("name")
        path = file.get("path")
        item_id = file.get("id")
        label = file.get("sensitivity_label")
        ext = name.split(".")[-1].lower() if "." in name else ""
        
        # Skip encrypted/restricted files since they cannot be read
        is_encrypted = False
        if label and any(kw in label.lower() for kw in ["confidential", "restricted"]):
            is_encrypted = True
            
        if ext not in target_extensions or is_encrypted:
            continue
            
        print(f"[{processed_count+1}] Extracting key statements from unencrypted document: '{name}'...")
        try:
            content = read_sharepoint_file_api(item_id=item_id, drive_id=drive_id)
            # Parse standard text output
            if content and not content.startswith("[File type") and not content.startswith("[Error"):
                statements = extract_key_statements(name, content)
                document_index.append({
                    "filename": name,
                    "path": path,
                    "sensitivity_label": label or "None",
                    "key_statements": statements
                })
                processed_count += 1
        except Exception as e:
            print(f"Error processing {name}: {e}")
            continue
            
    print(f"\nExtraction completed. Collated {processed_count} documents in the index.")
    
    print("Running Semantic Conflict and Clustering Audit via Gemini LLM...")
    audit_report = perform_semantic_conflict_audit(document_index)
    
    conflict_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(conflict_dir, "semantic_conflicts_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(audit_report)
        
    json_path = os.path.join(conflict_dir, "semantic_conflicts.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(document_index, f, indent=2)
        
    print(f"\n========================================")
    print(f"        Audit Complete!")
    print(f"========================================")
    print(f"Detailed audit report written to: {report_path}")
    print(f"Factual document statements index: {json_path}")

if __name__ == "__main__":
    main()
