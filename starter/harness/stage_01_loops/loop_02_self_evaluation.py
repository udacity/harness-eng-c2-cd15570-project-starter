"""TODO: Add retrospective self-evaluation after a completed EDA task."""

from __future__ import annotations

from .loop_01_non_production import HarnessLoop


class SelfEvaluationLoop(HarnessLoop):
    """Extend Loop 01 without changing its primary EDA behavior."""

    def agent_loop(self, user_query: str, previous_response_id: str | None = None):
        # TODO: Save the original prompt, run the primary loop, then evaluate a
        # completed or iteration-limited result with the full execution trace.
        return super().agent_loop(user_query, previous_response_id)

    def resume_after_approval(self, approval_response, tool_results, starting_loop: int):
        # TODO: Resume the primary loop, then evaluate its completed result.
        return super().resume_after_approval(
            approval_response,
            tool_results,
            starting_loop,
        )
