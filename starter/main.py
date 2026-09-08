# =============================================================================
# CLI entry point for the foundational Vehicle EDA harness
# =============================================================================

from __future__ import annotations

import argparse
from pathlib import Path

from harness import (
    AppConfig,
    HarnessLoop,
    RuntimeState,
    build_system_prompt,
    create_azure_client,
    create_openai_client,
)
from harness.stage_00_runtime.persistence import (
    write_evaluation_artifact,
    write_run_artifacts,
)
from harness.stage_01_loops.loop_02_self_evaluation import SelfEvaluationLoop
from harness.stage_01_loops.loop_03_hooks import HooksLoop
from harness.stage_01_loops.loop_04_permissions import PermissionsLoop
from harness.stage_02_skills import SkillCatalog
from harness.stage_03_tools import ToolHandlers, ToolRegistry


LOOP_STAGES = {
    "non-production": ("Non-Production", HarnessLoop, "Active baseline loop."),
    "self-evaluation": (
        "Self-Evaluation",
        SelfEvaluationLoop,
        "TODO: implement retrospective evaluation after the primary task completes.",
    ),
    "hooks": (
        "Hooks",
        HooksLoop,
        "TODO: implement hooks and deterministic antidotes.",
    ),
    "permissions": (
        "Permissions",
        PermissionsLoop,
        "TODO: implement scoped permissions for consequential tool calls.",
    ),
}


# =============================================================================
# Run one prompt through the foundational skills-and-tools harness
# =============================================================================
def run_harness(
    loop: HarnessLoop,
    state: RuntimeState,
    query: str,
    previous_response_id: str | None,
    output_file: Path,
    tool_log_file: Path,
    evaluation_file: Path,
) -> str:
    # Start a fresh trace and approval state for this request.
    state.tool_run_log.clear()
    state.execution_trace.clear()
    state.plan.clear()
    state.approval_required = False
    state.approval_message = None
    state.permission_required = False
    state.permission_request = None
    state.granted_permission = None
    result = loop.agent_loop(query, previous_response_id)

    while result["status"] in {"approval_required", "permission_required"}:
        if result["status"] == "approval_required":
            print("\n========== PLAN FOR APPROVAL ==========")
            for item in state.plan:
                print(f"{item['id']}. {item['task']}")
            print(f"\n{state.approval_message}")
            prompt = "Approve plan? [y/N]: "
        else:
            request = state.permission_request or {}
            print("\n========== PERMISSION FOR APPROVAL ==========")
            print(f"Tool: {request.get('tool', '(unknown)')}")
            print("Requested arguments:")
            print(request.get("input", {}))
            print("\nThis permission applies only to this exact tool call.")
            prompt = "Grant permission? [y/N]: "

        answer = input(prompt).strip().lower()
        if answer not in {"y", "yes", "approve", "approved"}:
            print("Approval rejected. Analysis stopped.")
            return result["response"].id
        if result["status"] == "approval_required":
            result = loop.resume_after_approval(
                result["response"],
                result["tool_results"],
                result["loop_number"] + 1,
            )
        else:
            if not isinstance(loop, PermissionsLoop):
                raise RuntimeError("permission approval was requested by a loop without a permission policy")
            loop.grant_pending_permission()
            result = loop.resume_after_permission(
                result["response"],
                result["tool_results"],
                result["loop_number"] + 1,
            )

    # Save the completed EDA response and its tool trace.
    response = result["response"]
    print("\n========== FINAL EDA RESULT ==========\n" + response.output_text)
    write_run_artifacts(response, state.tool_run_log, output_file, tool_log_file)
    print(f"\nSaved EDA result to: {output_file}")
    print(f"Saved tool trace to: {tool_log_file}")
    if evaluation := result.get("evaluation"):
        write_evaluation_artifact(evaluation, evaluation_file)
        print(f"Saved retrospective evaluation to: {evaluation_file}")
    return response.id


