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

Please follow the step-by-step instructions inside the walkthrough guides:
*   **[sharepoint_agent_walkthrough.md](sharepoint_agent_walkthrough.md)**: Covers setting up Azure AD App registrations, permissions, credentials, and running the CLI agent.
*   **[harness/README.md](harness/README.md)**: Covers generating the benchmark CSV and executing the automated Evaluation Harness.
*   **[stats/README.md](stats/README.md)**: Covers calculating SharePoint metrics and plotting Matplotlib size/sensitivity/extension distribution charts.
*   **[analyse_conflict/README.md](analyse_conflict/README.md)**: Covers building the factual statement index and executing the semantic contradictions/conflicts audit.

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

### 5. Run SharePoint Content & Cleanliness Audit
To recursively analyze your SharePoint Document Library and generate a high-level report on file sizing, Purview sensitivity labels, file suffixes, and data cleanliness:
```bash
python stats/collate_stats.py
```
Detailed output is saved to `stats/sharepoint_contents_report.md` and raw JSON metrics to `stats/sharepoint_contents_stats.json`.

### 6. Run Semantic Contradiction & Conflict Audit
To recursively traverse SharePoint, build a factual statement index from all unencrypted documents, and perform a semantic auditing run to identify file clusters and policy contradictions:
```bash
python analyse_conflict/detect_conflicts.py
```
Detailed report is saved to `analyse_conflict/semantic_conflicts_report.md` and raw JSON statements to `analyse_conflict/semantic_conflicts.json`.
