# 🚀 Gemini Enterprise Synthetic Prober (`ge-prober`)

A high-performance, containerized Go synthetic monitoring tool and smoke prober for **Gemini Enterprise (Discovery Engine)** applications and multimodal knowledge bases.

---

## ⭐ Recommended Architecture: Serverless Cloud Run Job with Cloud Scheduler

> [!TIP]
> **Production Best Practice**: Deploying `ge-prober` as a **Google Cloud Run Job** triggered by **Cloud Scheduler** is the **strongly recommended deployment model**.
> - **Zero Server Maintenance**: Purely serverless container execution that scales to zero between runs.
> - **Continuous Proactive Monitoring**: Detects silent backend breakages, connector sync failures, and latency spikes before end-users notice.
> - **Native GCP Security**: Uses Google Cloud Workload Identity / IAM Service Account tokens automatically (no static API keys or long-lived credentials to rotate).

```
  ┌──────────────────────┐         HTTP POST Trigger          ┌───────────────────────────┐
  │   Cloud Scheduler    │ ─────────────────────────────────> │      Cloud Run Job        │
  │  (Daily / Scheduled) │                                    │   (ge-prober Container)   │
  └──────────────────────┘                                    └─────────────┬─────────────┘
                                                                            │ StreamAssist
                                                                            ▼
                                                              ┌───────────────────────────┐
                                                              │ Gemini Enterprise Backend │
                                                              │  (Discovery Engine APIs)  │
                                                              └───────────────────────────┘
```

### ⚡ Quick Deployment (1 Command)

1. **Set your target GCP environment variables**:
   ```bash
   export GCP_PROJECT_ID="YOUR_GCP_PROJECT_ID"
   export GE_ENGINE_ID="YOUR_GEMINI_ENTERPRISE_ENGINE_ID"
   export GE_LOCATION="global"
   export GCP_REGION="us-central1"   # Cloud Run execution region
   ```

2. **Run the deployment script**:
   ```bash
   bash deploy_job.sh
   ```
   *This script automatically builds the distroless container image via Google Cloud Build, deploys the Cloud Run Job `ge-prober-daily`, and configures Cloud Scheduler to trigger it daily at 01:00 UTC (09:00 SGT).*

3. **Execute an on-demand probe run anytime**:
   ```bash
   gcloud run jobs execute ge-prober-daily --project="${GCP_PROJECT_ID}" --region="${GCP_REGION}" --wait
   ```

4. **View Execution Logs & Health**:
   - In Cloud Console: Navigate to **Cloud Run $\rightarrow$ Jobs $\rightarrow$ `ge-prober-daily` $\rightarrow$ Executions**.
   - In Terminal:
     ```bash
     gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=ge-prober-daily" --limit=50 --format="value(textPayload)"
     ```

---

## 💻 Alternative: Local Workstation & Ad-Hoc CLI Testing

For local development or testing without deploying to Cloud Run, `ge-prober` can be run directly on your workstation using any of the following configuration options (resolved via 12-factor precedence: `Flags > Env Vars > .env > config.json > Defaults`):

### Option A: Local `.env` File *(Recommended for Developers)*
Copy [`.env.example`](./.env.example) to `.env`:
```bash
GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID
GE_LOCATION=global
GE_ENGINE_ID=YOUR_GEMINI_ENTERPRISE_ENGINE_ID
GE_DATA_STORE_IDS=datastore_1,datastore_2
GE_MAX_CONCURRENCY=4
```
Run:
```bash
./ge-prober
```

### Option B: Local `config.json` File
Copy [`config.example.json`](./config.example.json) to `config.json`:
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
Run:
```bash
./ge-prober
```

### Option C: Direct CLI Flags *(One-Liners & CI/CD)*
```bash
./ge-prober \
  -project="YOUR_GCP_PROJECT_ID" \
  -engine="YOUR_GEMINI_ENTERPRISE_ENGINE_ID" \
  -region="global" \
  -datastores="datastore_1,datastore_2" \
  -concurrency=4
```

#### Complete CLI Flag Reference:
| Flag | Description | Default |
| :--- | :--- | :--- |
| `-project` | Target GCP Project ID | From config / env |
| `-location` / `-region` | Discovery Engine location (`global`, `us`, `eu`, etc.) | `global` |
| `-engine` | Target Gemini Enterprise Engine / App ID | From config / env |
| `-assistant` | Assistant ID | `default_assistant` |
| `-datastores` | Comma-separated list of Data Store IDs | `""` |
| `-concurrency` | Number of concurrent workers | `4` |
| `-timeout` | Per-probe timeout in seconds | `180` |
| `-test-cases` | Path to custom test suite JSON file | `test_cases/smoke_test_cases.json` |
| `-output` | Path to export JSON results report | `smoke_prober_results.json` |
| `-config` | Path to custom JSON configuration file | `config.json` |
| `-token` | GCP Access token override | Automatic ADC / Service Account |

---

## 📝 Customizing & Adding Test Queries

You can easily customize queries or add new test cases in **2 ways**:

### 1. Edit the Default Test Suite
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

### 2. Point to a Custom Test Catalog File
Maintain separate test suites (e.g. `prod_queries.json`, `hr_tests.json`) and pass the path using `-test-cases`:

```bash
./ge-prober -test-cases="path/to/custom_queries.json"
```

### 📋 Grounding Type Reference:
| `grounding_type` | Subsystem Targeted | Backend Behavior |
| :--- | :--- | :--- |
| **`vertex_ai_search`** | Enterprise Connectors | Queries attached enterprise data stores (SharePoint, OneDrive, Confluence, Jira, BigQuery). |
| **`deep_research_agent`** | Deep Research Agent | Injects `agentsSpec: { agentSpecs: [{ agentId: "deep_research" }] }` with web grounding for multi-step research plans. |
| **`gemini_notebook`** | Gemini Notebook | Queries the notebook workspace knowledge base directly without external connectors. |
| **`web_search`** | Google Search | Injects `toolsSpec: { webGroundingSpec: {} }` for real-time public web search facts. |

---

## 🔐 Authentication
The prober automatically manages authentication across environments:
1. **Cloud Run / GKE**: Automatically uses the attached Service Account metadata token (requires `roles/discoveryengine.editor` or `roles/discoveryengine.admin`).
2. **Local Workstations**: Automatically uses Application Default Credentials (`gcloud auth application-default login`).
3. **CI/CD / Custom Pipelines**: Pass `$GCP_ACCESS_TOKEN` in the environment or `-token="ya29..."`.

---

## 📊 Sample Execution Output
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
Container called exit(0).
```
