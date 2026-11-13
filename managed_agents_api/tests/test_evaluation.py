"""Tests for the evaluation helpers. They do not need the evaluation SDK."""

import io
import json
from types import SimpleNamespace

from rich.console import Console

from managed_agents_demo import evaluation
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")


def record(name):
    def build(**kwargs):
        return SimpleNamespace(kind=name, **kwargs)

    return build


FAKE_TYPES = SimpleNamespace(
    RubricMetric=SimpleNamespace(MULTI_TURN_TASK_SUCCESS="task", SAFETY="safety"),
    EvaluationDataset=record("dataset"),
    EvalCase=record("case"),
    InteractionsDataSource=record("source"),
    GeminiAgentConfig=record("agent_config"),
)


def fake_result():
    metric = SimpleNamespace(
        score=1.0, explanation="The agent completed the task.", error_message=None
    )
    case = SimpleNamespace(
        eval_case_index=0,
        response_candidate_results=[SimpleNamespace(metric_results={"task": metric})],
    )
    summary = SimpleNamespace(
        metric_name="task", mean_score=1.0, pass_rate=1.0, num_cases_valid=1, num_cases_total=1
    )
    return SimpleNamespace(
        eval_case_results=[case],
        summary_metrics=[summary],
        model_dump=lambda **kw: {"summary_metrics": [{"metric_name": "task", "mean_score": 1.0}]},
    )


class FakeEvals:
    def __init__(self):
        self.calls = []

    def evaluate(self, dataset, metrics, agent):
        self.calls.append(("evaluate", dataset, metrics, agent))
        return fake_result()

    def generate_conversation_scenarios(self, agent, config):
        self.calls.append(("generate", agent, config))
        return SimpleNamespace(show=lambda: None)

    def run_inference(self, agent, src, config):
        self.calls.append(("inference", agent, src, config))
        return "inference-results"


def make():
    buffer = io.StringIO()
    return (
        SimpleNamespace(evals=FakeEvals()),
        Console(file=buffer, width=160, color_system=None),
        buffer,
    )


def test_agent_resource():
    assert evaluation.agent_resource(SETTINGS, "demo-a") == (
        "projects/test-project/locations/global/agents/demo-a"
    )


def test_recorded_dataset_points_to_interaction():
    state = {"agent_id": "demo-a", "interaction_id": "int-1"}
    dataset = evaluation.recorded_dataset(FAKE_TYPES, SETTINGS, state)
    source = dataset.eval_cases[0].interactions_data_source
    assert source.interaction == "projects/test-project/locations/global/interactions/int-1"
    assert source.gemini_agent_config.gemini_agent.endswith("/agents/demo-a")


def test_summarize_rows():
    cases, summary = evaluation.summarize(fake_result())
    assert cases == [(0, "task", 1.0, "The agent completed the task.")]
    assert summary == [("task", 1.0, 1.0, "1/1")]


def test_run_recorded_mode_saves_json(tmp_path):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"agent_id": "demo-a", "interaction_id": "int-1"}))
    eval_client, console, buffer = make()
    code = evaluation.run(
        console,
        SETTINGS,
        mode="recorded",
        eval_client=eval_client,
        types=FAKE_TYPES,
        state_path=state,
        output_dir=tmp_path / "eval",
    )
    assert code == 0
    kind, dataset, metrics, agent = eval_client.evals.calls[0]
    assert kind == "evaluate"
    assert metrics == ["task", "safety"]
    assert agent.endswith("/agents/demo-a")
    saved = list((tmp_path / "eval").glob("recorded_*.json"))
    assert len(saved) == 1
    assert "The agent completed the task." in buffer.getvalue()


def test_run_recorded_without_state_states_the_fix(tmp_path):
    eval_client, console, buffer = make()
    code = evaluation.run(
        console,
        SETTINGS,
        mode="recorded",
        eval_client=eval_client,
        types=FAKE_TYPES,
        state_path=tmp_path / "missing.json",
        output_dir=tmp_path,
    )
    assert code == 1
    assert "02_interact.py" in buffer.getvalue()


def test_run_generated_mode_calls_three_steps(tmp_path):
    eval_client, console, buffer = make()
    code = evaluation.run(
        console,
        SETTINGS,
        mode="generated",
        count=2,
        eval_client=eval_client,
        types=FAKE_TYPES,
        output_dir=tmp_path,
    )
    assert code == 0
    kinds = [call[0] for call in eval_client.evals.calls]
    assert kinds == ["generate", "inference", "evaluate"]
    assert eval_client.evals.calls[0][2]["count"] == 2
    assert eval_client.evals.calls[1][3] == {"user_simulator_config": {"max_turn": 2}}
    assert eval_client.evals.calls[2][1] == "inference-results"
    assert "Cost" in buffer.getvalue()


def test_metric_error_is_shown():
    metric = SimpleNamespace(score=None, explanation=None, error_message="judge failed")
    result = SimpleNamespace(
        eval_case_results=[
            SimpleNamespace(
                eval_case_index=0,
                response_candidate_results=[SimpleNamespace(metric_results={"task": metric})],
            )
        ],
        summary_metrics=[],
    )
    cases, _ = evaluation.summarize(result)
    assert cases == [(0, "task", None, "Error: judge failed")]


def test_missing_sdk_states_the_fix(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def no_sdk(name, *args, **kwargs):
        if name.startswith("agentplatform"):
            raise ImportError("No module named 'agentplatform'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_sdk)
    _, console, buffer = make()
    assert evaluation.run(console, SETTINGS) == 1
    assert "requirements-eval.txt" in buffer.getvalue()


def test_generated_mode_reports_sdk_error(tmp_path):
    eval_client, console, buffer = make()

    def fail(agent, src, config):
        raise ModuleNotFoundError("No module named 'google.adk'")

    eval_client.evals.run_inference = fail
    code = evaluation.run(
        console,
        SETTINGS,
        mode="generated",
        count=1,
        eval_client=eval_client,
        types=FAKE_TYPES,
        output_dir=tmp_path,
    )
    assert code == 1
    assert "google.adk" in buffer.getvalue()
