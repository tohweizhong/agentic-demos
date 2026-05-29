# SharePoint File Lister & Searcher ADK Agent

This project implements an enterprise-ready Agent Development Kit (ADK) assistant that allows listing, searching, browsing, and reading files in a SharePoint site document library. It features advanced integration with Microsoft Purview Sensitivity Labels, robust region-routed search pipelines, and dependency-free file content extraction.

---

## 📁 File Structure

- **`config.json`**: Configuration file for Microsoft Azure AD, SharePoint site details, Gemini model name, and GCP project specs (excluded from Git).
- **`sharepoint_client.py`**: Core helper library containing Graph API interactions, regional search query execution, file content downloading, and Word document parsing.
- **`agent.py`**: The main ADK agent instruction set, custom tool registration (`list_sharepoint_files`, `search_sharepoint_files`, `read_sharepoint_file`), and advanced Markdown visual formatting rules.
- **`runner.py`**: Interactive and command-line CLI agent chat runner.
- **`test_agent.py`**: Automated evaluation script to execute multi-step conversational scenarios inside persistent sessions.
- **`sharepoint_lister_walkthrough.md`**: Comprehensive walkthrough of SharePoint OAuth registration, Graph API permission setup, and configuration steps.
- **`.gitignore`**: Pre-configured git ignore rules to protect credentials (`config.json`) and python artifacts.

---

## ✨ Core Features

### 🔍 Dual-Stage Fast Search
Avoids slow recursive folder scanning. The agent uses the modern Microsoft Graph `/search/query` endpoint with APC (Asia-Pacific) regional routing to locate files instantly across the entire site. It then makes a fast, direct call to retrieve the unique sensitivity labels.

### 🛡️ Purview Sensitivity Labels
Automatically retrieves and displays Microsoft Purview information protection sensitivity levels (e.g., `General`, `Confidential`, `Highly Confidential`) next to each file, categorized with intuitive status emojis (🟢, 🟡, 🔴).

### 📖 Dependency-Free File Reader & Document Parsers
Extracts clean text paragraphs from Word documents (`.docx`), slide contents from PowerPoint presentations (`.pptx`), cell grids from Excel spreadsheets (`.xlsx`), and text files (`.txt`, `.md`, `.json`, `.csv`, etc.) on the fly using Python’s standard library (`zipfile` and `xml.etree.ElementTree`), avoiding any extra pip dependencies.

### 🔐 RMS Encryption Awareness
Correctly identifies and handles files encrypted with Microsoft Information Protection (MIP) / Rights Management Services (RMS), safely reporting encryption constraints if a protected file cannot be opened.

### 🎨 Premium Markdown Formatting
Outputs beautiful, responsive Markdown tables with clickable Web URLs, specific emojis for folders vs. files, code block wrappers for relative paths, and clean human-readable file sizes.

---

## 🚀 Setup & Usage

Please follow the step-by-step instructions inside [sharepoint_agent_walkthrough.md](sharepoint_agent_walkthrough.md) to register your app in Azure AD and acquire your credentials.

### 1. Install Dependencies
Ensure you have Python 3.11+ and your virtual environment activated, then install the packages:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install google-adk msal
```

### 2. Authenticate with Google Cloud Application Default Credentials (ADC)
Before running the agent, authenticate with Google Cloud to enable the Gemini LLM via Vertex AI:
```bash
gcloud auth application-default login
```

### 3. Run the Interactive CLI
```bash
python runner.py
```

### 4. Run Automated Conversational Tests
To execute targeted, multi-turn conversational scripts with persistent memory on specific file types, run:
```bash
# Test Word (.docx) parsing and context
python test_docx.py

# Test PDF (.pdf) page-by-page extraction
python test_pdf.py

# Test PowerPoint (.pptx) slide-by-slide parsing
python test_pptx.py

# Test Excel (.xlsx) spreadsheet analytical insights (weekends vs weekdays)
python test_xlsx.py
```
