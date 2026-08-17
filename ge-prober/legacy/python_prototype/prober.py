#!/usr/bin/env python3
"""Gemini Enterprise Synthetic Smoke Test Prober.

Executes lightweight, concurrent synthetic smoke probes across Gemini Enterprise
subsystems (M365 Connectors, Workspace, Deep Research, Agent Designer, BYO-MCP,
Direct URL, NotebookLM, Web Grounding, and Memory) to verify cross-tenant
connectivity, latency SLOs, and vital health signs.
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    resolved = config_path if os.path.isabs(config_path) else os.path.join(SCRIPT_DIR, config_path)
    if os.path.exists(resolved):
        with open(resolved, "r") as f:
            return json.load(f)
    return {}


def load_test_cases(test_cases_path: str) -> List[Dict[str, Any]]:
    resolved = test_cases_path if os.path.isabs(test_cases_path) else os.path.join(SCRIPT_DIR, test_cases_path)
    if not os.path.exists(resolved):
        print(f"❌ Test cases file not found: {resolved}")
        sys.exit(1)
    with open(resolved, "r") as f:
        return json.load(f)


def get_access_token() -> str:
    """Retrieves access token from environment or active gcloud session."""
    env_token = os.environ.get("GCP_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()
    try:
        return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    except Exception as e:
        print(f"❌ Failed to obtain access token via gcloud: {e}")
        sys.exit(1)


def execute_probe(
    tc: Dict[str, Any],
    project_id: str,
    location: str,
    engine_id: str,
    token: str,
    data_store_ids: List[str],
    timeout: float = 45.0,
) -> Dict[str, Any]:
    """Executes a single smoke probe against StreamAssist API."""
    tc_id = tc.get("id")
    query = tc.get("query")
    subsystem = tc.get("subsystem")
    grounding_type = tc.get("grounding_type", "vertex_ai_search")
    slo = tc.get("slo_targets", {})
    max_ttft = slo.get("max_ttft_ms", 3000.0)
    max_ttlt = slo.get("max_ttlt_ms", 12000.0)
    assertions = tc.get("assertions", {})

    url = (
        f"https://{location}-discoveryengine.googleapis.com/v1alpha/projects/{project_id}/"
        f"locations/{location}/collections/default_collection/engines/{engine_id}/"
        f"assistants/default_assistant:streamAssist"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Build toolsSpec based on grounding type
    tools_spec: Dict[str, Any] = {}
    if grounding_type == "vertex_ai_search" and data_store_ids:
        ds_specs = [
            {"dataStore": f"projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{ds}"}
            for ds in data_store_ids
        ]
        tools_spec["vertexAiSearchSpec"] = {"dataStoreSpecs": ds_specs}
    elif grounding_type == "web_search":
        tools_spec["webGroundingSpec"] = {}

    body = {
        "query": {"text": query},
        "toolsSpec": tools_spec,
    }

    start_time = time.perf_counter()
    status_code = None
    error_message = None
    response_text = ""
    ttft_ms = None
    has_citations = False

    try:
        res = requests.post(url, headers=headers, json=body, timeout=timeout)
        status_code = res.status_code

        if res.status_code == 200:
            data = res.json()
            # StreamAssist REST returns an array of chunks
            for chunk in data:
                ans = chunk.get("answer", {})
                for reply in ans.get("replies", []):
                    grounded = reply.get("groundedContent", {})
                    content = grounded.get("content", {})
                    text = content.get("text", "")
                    thought = content.get("thought", False)

                    if text and not thought and ttft_ms is None:
                        ttft_ms = (time.perf_counter() - start_time) * 1000.0

                    if not thought and text:
                        response_text += text

                    if grounded.get("groundingMetadata", {}).get("webSearchQueries") or grounded.get("groundingMetadata", {}).get("groundingChunks"):
                        has_citations = True

                    if "references" in reply or "citations" in reply:
                        has_citations = True
        else:
            error_message = f"HTTP {res.status_code}: {res.text[:200]}"
    except Exception as e:
        error_message = str(e)

    total_latency_ms = (time.perf_counter() - start_time) * 1000.0
    if ttft_ms is None:
        ttft_ms = total_latency_ms

    # Assertions evaluation
    passed = True
    failure_reasons = []

    if status_code != 200:
        passed = False
        failure_reasons.append(f"Bad status code: {status_code} ({error_message})")

    for forbidden in assertions.get("forbidden_errors", []):
        if forbidden in (error_message or "") or forbidden in response_text:
            passed = False
            failure_reasons.append(f"Forbidden error detected: {forbidden}")

    required_keywords = assertions.get("must_contain_keywords", [])
    if required_keywords and response_text:
        found_any = any(k.lower() in response_text.lower() for k in required_keywords)
        if not found_any:
            failure_reasons.append(f"Keywords missing: {required_keywords}")

    # Latency SLO checks
    slo_passed = True
    if ttft_ms > max_ttft:
        slo_passed = False
        failure_reasons.append(f"TTFT breached SLO: {ttft_ms:.1f}ms > {max_ttft}ms")
    if total_latency_ms > max_ttlt:
        slo_passed = False
        failure_reasons.append(f"TTLT breached SLO: {total_latency_ms:.1f}ms > {max_ttlt}ms")

    return {
        "id": tc_id,
        "title": tc.get("title"),
        "subsystem": subsystem,
        "query": query,
        "passed": passed and (status_code == 200),
        "slo_passed": slo_passed,
        "status_code": status_code,
        "ttft_ms": round(ttft_ms, 1),
        "total_latency_ms": round(total_latency_ms, 1),
        "has_citations": has_citations,
        "failure_reasons": failure_reasons,
        "response_preview": response_text.strip()[:200] if response_text else (error_message or ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Gemini Enterprise Synthetic Smoke Test Prober")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--test-cases", default="test_cases/smoke_test_cases.json", help="Path to test cases JSON")
    parser.add_argument("--concurrency", type=int, default=None, help="Number of concurrent probe workers")
    parser.add_argument("--output-json", default="smoke_prober_results.json", help="Path to export results JSON")
    args = parser.parse_args()

    cfg = load_config(args.config)
    project_id = cfg.get("project_id", "my-gcp-project")
    location = cfg.get("location", "global")
    engine_id = cfg.get("engine_id", "my-gemini-app")
    data_store_ids = cfg.get("data_store_ids", [])
    concurrency = args.concurrency or cfg.get("max_concurrency", 5)
    timeout = cfg.get("timeout_seconds", 45.0)

    test_cases = load_test_cases(args.test_cases)
    token = get_access_token()

    print(f"\n================================================================================")
    print(f"🚀 GEMINI ENTERPRISE SYNTHETIC SMOKE TEST PROBER")
    print(f"================================================================================")
    print(f"🎯 Target Project : {project_id}")
    print(f"📍 Location / Reg : {location} ({location}-discoveryengine.googleapis.com)")
    print(f"⚙️ Target Engine  : {engine_id}")
    print(f"📦 Test Cases     : {len(test_cases)} probes across {len(set(tc.get('subsystem') for tc in test_cases))} subsystems")
    print(f"⚡ Concurrency    : {concurrency} parallel workers")
    print(f"================================================================================\n")

    results = []
    start_all = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_tc = {
            executor.submit(
                execute_probe, tc, project_id, location, engine_id, token, data_store_ids, timeout
            ): tc
            for tc in test_cases
        }

        for future in concurrent.futures.as_completed(future_to_tc):
            tc = future_to_tc[future]
            try:
                res = future.result()
                results.append(res)
                icon = "✅" if res["passed"] and res["slo_passed"] else ("⚠️" if res["passed"] else "❌")
                print(f"{icon} [{res['subsystem']}] {res['title']} | TTFT: {res['ttft_ms']}ms | TTLT: {res['total_latency_ms']}ms")
                if res["failure_reasons"]:
                    for reason in res["failure_reasons"]:
                        print(f"   ↳ ⚠️ {reason}")
            except Exception as e:
                print(f"❌ [{tc.get('subsystem')}] {tc.get('title')} failed with exception: {e}")

    total_time = time.perf_counter() - start_all
    passed_count = sum(1 for r in results if r["passed"])
    slo_passed_count = sum(1 for r in results if r["slo_passed"] and r["passed"])
    total_count = len(results)

    print(f"\n================================================================================")
    print(f"📊 PROBER SUMMARY & HEALTH SCORE")
    print(f"================================================================================")
    print(f"Total Execution Time : {total_time:.2f}s")
    print(f"Functional Pass Rate : {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")
    print(f"SLO Compliance Rate  : {slo_passed_count}/{total_count} ({slo_passed_count/total_count*100:.1f}%)")
    print(f"Report Exported To   : {args.output_json}")
    print(f"================================================================================\n")

    with open(args.output_json, "w") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "project_id": project_id,
                "location": location,
                "engine_id": engine_id,
                "total_probes": total_count,
                "functional_passed": passed_count,
                "slo_passed": slo_passed_count,
                "results": results,
            },
            f,
            indent=2,
        )


if __name__ == "__main__":
    main()
