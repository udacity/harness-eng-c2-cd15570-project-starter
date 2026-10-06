"""Baseline contract: the foundational loop exposes extension points."""

from types import SimpleNamespace

from harness.stage_00_runtime.state import RuntimeState
from harness.stage_01_loops.loop_01_non_production import HarnessLoop


def test_foundational_loop_exposes_production_extension_points():
    assert callable(HarnessLoop.before_tool_execution)
    assert callable(HarnessLoop.after_tool_execution)
    assert callable(HarnessLoop.pause_status)


def test_unknown_tool_passes_through_pre_execution_hook():
    class DenyingLoop(HarnessLoop):
        def before_tool_execution(self, tool_name, tool_input):
            assert tool_name == "run_shell"
            assert tool_input == {}
            return "DENIED: unsupported tool"

    state = RuntimeState()
    loop = DenyingLoop(
        client=None,
        deployment="test",
        instructions=lambda: "",
        handlers=SimpleNamespace(dispatch={}),
        registry=SimpleNamespace(
            knowledge=frozenset(),
            planning=frozenset(),
            execution=frozenset(),
        ),
        state=state,
    )
    response = SimpleNamespace(output=[SimpleNamespace(
        type="function_call",
        name="run_shell",
        arguments="{}",
        call_id="call-unknown",
    )])

    results = loop.dispatch_tools(response)

    assert results[0]["output"].startswith("DENIED")
    assert state.tool_run_log[0]["status"] == "denied"
