# SharePoint File Lister & Searcher ADK Agent

This project implements an enterprise-ready Agent Development Kit (ADK) assistant that allows listing, searching, browsing, and reading files in a SharePoint site document library. It features advanced integration with Microsoft Purview Sensitivity Labels, robust region-routed search pipelines, and dependency-free file content extraction.

---

## 📁 File Structure

- **`config.json`**: Configuration file for Microsoft Azure AD, SharePoint site details, Gemini model name, and GCP project specs (excluded from Git).
- **`deploy_ge_ae/.env`**: Environment configuration file storing SharePoint tenant/client credentials for cloud deployment (excluded from Git).
- **`sharepoint_client.py`**: Core helper library containing Graph API interactions, regional search query execution, file content downloading, and Word document parsing.
- **`agent.py`**: The main ADK agent instruction set, custom tool registration (`list_sharepoint_files`, `search_sharepoint_files`, `read_sharepoint_file`), and advanced Markdown visual formatting rules.
- **`runner.py`**: Interactive and command-line CLI agent chat runner.
- **`agent_tests/`**: Directory containing specialized conversational verification scripts for testing Word, PDF, PowerPoint, Excel, and file permissions workflows.
- **`sharepoint_agent_walkthrough.md`**: Comprehensive walkthrough of SharePoint OAuth registration, Graph API permission setup, and configuration steps.
- **`harness/`**: At-scale automated evaluation harness including dataset generator (`generate_dataset.py`) and Gemini-graded regression runner (`run_eval.py`).
- **`stats/`**: SharePointDocument library recursively walks sizing, Purview classifications, file extensions compilation, and Matplotlib graph plotters.
- **`analyse_conflict/`**: Semantic contradiction auditing utility that builds a factual statement index and groups policy conflict statements using Vertex AI Gemini.
- **`deploy_ge_ae/`**: Self-contained deployment package containing environment configuration, build ignores, and automated shell scripts for deploying the ADK Agent to Gemini Enterprise Agent Engine.
- **`mock_data/`**: Unique banking dataset generation scripts and MSAL token-refresh SharePoint file uploaders.
- **`.gitignore`**: Pre-configured git ignore rules to protect credentials (`config.json`, `.env`) and python artifacts.

---

## ✨ Core Features

### 🔍 Dual-Stage Fast Search
Avoids slow recursive folder scanning. The agent uses the modern Microsoft Graph `/search/query` endpoint with APC (Asia-Pacific) regional routing to locate files instantly across the entire site. It then makes a fast, direct call to retrieve the unique sensitivity labels.

### 🛡️ Purview Sensitivity Labels
Automatically retrieves and displays Microsoft Purview information protection sensitivity levels (e.g., `General`, `Confidential`, `Highly Confidential`) next to each file, categorized with intuitive status emojis (🟢, 🟡, 🔴).

### 📖 High-Speed Bash Parsers & Smart Context Chunker
*   **Bash-Native Subprocess Parsing**: Spawns high-speed, native command-line parsers (e.g., `pdftotext` for PDFs, `docx2txt` for Word, and `exiftool` for images/media) via Python subprocesses. Automatically falls back to robust Python-native parsers if bash utilities are absent in the host environment, guaranteeing universal execution.
*   **Semantic Relevance Chunker**: Implements a keyword match density chunker. Instead of loading an entire large file (e.g., a 50-page document) into the context window, it splits text into overlapping semantic paragraphs, scores them dynamically against the user's context query, and streams only the top 3 most relevant segments—minimizing LLM execution costs by **95%+** and completely preventing context window overflow.

### 🧪 At-Scale Regression Evaluation Harness
Includes a robust, automated regression testing suite. It uses a crawler script (`harness/generate_dataset.py`) to recursively scan your SharePoint library and compile structured test cases, then executes persistent conversational turns through the ADK Agent (`harness/run_eval.py`), automatically score-judging answering accuracy, trajectory correctness, and LLM context cost parameters via a Gemini judge.

### 🔐 RMS Encryption Awareness
*   **RMS-Protected Files**: Correctly identifies and handles files encrypted with Microsoft Information Protection (MIP) / Rights Management Services (RMS) based on metadata inspection before downloading content, safely reporting encryption constraints if a protected file cannot be opened.

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
python agent_tests/test_docx.py

# Test PDF (.pdf) page-by-page extraction
python agent_tests/test_pdf.py

# Test PowerPoint (.pptx) slide-by-slide parsing
python agent_tests/test_pptx.py

# Test Excel (.xlsx) spreadsheet analytical insights
python agent_tests/test_xlsx.py

# Test SharePoint Direct File Permissions Auditing
python agent_tests/test_permissions_agent.py
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

### 7. Deploy to Gemini Enterprise Agent Engine
To package and deploy this ADK Agent to Google Cloud's Gemini Enterprise Agent Engine (Reasoning Engine), follow the self-contained instructions inside the deployment folder:
*   **[deploy_ge_ae/README.md](deploy_ge_ae/README.md)**: Comprehensive walkthrough on configuring your environment variables and triggering the automated one-click deployment script.

> [!NOTE]
> **Dual-Environment Aware Configuration Architecture**: The agent helper `sharepoint_client.py` automatically checks for environment variables (`TENANT_ID`, `CLIENT_ID`, etc.) set dynamically by Agent Engine in the cloud, and seamlessly falls back to the local `config.json` file only when running locally. This prevents packaging hardcoded credentials into your staged build uploads.


