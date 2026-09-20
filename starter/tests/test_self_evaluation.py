"""Target contract for retrospective evaluation."""

from types import SimpleNamespace
from unittest.mock import patch

from harness.stage_00_runtime.state import RuntimeState
from harness.stage_01_loops.loop_01_non_production import HarnessLoop
from harness.stage_01_loops.loop_02_self_evaluation import SelfEvaluationLoop
from harness.stage_04_evaluation.retrospective_evaluation import (
    run_retrospective_evaluation,
)


def test_retrospective_evaluation_returns_the_required_schema():
    response = SimpleNamespace(output_text=(
        '{"task_status":"SUCCESS","efficiency_score":1.0,'
        '"critique":"complete","systemic_failure_root_cause":"none",'
        '"workflow_adjustments":"none"}'
    ))
    client = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **_: response)
    )
    result = run_retrospective_evaluation(
        client,
        "test",
        "prompt",
        [],
        [],
        "answer",
        "complete",
    )
    assert result["task_status"] == "SUCCESS"
    assert 0 <= result["efficiency_score"] <= 1


def test_review_waits_until_approved_primary_run_finishes():
    state = RuntimeState()
    loop = SelfEvaluationLoop(
        client=None,
        deployment="test",
        instructions=lambda: "SYSTEM GUIDANCE",
        handlers=SimpleNamespace(),
        registry=SimpleNamespace(),
        state=state,
    )
    paused = {"status": "approval_required", "response": SimpleNamespace(output_text="Plan")}
    finished = {"status": "complete", "response": SimpleNamespace(output_text="Final answer")}
    review_result = {
        "task_status": "SUCCESS", "efficiency_score": 1.0,
        "critique": "Grounded", "systemic_failure_root_cause": "None",
        "workflow_adjustments": "None",
    }
    with (
        patch.object(HarnessLoop, "agent_loop", return_value=paused),
        patch.object(HarnessLoop, "resume_after_approval", return_value=finished),
        patch("harness.stage_01_loops.loop_02_self_evaluation.run_retrospective_evaluation",
              return_value=review_result) as evaluator,
    ):
        first = loop.agent_loop("USER QUESTION")
        assert first["status"] == "approval_required"
        evaluator.assert_not_called()

        result = loop.resume_after_approval(SimpleNamespace(id="plan"), [], 2)
        assert result["evaluation"] == review_result
        kwargs = evaluator.call_args.kwargs
        assert "SYSTEM GUIDANCE" in kwargs["original_prompt"]
        assert "USER QUESTION" in kwargs["original_prompt"]
        assert kwargs["final_output"] == "Final answer"
