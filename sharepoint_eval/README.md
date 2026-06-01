# SharePoint ADK Agent

This project is an assistant built with the Agent Development Kit (ADK). It lets you list, search, browse, and read files in a SharePoint site document library. It can read Microsoft Purview Sensitivity Labels, run fast regional search pipelines, and extract file contents without extra setup.

---

## 📁 File Structure

- **`config.json`**: Settings for Microsoft Azure AD, SharePoint, Gemini, and GCP (ignored by Git).
- **`deploy_ge_ae/.env`**: Environment settings with credentials for cloud deployment (ignored by Git).
- **`sharepoint_client.py`**: Core helper to talk to Graph API, run search, download files, and parse documents.
- **`agent.py`**: Main agent instructions, tool registrations (`list_sharepoint_files`, `search_sharepoint_files`, `read_sharepoint_file`), and Markdown formatting rules.
- **`runner.py`**: Interactive command-line chat for the agent.
- **`agent_tests/`**: Tests to verify Word, PDF, PowerPoint, Excel, and file permissions.
- **`sharepoint_agent_walkthrough.md`**: Setup guide for Azure AD App registration, permissions, and config.
- **`harness/`**: Automated test harness with a dataset generator (`generate_dataset.py`) and a Gemini-graded evaluation runner (`run_eval.py`).
- **`stats/`**: Scripts to count file sizes, labels, and extensions, and plot graphs with Matplotlib.
- **`analyse_conflict/`**: Utility to find factual statements and group conflicting policy statements using Gemini.
- **`deploy_ge_ae/`**: Package and scripts to deploy the agent to Gemini Enterprise Agent Engine.
- **`mock_data/`**: Scripts to generate banking files and upload them to SharePoint.
- **`.gitignore`**: Rules to keep secrets (`config.json`, `.env`) and python files out of Git.

---

## ✨ Core Features

### 🔍 Fast Two-Step Search
The agent uses the modern Microsoft Graph search endpoint to find files instantly across the site. It then makes a direct call to get Purview sensitivity labels.

### 🛡️ Purview Sensitivity Labels
Shows Microsoft Purview labels (🟢 `General`, 🟡 `Confidential`, 🔴 `Highly Confidential`) next to each file using status emojis.

### 📖 Fast Subprocess Parsers & Smart Chunking
*   **Fast Subprocess Parsing**: Spawns fast, native command-line tools (`pdftotext` for PDFs, `docx2txt` for Word, and `exiftool` for media) to parse files. Falls back to Python libraries if these tools are missing, so it runs anywhere.
*   **Smart Chunking**: Splits large files into overlapping semantic paragraphs. Scores them against the user's query and sends only the top 3 most relevant segments to the LLM. This cuts token cost by **95%+** and stops context window overflow.

### 🧪 Automated Test Harness
Runs regression tests automatically. A crawler script (`harness/generate_dataset.py`) scans your SharePoint site to generate 100 test cases. The runner (`harness/run_eval.py`) executes these turns and uses Gemini as a judge to grade accuracy, tool paths, and token costs.

### 🔐 RMS Encryption Check
Inspects metadata *before* downloading files to check if they are encrypted with Microsoft Information Protection (MIP/RMS). Reports encryption constraints safely if a file is locked.

### 🎨 Clean Markdown Output
Displays responsive Markdown tables with clickable Web URLs, distinct emojis for files vs. folders, code blocks for paths, and clear file sizes.

---

## 🚀 Setup & Usage

Follow these step-by-step guides:
*   **[sharepoint_agent_walkthrough.md](sharepoint_agent_walkthrough.md)**: Setup guide for Azure AD, credentials, and running the CLI.
*   **[harness/README.md](harness/README.md)**: Guide to generate the CSV dataset and run the test harness.
*   **[stats/README.md](stats/README.md)**: Guide to count metrics and plot Matplotlib charts.
*   **[analyse_conflict/README.md](analyse_conflict/README.md)**: Guide to check for policy conflicts.

### 1. Install Dependencies
Make sure you have Python 3.11+ and your virtual environment is active, then run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install google-adk msal
```

### 2. Log In to Google Cloud (ADC)
Log in to enable Vertex AI and the Gemini LLM:
```bash
gcloud auth application-default login
```

### 3. Run the CLI
```bash
python runner.py
```

### 4. Run Conversational Tests
To test specific file types, run:
```bash
# Test Word (.docx)
python agent_tests/test_docx.py

# Test PDF (.pdf)
python agent_tests/test_pdf.py

# Test PowerPoint (.pptx)
python agent_tests/test_pptx.py

# Test Excel (.xlsx)
python agent_tests/test_xlsx.py

# Test SharePoint Permissions Audit
python agent_tests/test_permissions_agent.py
```

### 5. Run Cleanliness Audit
To scan SharePoint and generate a report on file sizes, sensitivity labels, and extensions:
```bash
python stats/collate_stats.py
```
Saves report to `stats/sharepoint_contents_report.md` and raw stats to `stats/sharepoint_contents_stats.json`.

### 6. Run Conflict Audit
To find conflicting facts across your documents:
```bash
python analyse_conflict/detect_conflicts.py
```
Saves report to `analyse_conflict/semantic_conflicts_report.md` and raw statements to `analyse_conflict/semantic_conflicts.json`.

### 7. Deploy to Gemini Enterprise Agent Engine
To deploy the agent to Google Cloud:
*   **[deploy_ge_ae/README.md](deploy_ge_ae/README.md)**: Guide to set environment variables and run the deploy script.

> [!NOTE]
> **Smart Credentials Check**: The agent checks for cloud environment variables first. If running locally, it falls back to `config.json`. This keeps your secrets out of your staged build uploads.
