"""Loop 02 scaffold: review a finished Loop 01 run without changing its answer."""

from __future__ import annotations

from .loop_01_non_production import HarnessLoop
from harness.stage_04_evaluation import run_retrospective_evaluation


class SelfEvaluationLoop(HarnessLoop):
    """The primary task is the inherited loop; evaluation is a later model call."""

    def agent_loop(self, user_query: str, previous_response_id: str | None = None):
        self.original_prompt = (
            f"SYSTEM INSTRUCTIONS:\n{self.instructions()}\n\n"
            f"USER REQUEST:\n{user_query}"
        )
        return self._evaluate_if_finished(
            super().agent_loop(user_query, previous_response_id)
        )

    def resume_after_approval(self, approval_response, tool_results, starting_loop: int):
        # A plan pause is normal for the supplied master prompt. Evaluate
        # only after the resumed primary task has actually finished.
        return self._evaluate_if_finished(
            super().resume_after_approval(
                approval_response,
                tool_results,
                starting_loop,
            )
        )

    def _evaluate_if_finished(self, result: dict) -> dict:
        """Attach a separate review only after completion or iteration limit."""
        if result["status"] not in {"complete", "iteration_limit"}:
            return result
        # TODO: On a finished result, call run_retrospective_evaluation with the
        # original prompt, state.execution_trace, state.tool_run_log, final
        # response text, and result status. Print the review and store it under
        # result["evaluation"] so main.py writes the JSON artifact.
        raise NotImplementedError("Implement the Loop 02 retrospective review.")
