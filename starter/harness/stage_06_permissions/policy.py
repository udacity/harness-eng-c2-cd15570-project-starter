"""Loop 04 component: classify tools by least-privilege policy."""

from __future__ import annotations

from typing import Any


class PermissionPolicy:
    """Return allow, require_approval, or deny for each registered tool."""

    # TODO: Add the skill, planning, and bounded read-only EDA tool names.
    ALLOWED = frozenset()
    # TODO: plot_data and rank_inventory require a separate human grant.
    APPROVAL_REQUIRED = frozenset()

    def decide(self, tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
        # TODO: Return ("allow", reason) for ALLOWED;
        # ("require_approval", reason) for APPROVAL_REQUIRED; otherwise
        # ("deny", reason). The reason is printed and saved in the tool trace.
        raise NotImplementedError("Implement the permission policy.")
