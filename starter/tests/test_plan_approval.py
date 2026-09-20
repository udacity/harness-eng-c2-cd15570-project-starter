"""Regression checks for the plan approval gate."""

from __future__ import annotations

import json
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from main import artifact_paths, run_harness
from harness.stage_00_runtime.state import RuntimeState
from harness.stage_01_loops.loop_01_non_production import HarnessLoop


def response(response_id: str, text: str = "", call: tuple[str, dict] | None = None):
    output = []
    if text:
        output.append(SimpleNamespace(
            type="message",
            role="assistant",
            content=[{"type": "output_text", "text": text}],
        ))
    if call:
        name, arguments = call
        output.append(SimpleNamespace(
            type="function_call",
            name=name,
            arguments=json.dumps(arguments),
            call_id=f"call-{response_id}",
        ))
    return SimpleNamespace(id=response_id, output_text=text, output=output)


class QueuedResponses:
    def __init__(self, responses):
        self.remaining = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.remaining.pop(0)


class PlanApprovalTests(unittest.TestCase):
    def test_artifacts_are_separate_for_each_loop_and_mode(self):
        base = Path("outputs")
        prompt_paths = artifact_paths(base, "hooks", True)
        interactive_paths = artifact_paths(base, "hooks", False)
        other_loop_paths = artifact_paths(base, "permissions", True)

        self.assertEqual(prompt_paths[0], base / "hooks/prompt/answer.md")
        self.assertEqual(prompt_paths[1], base / "hooks/prompt/tool_trace.json")
        self.assertNotEqual(prompt_paths, interactive_paths)
        self.assertNotEqual(prompt_paths, other_loop_paths)

    def make_loop(self, responses):
        state = RuntimeState()
        executed = []

        def dataset_info(arguments):
            executed.append(arguments)
            return "Dataset inspected"

        client = SimpleNamespace(responses=QueuedResponses(responses))
        handlers = SimpleNamespace(dispatch={"dataset_info": dataset_info})
        registry = SimpleNamespace(
            definitions=[],
            knowledge=frozenset(),
            planning=frozenset(),
            execution=frozenset({"dataset_info"}),
        )
        loop = HarnessLoop(client, "test-model", lambda: "", handlers, registry, state)
        return loop, state, executed

    def test_plain_text_plan_pauses_and_blocks_early_analysis(self):
        loop, state, executed = self.make_loop([
            response("r1", call=("dataset_info", {"dataset": "inventory"})),
            response("r2", "My plan:\n1. Inspect inventory.\n2. Summarize prices."),
            response("r3", call=("dataset_info", {"dataset": "inventory"})),
            response("r4", "Analysis complete."),
        ])

        paused = loop.agent_loop("Write a plan and ask for my approval before analysis.")
        self.assertEqual(paused["status"], "approval_required")
        self.assertEqual(executed, [])
        self.assertEqual(state.tool_run_log[0]["status"], "blocked")
        self.assertIn("Inspect inventory", state.plan[0]["task"])

        finished = loop.resume_after_approval(
            paused["response"], paused["tool_results"], paused["loop_number"] + 1
        )
        self.assertEqual(finished["status"], "complete")
        self.assertEqual(executed, [{"dataset": "inventory"}])

    def test_request_without_plan_approval_can_finish_normally(self):
        loop, state, _ = self.make_loop([response("r1", "Done.")])

        result = loop.agent_loop("Summarize the dataset.")

        self.assertEqual(result["status"], "complete")
        self.assertFalse(state.plan_approval_pending)

    def test_response_without_text_or_tool_call_is_not_complete(self):
        loop, _, _ = self.make_loop([response("r1")])

        with self.assertRaisesRegex(RuntimeError, "neither text nor a tool call"):
            loop.agent_loop("Summarize the dataset.")

    def test_trace_prints_full_model_output_item(self):
        loop, _, _ = self.make_loop([])
        model_response = response(
            "r1", call=("dataset_info", {"dataset": "inventory"})
        )

        with redirect_stdout(io.StringIO()) as captured:
            loop.print_loop_trace(1, "Inspect inventory.", model_response)

        raw_json = captured.getvalue().split(
            "RAW MODEL OUTPUT (response.output):\n", 1
        )[1].split("\nMODEL TEXT:", 1)[0]
        self.assertEqual(json.loads(raw_json), [{
            "type": "function_call",
            "name": "dataset_info",
            "arguments": '{"dataset": "inventory"}',
            "call_id": "call-r1",
        }])

    def test_raw_prompt_matches_each_model_call(self):
        loop, _, _ = self.make_loop([
            response("r1", call=("dataset_info", {"dataset": "inventory"})),
            response("r2", "Done."),
        ])

        with redirect_stdout(io.StringIO()) as captured:
            loop.agent_loop("Inspect inventory.")

        printed_prompts = [
            json.loads(section.split("\nINPUT TO MODEL:", 1)[0])
            for section in captured.getvalue().split("RAW PROMPT TO MODEL:\n")[1:]
        ]
        self.assertEqual(len(printed_prompts), 2)
        for printed, call in zip(printed_prompts, loop.client.responses.calls):
            self.assertEqual(printed, {
                "instructions": call["instructions"],
                "input": call["input"],
                "previous_response_id": call["previous_response_id"],
            })
        self.assertEqual(printed_prompts[0]["input"], "Inspect inventory.")
        self.assertEqual(printed_prompts[1]["previous_response_id"], "r1")

    def test_loop_pause_waits_after_tools_before_next_model_cycle(self):
        loop, _, executed = self.make_loop([
            response("r1", call=("dataset_info", {"dataset": "inventory"})),
            response("r2", "Analysis complete."),
        ])
        loop.loop_pause = True
        pause_prompts = []

        def review(prompt):
            pause_prompts.append(prompt)
            self.assertEqual(executed, [{"dataset": "inventory"}])
            self.assertEqual(len(loop.client.responses.remaining), 1)
            return ""

        with patch("builtins.input", side_effect=review):
            result = loop.agent_loop("Summarize the dataset.")

        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(pause_prompts), 1)
        self.assertIn("Loop 1 complete", pause_prompts[0])

    def test_loop_pause_waits_before_plan_approval(self):
        loop, _, _ = self.make_loop([response("r1", "My plan: inspect inventory.")])
        loop.loop_pause = True

        with patch("builtins.input", return_value="") as review:
            result = loop.agent_loop("Make a plan and ask for approval.")

        self.assertEqual(result["status"], "approval_required")
        review.assert_called_once()

    def test_cli_flow_saves_analysis_after_approval(self):
        loop, state, executed = self.make_loop([
            response("r1", "My plan:\n1. Inspect inventory."),
            response("r2", call=("dataset_info", {"dataset": "inventory"})),
            response("r3", "Analysis complete."),
        ])

        with TemporaryDirectory() as temp_dir, patch("builtins.input", return_value="y") as ask:
            output_file = Path(temp_dir) / "answer.md"
            with redirect_stdout(io.StringIO()):
                result_id = run_harness(
                    loop,
                    state,
                    "Write a plan and ask for my approval before analysis.",
                    None,
                    output_file,
                    Path(temp_dir) / "tools.json",
                    Path(temp_dir) / "evaluation.json",
                )

            self.assertEqual(result_id, "r3")
            self.assertEqual(output_file.read_text(encoding="utf-8"), "Analysis complete.\n")
            self.assertEqual(executed, [{"dataset": "inventory"}])
            self.assertTrue(any(
                item.get("component") == "plan_approval"
                and item.get("decision") == "approved"
                for item in state.tool_run_log
            ))
            ask.assert_called_once_with("Approve plan? [y/N]: ")


if __name__ == "__main__":
    unittest.main()
