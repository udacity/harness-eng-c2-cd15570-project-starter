"""Loop 02 component: make a separate model call that reviews finished evidence."""

from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "task_status",
    "efficiency_score",
    "critique",
    "systemic_failure_root_cause",
    "workflow_adjustments",
}

EVALUATION_INSTRUCTIONS = """TODO: Tell the evaluator to judge goal fulfillment,
loop or stall behavior, tool efficiency, and log sufficiency using only the
supplied evidence. Require JSON with exactly the keys in REQUIRED_KEYS.
task_status must be SUCCESS, FAILED, or PARTIAL_SUCCESS; efficiency_score
must be a number from 0 to 1. Do not ask for private model reasoning."""


def run_retrospective_evaluation(
    client: Any,
    deployment: str,
    original_prompt: str,
    execution_trace: list[dict[str, Any]],
    tool_run_log: list[dict[str, Any]],
    final_output: str,
    task_result: str,
) -> dict[str, Any]:
    """Return validated retrospective JSON for one finished task."""
    # TODO 1: Build an evidence object containing original_prompt,
    # execution_trace, tool_run_log, final_output, and task_result.
    # TODO 2: Call client.responses.create with deployment, these evaluator
    # instructions, and the serialized evidence. This must be a NEW call,
    # separate from the primary EDA conversation.
    # TODO 3: Parse review.output_text, verify the exact schema and value
    # constraints, and return a useful structured error on malformed output.
    raise NotImplementedError("Implement retrospective evaluation.")