# =============================================================================
# Configure the foundational harness and run file-based or interactive prompts
# =============================================================================
def main() -> None:
    # Load environment defaults, then allow CLI arguments to override them.
    config = AppConfig.from_environment()
    parser = argparse.ArgumentParser(
        description="Vehicle EDA harness with progressive skills and approved tools."
    )
    parser.add_argument(
        "--provider",
        choices=["azure", "openai"],
        default="azure",
        help="LLM provider to use. Defaults to azure.",
    )
    parser.add_argument(
        "--model",
        help="Azure deployment or OpenAI model name. Uses the provider default when omitted.",
    )
    parser.add_argument("--prompt-file", type=Path, help="Read one complete user request from a UTF-8 text file, then exit.")
    parser.add_argument("--output-file", type=Path, default=config.output_dir / "agent_output.txt", help="Write the completed EDA result here.")
    parser.add_argument("--tool-log-file", type=Path, default=config.output_dir / "agent_tools.json", help="Write tool activity here.")
    parser.add_argument("--evaluation-file", type=Path, default=config.output_dir / "retrospective_evaluation.json", help="Write retrospective evaluation here when using loop 02.")
    parser.add_argument(
        "--loop",
        choices=LOOP_STAGES,
        default="non-production",
        help="Harness loop stage to run. Defaults to non-production.",
    )
    args = parser.parse_args()

    # A prompt file runs one reproducible EDA request instead of interactive input.
    prompt_text = None
    if args.prompt_file:
        try:
            prompt_text = args.prompt_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            parser.error(f"cannot read prompt file: {exc}")
        if not prompt_text:
            parser.error("prompt file is empty")

    # Build the selected provider client, skills catalog, registered tools, and loop.
    if args.provider == "azure":
        client, deployment = create_azure_client(config.vault_url, args.model)
    else:
        client, deployment = create_openai_client(args.model)
    state = RuntimeState()
    skills = SkillCatalog(config.skills_dir)
    handlers = ToolHandlers(config, state, skills)
    registry = ToolRegistry(handlers.dispatch)
    loop_name, loop_class, loop_note = LOOP_STAGES[args.loop]
    loop = loop_class(
        client=client,
        deployment=deployment,
        instructions=lambda: build_system_prompt(config, skills),
        handlers=handlers,
        registry=registry,
        state=state,
    )

    print(f"\nVehicle EDA Harness: {loop_name}")
    print("=" * (22 + len(loop_name)))
    print(f"Loop stage: {args.loop}")
    print(f"LLM provider: {args.provider} ({deployment})")
    print(loop_note)
    print(f"Tools available: {len(registry.definitions)}")
    print(f"Skills available: {len(skills.discover())}")
    print("Flow: model -> progressive skills/tools -> observation")
    if args.loop == "self-evaluation":
        print(
            "Self-evaluation flow: completed EDA -> second LLM review of the "
            "prompt, trace, tool evidence, and final response"
        )
    if args.loop == "hooks":
        print(
            "Hook flow: pre-tool validation -> tool execution -> "
            "post-tool deterministic antidote evidence"
        )
    if args.loop == "permissions":
        print(
            "Permission flow: allow bounded EDA -> require scoped user approval "
            "for inventory rankings"
        )

    # RuntimeState keeps local control state across loop iterations. This ID
    # separately lets the LLM provider continue its prior loop conversation.
    previous_response_id = None
    if prompt_text is not None:
        run_harness(
            loop,
            state,
            prompt_text,
            previous_response_id,
            args.output_file,
            args.tool_log_file,
            args.evaluation_file,
        )
        return

    # Continue the LLM conversation across interactive requests.
    while True:
        try:
            query = input("\n\033[36mvehicle-eda >> \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return
        if query.lower() in {"", "q", "quit", "exit"}:
            return
        previous_response_id = run_harness(
            loop,
            state,
            query,
            previous_response_id,
            args.output_file,
            args.tool_log_file,
            args.evaluation_file,
        )


if __name__ == "__main__":
    main()
