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
    assert loop.before_tool_execution("plot_data", request).startswith("BLOCKED")
    assert loop.pause_status() == "permission_required"
    assert state.permission_request == {"tool": "plot_data", "input": request}

    loop.grant_pending_permission()
    assert loop.before_tool_execution("plot_data", request) is None
    assert state.granted_permission is None

    changed = {**request, "plot_type": "bar"}
    assert loop.before_tool_execution("plot_data", changed).startswith("BLOCKED")
    assert loop.pause_status() == "permission_required"


def test_unknown_tool_is_denied():
    decision, reason = PermissionPolicy().decide("run_shell", {})
    assert decision == "deny"
    assert reason


def test_permission_decisions_are_printed_and_logged():
    state = RuntimeState()
    loop = PermissionsLoop(
        client=None,
        deployment="test",
        instructions=lambda: "",
        handlers=SimpleNamespace(),
        registry=SimpleNamespace(),
        state=state,
    )
    chart = {"dataset": "inventory", "filters": [], "x": "horsepower"}

    with redirect_stdout(io.StringIO()) as terminal:
        assert loop.before_tool_execution("dataset_info", {"dataset": "inventory"}) is None
        assert loop.before_tool_execution("plot_data", chart).startswith("BLOCKED")
        loop.grant_pending_permission()
        assert loop.before_tool_execution("plot_data", chart) is None

    output = terminal.getvalue()
    assert "PERMISSION CHECK: dataset_info -> allow" in output
    assert "PERMISSION CHECK: plot_data -> require_approval" in output
    assert "PERMISSION GRANTED: plot_data" in output

    entries = [e for e in state.tool_run_log if e.get("component") == "permission"]
    assert [e["decision"] for e in entries] == [
        "allow", "require_approval", "granted", "require_approval",
    ]
    assert all(e["tool"] and "input" in e for e in entries)
    assert entries[-1]["grant_used"] is True


def test_unknown_tool_call_reaches_the_policy_and_is_denied():
    state = RuntimeState()
    loop = PermissionsLoop(
        client=None,
        deployment="test",
        instructions=lambda: "",
        handlers=SimpleNamespace(dispatch={}),
        registry=SimpleNamespace(
            knowledge=frozenset(), planning=frozenset(), execution=frozenset(),
        ),
        state=state,
    )
    call = SimpleNamespace(
        type="function_call", name="run_shell", arguments="{}", call_id="c1",
    )

    with redirect_stdout(io.StringIO()):
        loop.dispatch_tools(SimpleNamespace(output=[call]))

    tool_entry = state.tool_run_log[-1]
    assert tool_entry["tool"] == "run_shell"
    assert tool_entry["status"] == "denied"
