"""TODO: Bind three or more deterministic antidotes to hook lifecycle events."""

from __future__ import annotations

from typing import Any


class AntidoteRegistry:
    """Return deterministic decisions or evidence for registered tools."""

    def pre_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str | None:
        # TODO: Block at least three recurring failure patterns before handlers
        # execute. Examples include invalid ranking weights, duplicate stock IDs,
        # or a chart with no declared population.
        return None

    def post_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        output: str,
        handlers: Any,
    ) -> list[tuple[str, str]]:
        # TODO: Return deterministic evidence or recovery information after a
        # completed tool call. Include one chart-evidence antidote.
        return []
