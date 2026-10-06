"""Loop 04 scaffold: authorize each protected request before it runs."""

from __future__ import annotations

from typing import Any

from .loop_01_non_production import HarnessLoop
from harness.stage_06_permissions import PermissionPolicy


class PermissionsLoop(HarnessLoop):
    """A grant applies to one exact tool name and argument object."""

    def __init__(self, *args: Any, **kwargs: Any):
        # Scoped approval and exact-call replay add model round trips beyond the
        # foundational loop's normal budget.
        kwargs.setdefault("max_loop_iterations", 30)
        super().__init__(*args, **kwargs)
        self.permissions = PermissionPolicy()

    @staticmethod
    def _same_request(left: dict[str, Any] | None, right: dict[str, Any]) -> bool:
        """Report whether a stored grant covers exactly this request."""
        # TODO: A grant is scoped to one tool name and one argument object.
        # Compare the stored request against the current one in full, so a
        # grant for plot_data(plot_type="scatter") cannot authorize a later
        # plot_data(plot_type="bar").
        raise NotImplementedError("Compare a stored grant with the current request.")

    def before_tool_execution(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> str | None:
        # TODO: Ask self.permissions.decide for allow, require_approval, or
        # deny. Log every check as {"component": "permission_check", "tool":
        # tool_name, "input": tool_input, "decision": decision, "reason":
        # reason}, then print exactly "PERMISSION CHECK: <tool_name> ->
        # <decision>". Use self._same_request against state.granted_permission
        # before blocking a protected call: on a match, clear that one-use grant
        # and let the handler execute. For deny, return a DENIED message. For
        # require_approval without a matching grant, save {"tool": tool_name,
        # "input": tool_input} in state.permission_request, set
        # state.permission_required, and return a BLOCKED message.
        raise NotImplementedError("Implement the Loop 04 permission check.")

    def pause_status(self) -> str | None:
        # TODO: Return "permission_required" while a protected request waits
        # for a human decision; otherwise return None.
        return None

    def grant_pending_permission(self) -> None:
        # TODO: Called by main.py only after the user approves. Move the
        # pending request into state.granted_permission and clear the pending
        # flag. Log {"component": "permission_grant", "tool": tool_name,
        # "input": tool_input, "event": "grant", "scope": "one_exact_call"}.
        # Then print exactly "PERMISSION GRANTED: <tool_name>". The grant is
        # consumed by the matching before_tool_execution.
        pass

    def resume_after_permission(
        self,
        permission_response: Any,
        tool_results: list[dict[str, Any]],
        starting_loop: int,
    ) -> dict[str, Any]:
        # TODO: Resume the inherited loop using permission_response.id.
        # Include tool_results plus a user message asking the model to reissue
        # the *identical* tool call and arguments. Do not run the tool here.
        raise NotImplementedError("Resume the exact approved request.")
