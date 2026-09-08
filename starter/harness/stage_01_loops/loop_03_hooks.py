"""TODO: Add deterministic lifecycle hooks and antidotes to Loop 01."""

from __future__ import annotations

from .loop_01_non_production import HarnessLoop


class HooksLoop(HarnessLoop):
    """Extend the Loop 01 lifecycle without duplicating the agent loop."""

    # TODO: Override the lifecycle extension points provided by HarnessLoop.
    # - Block invalid tool calls before they reach a handler.
    # - Add deterministic evidence after relevant tool calls complete.
    # - Record hook and antidote activity in state.tool_run_log.
    pass
