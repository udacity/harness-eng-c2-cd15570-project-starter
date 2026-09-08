"""Target contract for retrospective evaluation."""

from types import SimpleNamespace

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
