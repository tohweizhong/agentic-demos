# Product Guidelines — Gemini Enterprise Prober (`ge-prober`)

## 1. Design & UX Principles
- **Minimalist & Deterministic**: Focus strictly on vital health checks, latency profiling, and error detection without unnecessary complexity.
- **Human-Readable CLI UX**: When run interactively, provide clear single-line test progress with intuitive status icons:
  - `✅` : Functional pass & within SLO thresholds
  - `⚠️` : Functional pass, but latency breached SLO
  - `❌` : Functional failure or service error
- **Machine-Readable Telemetry**: Always output clean, structured JSON reports suitable for ingestion by Cloud Logging, Cloud Monitoring, and web dashboards.

---

## 2. Reliability & SRE Standards
- **Error Taxonomy**: Clearly separate client-side / auth / quota errors (401/403/429) from server-side outages (500/503).
- **Headless Execution**: Zero reliance on interactive browser prompts or interactive logins. Must execute seamlessly as a Cloud Run Job.
- **Fail-Safe Operation**: A single probe failure must never crash the entire batch runner; exceptions must be caught, recorded, and summarized.
