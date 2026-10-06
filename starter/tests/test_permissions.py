"""Target contract for least-privilege tool permissions."""

import io
from contextlib import redirect_stdout
from types import SimpleNamespace

from harness.stage_00_runtime.state import RuntimeState
from harness.stage_01_loops.loop_04_permissions import PermissionsLoop
from harness.stage_06_permissions import PermissionPolicy


def test_permission_policy_allows_read_only_eda():
    decision, _ = PermissionPolicy().decide(
        "dataset_info",
        {"dataset": "inventory"},
    )
    assert decision == "allow"


def test_permission_loop_records_canonical_allow_decision():
    state = RuntimeState()
    loop = PermissionsLoop(
        client=None,
        deployment="test",
        instructions=lambda: "",
        handlers=SimpleNamespace(),
        registry=SimpleNamespace(),
        state=state,
    )
    request = {"dataset": "inventory"}

    with redirect_stdout(io.StringIO()) as terminal:
        assert loop.before_tool_execution("dataset_info", request) is None
    assert "PERMISSION CHECK: dataset_info -> allow" in terminal.getvalue()
    check = state.tool_run_log[-1]
    assert check["component"] == "permission_check"
    assert check["tool"] == "dataset_info"
    assert check["input"] == request
    assert check["decision"] == "allow"
    assert check["reason"]


def test_protected_grant_is_scoped_to_one_exact_call():
    state = RuntimeState()
    loop = PermissionsLoop(
        client=None,
        deployment="test",
        instructions=lambda: "",
        handlers=SimpleNamespace(),
        registry=SimpleNamespace(),
        state=state,
    )
    request = {"dataset": "inventory", "filters": [], "plot_type": "scatter"}
    terminal = io.StringIO()
    with redirect_stdout(terminal):
        result = loop.before_tool_execution("plot_data", request)
    assert result.startswith("BLOCKED")
    assert "PERMISSION CHECK: plot_data -> require_approval" in terminal.getvalue()
    assert loop.pause_status() == "permission_required"
    assert state.permission_request == {"tool": "plot_data", "input": request}
    check = state.tool_run_log[-1]
    assert check["component"] == "permission_check"
    assert check["tool"] == "plot_data"
    assert check["input"] == request
    assert check["decision"] == "require_approval"
    assert check["reason"]

    with redirect_stdout(terminal):
        loop.grant_pending_permission()
    assert "PERMISSION GRANTED: plot_data" in terminal.getvalue()
    grant = state.tool_run_log[-1]
    assert grant == {
        "component": "permission_grant",
        "tool": "plot_data",
        "input": request,
        "event": "grant",
        "scope": "one_exact_call",
    }
    assert loop.before_tool_execution("plot_data", request) is None
    assert state.granted_permission is None

    changed = {**request, "plot_type": "bar"}
    assert loop.before_tool_execution("plot_data", changed).startswith("BLOCKED")
    assert loop.pause_status() == "permission_required"


def test_unknown_tool_is_denied():
    decision, reason = PermissionPolicy().decide("run_shell", {})
    assert decision == "deny"
    assert reason
