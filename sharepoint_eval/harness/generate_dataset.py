import sys
import os
import csv
import json
import requests
from google.genai import Client

# Add sharepoint_eval to path to import clients
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sharepoint_client import (
    load_config,
    get_access_token,
    get_site_id,
    get_default_drive_id,
    list_children,
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

def generate_qa_from_content(filename: str, text: str) -> tuple:
    """Uses Gemini to generate a highly specific query and expected response from file content."""
    prompt = f"""
    You are a Benchmark Dataset Generator. Based on the extracted text content from the file '{filename}', 
    generate a single specific, natural question (query) a user might ask about the factual content or insights inside this document.
    Also, generate a precise, factual expected response (answer) to that question.
    
    Extracted Text Content (Snippet):
    ---
    {text[:1500]}
    ---
    
    Return your output strictly as a JSON object matching this format:
    {{
        "query": "Your generated question here",
        "expected_response": "Your generated precise answer here"
    }}
    """
    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        res = json.loads(response.text)
        return res.get("query"), res.get("expected_response")
    except Exception as e:
        return f"Summarize the contents of {filename}", f"This document describes details of {filename}."

def main():
    print("Fetching all files from SharePoint...")
    config = load_config()
    token = get_access_token(config)
    site_id = get_site_id(token, config["SHAREPOINT_SITE_HOST"], config["SHAREPOINT_SITE_PATH"])
    drive_id = get_default_drive_id(token, site_id)
    
    # Get all files recursively
    files = get_all_files_recursive(token, drive_id, "root", "")
    print(f"Retrieved {len(files)} total items from SharePoint.")
    
    # Filter folders out
    files = [f for f in files if f.get("type") == "file"]
    print(f"Found {len(files)} files to process.")
    
    harness_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(harness_dir, "evaluation_dataset.csv")
    
    headers = [
        "query", 
        "expected_response", 
        "expected_tool_trajectory", 
        "source", 
        "file_type", 
        "sensitivity_label", 
        "is_encrypted"
    ]
    
    records_count = 0
    limit = 100
    
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i, file in enumerate(files):
            if records_count >= limit:
                break
                
            name = file.get("name")
            path = file.get("path")
            item_id = file.get("id")
            label = file.get("sensitivity_label")
            ext = name.split(".")[-1].lower() if "." in name else ""
            
            # Check if file is encrypted (Confidential or Highly Confidential Purview labels)
            is_encrypted = False
            if label and any(kw in label.lower() for kw in ["confidential", "restricted"]):
                is_encrypted = True
                
            print(f"[{records_count+1}/{limit}] Processing '{name}' (Label: {label}, Encrypted: {is_encrypted})...")
            
            if is_encrypted:
                # Encrypted file expected behavior
                query = f"Summarize the contents of {name}"
                expected_response = (
                    f"I apologize, but I encountered an error when trying to read the content of `{path}`. "
                    f"The file is protected by a Microsoft Purview Sensitivity Label and is encrypted. "
                    f"I am unable to parse its contents."
                )
                trajectory = [
                    {"tool": "search_sharepoint_files", "args": {"query": name}},
                    {"tool": "read_sharepoint_file", "args": {"item_id": item_id}}
                ]
                writer.writerow([
                    query,
                    expected_response,
                    json.dumps(trajectory),
                    path,
                    ext,
                    label or "None",
                    "True"
                ])
                records_count += 1
            else:
                # Unencrypted file
                try:
                    content = read_sharepoint_file_api(item_id=item_id, drive_id=drive_id)
                    # If we successfully parsed contents
                    if content and not content.startswith("[File type") and not content.startswith("[Error"):
                        # Generate Q&A from contents using Gemini
                        query, expected_response = generate_qa_from_content(name, content)
                        
                        trajectory = [
                            {"tool": "search_sharepoint_files", "args": {"query": name}},
                            {"tool": "read_sharepoint_file", "args": {"item_id": item_id}}
                        ]
                        writer.writerow([
                            query,
                            expected_response,
                            json.dumps(trajectory),
                            path,
                            ext,
                            label or "None",
                            "False"
                        ])
                        records_count += 1
                    else:
                        # For files we can't read directly as text (like images or generic types)
                        query = f"What are the details of the file {name}?"
                        expected_response = f"File '{name}' is located at path `{path}` with a size of {file.get('size', 0)} bytes."
                        trajectory = [
                            {"tool": "search_sharepoint_files", "args": {"query": name}}
                        ]
                        writer.writerow([
                            query,
                            expected_response,
                            json.dumps(trajectory),
                            path,
                            ext,
                            label or "None",
                            "False"
                        ])
                        records_count += 1
                except Exception as e:
                    print(f"Skipping {name} due to read error: {e}")
                    continue
                    
    print(f"\nSuccessfully generated evaluation dataset with {records_count} rows at {csv_path}!")

if __name__ == "__main__":
    main()
