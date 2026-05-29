import sys
import os
import csv
import json
import time
import asyncio
from google.genai import Client

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import agent

# Initialize Gemini Evaluator Client
try:
    config = agent.load_config()
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
    
eval_client = Client(**kwargs)

def evaluate_semantic_correctness(reference: str, candidate: str) -> bool:
    """Uses Gemini to semantically grade the correctness of the candidate response."""
    # Clean up inputs
    reference = reference.strip()
    candidate = candidate.strip()
    
    if not candidate:
        return False
        
    prompt = f"""
    You are an AI Evaluation Judge. Compare the Candidate Answer with the Reference Answer.
    Determine if the Candidate Answer has the same semantic meaning and correctly addresses the core facts/insights outlined in the Reference Answer.
    
    * Note: Minor wording differences, formatting differences, or extra polite greetings are completely acceptable.
    * Crucial: If the Reference Answer is an RMS protection/encryption block message, the Candidate Answer MUST correctly state that the file is encrypted, protected, or unreadable.
    
    Reference Answer:
    ---
    {reference}
    ---
    
    Candidate Answer:
    ---
    {candidate}
    ---
    
    Response strictly with either 'CORRECT' or 'WRONG' in plain text. Do not include any other explanation or markdown.
    """
    try:
        response = eval_client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        result_text = response.text.strip().upper()
        return "CORRECT" in result_text
    except Exception as e:
        print(f"LLM-as-a-Judge grading failed: {e}")
        # Fallback to simple keyword/substring checking
        return reference[:30].lower() in candidate.lower()

def compare_trajectories(expected: list, actual: list) -> bool:
    """Compares expected tool call trajectory list with actual executed tool call list."""
    if len(expected) != len(actual):
        return False
        
    for exp, act in zip(expected, actual):
        if exp.get("tool") != act.get("tool"):
            return False
        # For search, check if query parameter matches roughly
        if exp.get("tool") == "search_sharepoint_files":
            exp_q = exp.get("args", {}).get("query", "").lower()
            act_q = act.get("args", {}).get("query", "").lower()
            if exp_q not in act_q and act_q not in exp_q:
                return False
        # For read, check if item_id matches
        elif exp.get("tool") == "read_sharepoint_file":
            exp_id = exp.get("args", {}).get("item_id", "")
            act_id = act.get("args", {}).get("item_id", "")
            if exp_id != act_id:
                return False
    return True

