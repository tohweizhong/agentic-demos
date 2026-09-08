# Specification: Verbose Cloud Logging & Real-Time Stream Tracing

## Overview
Enhance `ge-prober` with high-fidelity, line-by-line verbose cloud logging and stream tracing for Google Cloud Run Job executions and Google Cloud Logging Explorer. This provides real-time visibility into the exact queries sent to Gemini Enterprise, intermediate reasoning/thought processes, grounded response chunks formatted line-by-line, and latency telemetry (TTFT and TTLT).

## Functional Requirements

### 1. Formatted Probe Header & Query Display
For each test case execution, the prober must output:
- **Probe Header:** `[X/N] 🔎 [<grounding_type>] <test_case_id>` (e.g. `[4/4] 🔎 [sharepoint] sharepoint_01`)
- **Query Line:** `📜 Query: "<query_text>"` (e.g. `📜 Query: "Search for files about FormSG in our SharePoint site."`)

### 2. Intermediate Reasoning & Thought Tracing
- When intermediate streaming chunks contain `thought: true` or represent agent planning (e.g., Deep Research thought steps), the prober formats them under a `🧠 Thought:` or `💭 Thought:` block before the final response.

### 3. Line-by-Line Grounded Response Tracing
- Output `💬 Response:` header.
- Emit the Gemini Enterprise answer line-by-line / paragraph-by-paragraph to standard output so that markdown headings (`### 📌 Primary Document`), bullet points, descriptions, and citations/hyperlinks (`* **[Doc.pdf](https://...)**`) are rendered as distinct, easily readable lines in Cloud Run Log Explorer.

### 4. Stream Performance & Completion Banner
- Upon stream completion, output: `✅ Stream Done (TTFT: X.X ms | Total: Y.Y ms)` where `TTFT` is Time to First Token in milliseconds and `Total` is TTLT in milliseconds.

### 5. Thread-Safe Synchronized Log Output
- When executing multiple probes concurrently (`-concurrency > 1`), stdout log output for each test case must be synchronized so lines from different probes do not interleave or corrupt the output stream.

### 6. Test Suite Execution Summary
- Print the formatted summary table (`📊 TEST SUITE EXECUTION SUMMARY`) upon completion of all probes, including total probes, pass rate, SLO compliance rate, duration, and output file path.

### 7. CLI & Config Support
- Verbose stream logging is enabled by default.
- Support `-verbose` flag (default `true`) allowing users or scripts to toggle between verbose line-by-line output and condensed single-line output.

## Acceptance Criteria
- [ ] `logger.go` or equivalent logging engine provides thread-safe, structured line-by-line log emission.
- [ ] Unit tests in `logger_test.go` and `prober_test.go` validate header formatting, response line splitting, thought blocks, and performance banners.
- [ ] Concurrent prober execution maintains clean per-probe log grouping.
- [ ] Running `./ge-prober` locally displays the formatted probe headers, queries, line-by-line responses, and completion banners matching the Cloud Run Task 0 log explorer specification.
- [ ] All unit tests pass with `go test -v ./...`.
