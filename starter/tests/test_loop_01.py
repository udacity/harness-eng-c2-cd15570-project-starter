"""Baseline contract: the foundational loop exposes extension points."""

from harness.stage_01_loops.loop_01_non_production import HarnessLoop


def test_foundational_loop_exposes_production_extension_points():
    assert callable(HarnessLoop.before_tool_execution)
    assert callable(HarnessLoop.after_tool_execution)
    assert callable(HarnessLoop.pause_status)
