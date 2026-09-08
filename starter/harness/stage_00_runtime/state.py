"""Keep local harness memory during one running CLI session.

RuntimeState is the harness's own control memory across loop iterations: loaded
skills, the current plan, approval and permission status, and the current
request's tool log.
It is separate from the model conversation memory. main.py keeps
previous_response_id, which the Responses API uses on the next loop iteration
to continue the LLM conversation and remember prior user messages and tool
observations. Neither kind of memory survives program exit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeState:
    loaded_skills: dict[str, str] = field(default_factory=dict)
    tool_run_log: list[dict[str, Any]] = field(default_factory=list)
    execution_trace: list[dict[str, Any]] = field(default_factory=list)
    plan: list[dict[str, Any]] = field(default_factory=list)
    approval_required: bool = False
    approval_message: str | None = None
    permission_required: bool = False
    permission_request: dict[str, Any] | None = None
    granted_permission: dict[str, Any] | None = None

    def reset(self) -> None:
        self.loaded_skills.clear()
        self.tool_run_log.clear()
        self.execution_trace.clear()
        self.plan.clear()
        self.approval_required = False
        self.approval_message = None
        self.permission_required = False
        self.permission_request = None
        self.granted_permission = None
