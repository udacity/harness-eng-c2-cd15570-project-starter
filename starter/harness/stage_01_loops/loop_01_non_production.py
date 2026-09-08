# =============================================================================
# Vehicle EDA non-production loop: progressive skills, tools, and approval
# =============================================================================

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from harness.stage_00_runtime.state import RuntimeState
from harness.stage_03_tools import ToolHandlers, ToolRegistry


class HarnessLoop:
    """Run prompt-driven EDA through progressive skills and approved tools."""

    def __init__(
        self,
        client: Any,
        deployment: str,
        instructions: Callable[[], str],
        handlers: ToolHandlers,
        registry: ToolRegistry,
        state: RuntimeState,
        max_loop_iterations: int = 20,
    ):
        self.client = client
        self.deployment = deployment
        self.instructions = instructions
        self.handlers = handlers
        self.registry = registry
        self.state = state
        self.max_loop_iterations = max_loop_iterations

    def before_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> str | None:
        """Allow production loop variants to block a tool before it runs."""
        return None

    def after_tool_execution(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        output: str,
    ) -> list[str]:
        """Allow production loop variants to add deterministic evidence."""
        return []

    def pause_status(self) -> str | None:
        """Allow production loop variants to request a non-plan user decision."""
        return None

    # =============================================================================
    # Send the user request or tool observations to the Azure OpenAI model
    # =============================================================================
    def run_model(self, request_input: Any, previous_response_id: str | None):
        # The model sees both progressive-disclosure skill tools and EDA tools.
        return self.client.responses.create(
            model=self.deployment,
            instructions=self.instructions(),
            input=request_input,
            tools=self.registry.definitions,
            previous_response_id=previous_response_id,
        )

    # =============================================================================
    # Execute selected skills and tools, then return their observations
    # =============================================================================
    def dispatch_tools(self, response: Any) -> list[dict[str, Any]]:
        results = []
        approval_requested = any(
            item.type == "function_call" and item.name == "request_approval"
            for item in response.output
        )
        for item in response.output:
            if item.type != "function_call":
                continue

            tool_name = item.name
            try:
                tool_input = json.loads(item.arguments)
            except json.JSONDecodeError as exc:
                tool_input, output = {}, f"ERROR invalid tool arguments: {exc}"
            else:
                handler = self.handlers.dispatch.get(tool_name)
                if handler is None:
                    output = f"ERROR unknown tool '{tool_name}'"
                elif (
                    tool_name in self.registry.execution
                    and (self.state.approval_required or approval_requested)
                ):
                    output = (
                        f"BLOCKED: '{tool_name}' cannot run until the user "
                        "approves the current plan."
                    )
                else:
                    hook_block = self.before_tool_execution(tool_name, tool_input)
                    output = hook_block if hook_block else handler(tool_input)

            component = (
                "skill" if tool_name in self.registry.knowledge
                else "planning tool" if tool_name in self.registry.planning
                else "EDA tool"
            )
            status = (
                "error" if output.startswith("ERROR")
                else "denied" if output.startswith("DENIED")
                else "blocked" if output.startswith("BLOCKED")
                else "completed"
            )
            self.state.tool_run_log.append({
                "tool": tool_name,
                "input": tool_input,
                "status": status,
                "output": str(output),
                "output_preview": str(output).replace("\n", " ")[:240],
            })
            print(f"  {component}: {tool_name}")
            print(f"  input: {json.dumps(tool_input, default=str)[:180]}")
            print(f"  status: {status}")

            hook_evidence = self.after_tool_execution(
                tool_name,
                tool_input,
                str(output),
            )

            # Full skill content returns only after the model chooses load_skill.
            observation = (
                f"{output}\n\n--- ACTIVE SKILLS ---\n"
                f"{', '.join(self.state.loaded_skills) or '(none)'}"
            )
            if hook_evidence:
                observation += "\n\n--- HOOK EVIDENCE ---\n" + "\n\n".join(hook_evidence)
            results.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": observation,
            })
        return results

    # =============================================================================
    # Show the prompt, model text, and requested skills and tools for each loop
    # =============================================================================
    def print_loop_trace(self, loop_number: int, request_input: Any, response: Any) -> None:
        print(f"\n========== LOOP {loop_number} ==========")
        print("PROMPT TO MODEL:")
        print(request_input if loop_number == 1 else "Tool observations from the previous loop.")

        print("\nMODEL OUTPUT:")
        print(
            response.output_text
            or "(No written response yet. The model only selected skills or "
            "tools, so the harness will run them before the next loop.)"
        )

        calls = [item.name for item in response.output if item.type == "function_call"]
        skills = [name for name in calls if name in self.registry.knowledge]
        planning = [name for name in calls if name in self.registry.planning]
        tools = [name for name in calls if name in self.registry.execution]
        self.state.execution_trace.append({
            "loop_number": loop_number,
            "model_output": response.output_text,
            "requested_skills": skills,
            "requested_planning_tools": planning,
            "requested_eda_tools": tools,
        })
        print("\nMODEL REQUESTED:")
        print(f"  skills: {', '.join(skills) or '(none)'}")
        print(f"  planning tools: {', '.join(planning) or '(none)'}")
        print(f"  EDA tools: {', '.join(tools) or '(none)'}")

    # =============================================================================
    # Continue until the model completes the request or pauses for approval
    # =============================================================================
    def _run_until_pause_or_complete(
        self,
        request_input: Any,
        previous_response_id: str | None,
        loop_number: int,
    ) -> dict[str, Any]:
        while True:
            response = self.run_model(request_input, previous_response_id)
            self.print_loop_trace(loop_number, request_input, response)

            tool_calls = [item for item in response.output if item.type == "function_call"]
            if not tool_calls:
                print("\nDecision: model completed the EDA request.")
                return {"status": "complete", "response": response}

            if loop_number >= self.max_loop_iterations:
                print("\nDecision: maximum loop iterations reached.")
                return {"status": "iteration_limit", "response": response}

            print("\nCOMPONENTS EXECUTED:")
            tool_results = self.dispatch_tools(response)
            if self.state.approval_required:
                print("\nDecision: plan approval is required before continuing.")
                return {
                    "status": "approval_required",
                    "response": response,
                    "tool_results": tool_results,
                    "loop_number": loop_number,
                }

            if pause_status := self.pause_status():
                print("\nDecision: scoped user permission is required before continuing.")
                return {
                    "status": pause_status,
                    "response": response,
                    "tool_results": tool_results,
                    "loop_number": loop_number,
                }

            request_input = tool_results
            previous_response_id = response.id
            loop_number += 1

    # =============================================================================
    # Start a new request and let the model use skills and tools as needed
    # =============================================================================
    def agent_loop(
        self,
        user_query: str,
        previous_response_id: str | None = None,
    ) -> dict[str, Any]:
        return self._run_until_pause_or_complete(user_query, previous_response_id, 1)

    # =============================================================================
    # Resume the model after the user explicitly approves the plan
    # =============================================================================
    def resume_after_approval(
        self,
        approval_response: Any,
        tool_results: list[dict[str, Any]],
        starting_loop: int,
    ) -> dict[str, Any]:
        self.state.approval_required = False
        self.state.approval_message = None
        request_input = tool_results + [{
            "type": "message",
            "role": "user",
            "content": "The user explicitly approved the plan. Continue the planned analysis.",
        }]
        return self._run_until_pause_or_complete(
            request_input,
            approval_response.id,
            starting_loop,
        )
