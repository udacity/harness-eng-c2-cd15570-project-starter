"""Hook runs should show both a successful check and chart evidence."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from harness.stage_00_runtime.state import RuntimeState
from harness.stage_01_loops.loop_03_hooks import HooksLoop


class HookVisibilityTests(unittest.TestCase):
    def make_loop(self):
        state = RuntimeState()
        handlers = SimpleNamespace(plot_evidence=lambda _: "Chart population: 10 rows")
        loop = HooksLoop(
            client=None,
            deployment="test-model",
            instructions=lambda: "",
            handlers=handlers,
            registry=SimpleNamespace(),
            state=state,
        )
        return loop, state

    def test_valid_chart_shows_pre_check_and_post_chart_evidence(self):
        loop, state = self.make_loop()
        chart_input = {"filters": [], "dataset": "inventory", "x": "horsepower"}

        with redirect_stdout(io.StringIO()) as terminal:
            self.assertIsNone(loop.before_tool_execution("plot_data", chart_input))
            observations = loop.after_tool_execution(
                "plot_data", chart_input, "Chart created"
            )

        output = terminal.getvalue()
        self.assertIn("HOOK pre-tool check: plot_data", output)
        self.assertIn("HOOK pre-tool decision: continue plot_data", output)
        self.assertIn("HOOK post-tool evidence: plot_data", output)
        self.assertIn("ANTIDOTE plot-evidence: completed", output)
        self.assertIn("Chart population: 10 rows", observations[0])
        self.assertEqual(state.tool_run_log[0]["status"], "continued")
        self.assertEqual(state.tool_run_log[1]["antidote"], "plot-evidence")

    def test_invalid_chart_shows_block_reason(self):
        loop, state = self.make_loop()

        with redirect_stdout(io.StringIO()) as terminal:
            result = loop.before_tool_execution("plot_data", {"dataset": "inventory"})
            observations = loop.after_tool_execution(
                "plot_data", {"dataset": "inventory"}, result
            )

        self.assertIn("BLOCKED BY HOOK", result)
        self.assertIn("HOOK pre-tool validation: blocked plot_data", terminal.getvalue())
        self.assertIn("HOOK post-tool: no antidote for plot_data", terminal.getvalue())
        self.assertEqual(observations, [])
        self.assertEqual(state.tool_run_log[0]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
