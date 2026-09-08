"""TODO: Evaluate one completed harness run from saved evidence."""

from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "task_status",
    "efficiency_score",
    "critique",
    "systemic_failure_root_cause",
    "workflow_adjustments",
}

EVALUATION_INSTRUCTIONS = """TODO: Write evaluator instructions that score at
least five observable quality checks using only the supplied prompt, trace,
tool evidence, and final response. Return validated JSON with REQUIRED_KEYS."""


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
    # TODO: Build an evidence payload, make a second model call, validate the
    # exact schema, and return a normalized failure object on evaluator errors.
    raise NotImplementedError("Implement retrospective evaluation.")
