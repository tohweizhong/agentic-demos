# 🚀 Gemini Enterprise Synthetic Prober (`ge-prober`)

A high-performance, containerized Go synthetic monitoring tool and smoke prober for **Gemini Enterprise (Discovery Engine)** applications and multimodal knowledge bases.

---

## 🎯 Supported Subsystems & Grounding Types

1. **Enterprise SharePoint & Microsoft 365 Connector** (`vertex_ai_search` + dataStore full resource paths)
2. **Deep Research Multi-Step Planning & Synthesis** (`deep_research_agent` via `agentsSpec` + `webGroundingSpec`)
3. **Gemini Notebook Knowledge Base Q&A** (`gemini_notebook` / `notebooklm` direct prompt)
4. **Public Google Search Web Grounding** (`google_search` via `webGroundingSpec`)

---

## 📝 Customizing & Adding Test Queries

You can easily customize queries or add new test cases in **2 ways**:

### Option 1: Edit the Default Test Suite
Edit [`test_cases/smoke_test_cases.json`](./test_cases/smoke_test_cases.json) directly.

Each test case adheres to the following structure:
```json
[
  {
    "id": "smoke_m365_sharepoint_01",
    "title": "SharePoint Document Retrieval",
    "subsystem": "sharepoint",
    "query": "Find the workplace policy document in our SharePoint site.",
    "grounding_type": "vertex_ai_search",
    "slo_targets": {
      "max_ttft_ms": 60000.0,
      "max_ttlt_ms": 90000.0
    },
    "assertions": {
      "must_contain_keywords": ["policy", "SharePoint"],
      "forbidden_errors": ["401", "403", "500", "503", "USER_PROJECT_DENIED"],
      "must_have_citations": true
    }
  }
]
```

### Option 2: Point to a Custom Test Catalog File
Maintain separate test suites (e.g. `prod_queries.json`, `hr_tests.json`) and pass the path using the `-test-cases` flag:

```bash
./ge-prober -test-cases="path/to/custom_queries.json"
```

Or configure it in your `.env`:
```bash
GE_TEST_CASES_PATH=path/to/custom_queries.json
```

### 📋 Grounding Type Reference:
| `grounding_type` | Subsystem Targeted | Backend Behavior |
| :--- | :--- | :--- |
| **`vertex_ai_search`** | Enterprise Connectors | Queries attached enterprise data stores (SharePoint, OneDrive, Confluence, Jira, BigQuery). |
| **`deep_research_agent`** | Deep Research Agent | Injects `agentsSpec: { agentSpecs: [{ agentId: "deep_research" }] }` with web grounding for multi-step research plans. |
| **`gemini_notebook`** | Gemini Notebook | Queries the notebook workspace knowledge base directly without external connectors. |
| **`web_search`** | Google Search | Injects `toolsSpec: { webGroundingSpec: {} }` for real-time public web search facts. |

---

## ⚙️ Configuration Methods (Choose What Works Best for You)

The prober resolves configuration following a strict **12-Factor hierarchy**:
$$\text{1. CLI Flags} > \text{2. Environment Variables} > \text{3. Local .env File} > \text{4. config.json} > \text{5. Defaults}$$

### Method 1: Using `config.json` (Recommended for Teams)
Create or copy [`config.example.json`](./config.example.json) to `config.json`:
```json
{
  "project_id": "YOUR_GCP_PROJECT_ID",
  "location": "global",
  "engine_id": "YOUR_GEMINI_ENTERPRISE_ENGINE_ID",
  "assistant_id": "default_assistant",
  "timeout_seconds": 180,
  "max_concurrency": 4,
  "data_store_ids": [
    "YOUR_DATA_STORE_ID_1",
    "YOUR_DATA_STORE_ID_2"
  ]
}
```
Run the prober:
```bash
./ge-prober
```

---

