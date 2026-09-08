"""TODO: Define explicit tool permissions for the production harness."""

from __future__ import annotations

from typing import Any


class PermissionPolicy:
    """Return allow, require_approval, or deny for each registered tool."""

    # TODO: Define explicit allow and approval-required tool sets.

    def decide(self, tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
        # TODO: Return an explicit decision and a reviewer-readable reason.
        # Unknown tools need a deny decision.
        raise NotImplementedError("Implement the permission policy.")