async def run_evaluation(limit=5):
    harness_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(harness_dir, "evaluation_dataset.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: Dataset CSV not found at {csv_path}. Please run generate_dataset.py first!")
        return
        
    print(f"Loading benchmark dataset. Running evaluation on the first {limit} test cases...")
    
    test_cases = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append(row)
            
    session_service = InMemorySessionService()
    runner = Runner(agent=agent.root_agent, session_service=session_service, app_name="sharepoint_file_lister", auto_create_session=True)
    
    results = []
    correct_count = 0
    trajectory_match_count = 0
    total_latency = 0
    
    for idx, case in enumerate(test_cases[:limit]):
        query = case["query"]
        expected_resp = case["expected_response"]
        expected_traj = json.loads(case["expected_tool_trajectory"])
        source = case["source"]
        file_type = case["file_type"]
        is_encrypted = case["is_encrypted"] == "True"
        
        print(f"\n[{idx+1}/{limit}] Query: '{query}'")
        
        # Reset tool call logs in agent module
        agent._tool_calls_log = []
        
        # Run the agent in a fresh session per query
        session_id = f"eval_session_{idx+1}"
        content = types.Content(role='user', parts=[types.Part(text=query)])
        
        start_time = time.time()
        final_response = ""
        
        try:
            async for event in runner.run_async(
                new_message=content,
                user_id="eval_user",
                session_id=session_id
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response = event.content.parts[0].text
        except Exception as e:
            final_response = f"[Agent Execution Crashed: {str(e)}]"
            
        end_time = time.time()
        latency = end_time - start_time
        total_latency += latency
        
        # Retrieve actual tool calls log
        actual_traj = list(agent._tool_calls_log)
        
        # 1. Grade final response correctness semantically using LLM Judge
        is_correct = evaluate_semantic_correctness(expected_resp, final_response)
        if is_correct:
            correct_count += 1
            
        # 2. Grade trajectory correctness
        traj_match = compare_trajectories(expected_traj, actual_traj)
        if traj_match:
            trajectory_match_count += 1
            
        print(f"   Latency: {latency:.2f}s | Correct: {is_correct} | Trajectory Match: {traj_match}")
        
        results.append({
            "index": idx + 1,
            "query": query,
            "expected_response": expected_resp,
            "actual_response": final_response,
            "expected_trajectory": expected_traj,
            "actual_trajectory": actual_traj,
            "source": source,
            "file_type": file_type,
            "is_encrypted": is_encrypted,
            "latency_seconds": latency,
            "is_correct": is_correct,
            "trajectory_match": traj_match
        })
        
    # Calculate aggregate metrics
    total_cases = len(results)
    accuracy = (correct_count / total_cases) * 100 if total_cases > 0 else 0
    trajectory_match_rate = (trajectory_match_count / total_cases) * 100 if total_cases > 0 else 0
    avg_latency = total_latency / total_cases if total_cases > 0 else 0
    
    report_summary = {
        "total_test_cases": total_cases,
        "semantic_accuracy_percent": accuracy,
        "trajectory_match_rate_percent": trajectory_match_rate,
        "average_latency_seconds": avg_latency,
        "results": results
    }
    
    # Save detailed JSON results
    results_json_path = os.path.join(harness_dir, "evaluation_results.json")
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(report_summary, f, indent=2)
        
    # Generate beautiful markdown report
    generate_markdown_report(report_summary, os.path.join(harness_dir, "evaluation_report.md"))
    
    print(f"\n========================================")
    print(f"         Evaluation Completed!")
    print(f"========================================")
    print(f"Total Test Cases  : {total_cases}")
    print(f"Semantic Accuracy : {accuracy:.2f}%")
    print(f"Trajectory Match  : {trajectory_match_rate:.2f}%")
    print(f"Average Latency   : {avg_latency:.2f}s")
    print(f"Detailed results saved to: {results_json_path}")
    print(f"Markdown report generated at: {os.path.join(harness_dir, 'evaluation_report.md')}")

def generate_markdown_report(summary: dict, output_path: str):
    """Compiles the evaluation results into a gorgeous markdown report."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 🏆 SharePoint File Agent Evaluation Report\n\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')} (APC Region/Vertex AI)\n\n")
        
        f.write("## 📊 Aggregate Metrics\n\n")
        f.write("| Metric | Score / Value |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| **Total Test Cases Executed** | {summary['total_test_cases']} |\n")
        f.write(f"| **Semantic Accuracy Rate (LLM-as-a-Judge)** | `{summary['semantic_accuracy_percent']:.1f}%` 🟢 |\n")
        f.write(f"| **Tool Trajectory Match Rate** | `{summary['trajectory_match_rate_percent']:.1f}%` 🎯 |\n")
        f.write(f"| **Average Latency Per Query** | `{summary['average_latency_seconds']:.2f}s` ⚡ |\n\n")
        
        f.write("## 🔍 Individual Case Details\n\n")
        
        for case in summary["results"]:
            status_emoji = "✅" if case["is_correct"] else "❌"
            traj_emoji = "🎯" if case["trajectory_match"] else "⚠️"
            enc_status = "🔒 RMS Encrypted" if case["is_encrypted"] else "🔓 Unencrypted"
            
            f.write(f"### Test Case #{case['index']}: `{case['file_type'].upper()}` ({enc_status})\n")
            f.write(f"* **Source File**: `{case['source']}`\n")
            f.write(f"* **Semantic Correctness**: {status_emoji} | **Trajectory Match**: {case['trajectory_match']} {traj_emoji}\n")
            f.write(f"* **Latency**: `{case['latency_seconds']:.2f}s` | **RMS Encrypted**: `{case['is_encrypted']}`\n\n")
            
            f.write(f"🗣️ **User Query**:\n")
            f.write(f"> {case['query']}\n\n")
            
            f.write(f"🎯 **Expected Tool Trajectory**:\n")
            f.write(f"```json\n{json.dumps(case['expected_trajectory'], indent=2)}\n```\n\n")
            
            f.write(f"⚙️ **Actual Tool Trajectory**:\n")
            f.write(f"```json\n{json.dumps(case['actual_trajectory'], indent=2)}\n```\n\n")
            
            f.write(f"📄 **Expected Response**:\n")
            f.write(f"```text\n{case['expected_response']}\n```\n\n")
            
            f.write(f"🤖 **Agent Actual Response**:\n")
            f.write(f"```text\n{case['actual_response']}\n```\n\n")
            f.write("---\n\n")

if __name__ == "__main__":
    # Default to running first 5 test cases for efficiency, unless overridden in sys.argv
    limit = 5
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    asyncio.run(run_evaluation(limit=limit))