### Method 2: Using a Local `.env` File (Recommended for Developers)
Copy [`.env.example`](./.env.example) to `.env`:
```bash
GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID
GE_LOCATION=global
GE_ENGINE_ID=YOUR_GEMINI_ENTERPRISE_ENGINE_ID
GE_DATA_STORE_IDS=datastore_1,datastore_2
GE_MAX_CONCURRENCY=4
```
Run the prober:
```bash
./ge-prober
```

---

### Method 3: Direct Command-Line Flags (Instant One-Liner / CI/CD)
Pass all target parameters directly in your shell:
```bash
./ge-prober \
  -project="YOUR_GCP_PROJECT_ID" \
  -engine="YOUR_GEMINI_ENTERPRISE_ENGINE_ID" \
  -region="global" \
  -datastores="datastore_1,datastore_2" \
  -concurrency=4
```

#### Available CLI Flags:
| Flag | Description | Default |
| :--- | :--- | :--- |
| `-project` | Target GCP Project ID | From config / env |
| `-location` / `-region` | Engine location (`global`, `us`, `eu`, etc.) | `global` |
| `-engine` | Target Gemini Enterprise Engine / App ID | From config / env |
| `-assistant` | Assistant ID | `default_assistant` |
| `-datastores` | Comma-separated list of Data Store IDs | `""` |
| `-concurrency` | Number of concurrent workers | `4` |
| `-timeout` | Per-probe timeout in seconds | `180` |
| `-test-cases` | Path to custom test suite JSON file | `test_cases/smoke_test_cases.json` |
| `-output` | Path to export JSON results report | `smoke_prober_results.json` |
| `-config` | Path to custom JSON configuration file | `config.json` |
| `-token` | GCP Access token override | Automatic ADC / WIF |

---

### Method 4: Automated Daily Probing on Google Cloud Run
Deploy the prober as a serverless Cloud Run Job triggered daily by Cloud Scheduler:

```bash
export GCP_PROJECT_ID="YOUR_GCP_PROJECT_ID"
export GE_ENGINE_ID="YOUR_GEMINI_ENTERPRISE_ENGINE_ID"
export GE_LOCATION="global"

bash deploy_job.sh
```

To execute a probe run manually on Cloud Run anytime:
```bash
gcloud run jobs execute ge-prober-daily --project="YOUR_GCP_PROJECT_ID" --region="us-central1" --wait
```

---

## 🔐 Authentication
The prober automatically handles authentication:
1. **Local Workstations**: Automatically uses Application Default Credentials (`gcloud auth application-default login`).
2. **Cloud Run / GKE**: Automatically uses the attached Service Account metadata token.
3. **CI/CD / Workforce Identity**: Pass `$GCP_ACCESS_TOKEN` in the environment or `-token="ya29..."`.

---

## 📊 Sample Output
```
================================================================================
🚀 GEMINI ENTERPRISE SYNTHETIC SMOKE TEST PROBER (Go)
================================================================================
🎯 Target Project : my-gcp-project
📍 Location / Reg : global
⚙️ Target Engine  : my-gemini-app
📦 Smoke Probes   : 4 test cases
⚡ Concurrency    : 4 parallel workers
================================================================================

✅ [gemini_notebook] Gemini Notebook Knowledge Base Q&A     | TTFT: 14132.8ms | TTLT: 14132.8ms
✅ [google_search] Public Google Search Web Grounding       | TTFT: 15118.3ms | TTLT: 15118.3ms
✅ [deep_research] Deep Research Multi-Step Plan & Synthesis | TTFT: 37596.5ms | TTLT: 37596.5ms
✅ [sharepoint] SharePoint Document Retrieval               | TTFT: 40138.1ms | TTLT: 40138.1ms

================================================================================
📊 PROBER SUMMARY & HEALTH SCORE
================================================================================
Total Duration       : 40.14s
Functional Pass Rate : 4/4 (100.0%)
SLO Compliance Rate  : 4/4 (100.0%)
Report Exported To   : smoke_prober_results.json
================================================================================
```
