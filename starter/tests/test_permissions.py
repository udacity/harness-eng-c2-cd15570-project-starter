"""Target contract for least-privilege tool permissions."""

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
