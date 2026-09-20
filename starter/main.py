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
    create_llm_client,
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
        "Student TODO: add a retrospective review after the primary task completes.",
    ),
    "hooks": (
        "Hooks",
        HooksLoop,
        "Student TODO: validate calls and add deterministic chart evidence.",
    ),
    "permissions": (
        "Permissions",
        PermissionsLoop,
        "Student TODO: require scoped approval for plots and rankings.",
    ),
}

PROMPT_LOOPS = {
    "prompt_01_non_production.txt": "non-production",
    "prompt_02_self_evaluation.txt": "self-evaluation",
    "prompt_03_hooks.txt": "hooks",
    "prompt_04_permissions.txt": "permissions",
}

MASTER_PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "master_prompt.txt"


def read_prompt_file(path: Path) -> str:
    """Read one nonempty UTF-8 prompt."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"prompt file is empty: {path}")
    return text


def artifact_paths(output_dir: Path, loop_name: str, prompt_mode: bool) -> tuple[Path, Path, Path]:
    """Keep each loop's prompt run separate from its interactive session."""
    run_dir = output_dir / loop_name / ("prompt" if prompt_mode else "interactive")
    return (
        run_dir / "answer.md",
        run_dir / "tool_trace.json",
        run_dir / "retrospective_evaluation.json",
    )


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
    state.plan_approval_pending = False
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
            state.tool_run_log.append({
                "component": "plan_approval",
                "tool": "plan_approval",
                "decision": "approved",
                "status": "approved",
                "plan": list(state.plan),
            })
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
    # Load application paths and parse the harness options.
    config = AppConfig.from_environment()
    parser = argparse.ArgumentParser(
        description="Vehicle EDA harness with progressive skills and approved tools."
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="Run the shared master user prompt with one of the four supplied loop prompt files.",
    )
    parser.add_argument(
        "--loop-pause",
        action="store_true",
        help="Pause after each loop cycle so you can review it before continuing.",
    )
    args = parser.parse_args()
    if args.prompt_file and args.prompt_file.name == MASTER_PROMPT_FILE.name:
        parser.error("the master prompt is loaded automatically; select a loop prompt file")
    loop_stage = "non-production"
    if args.prompt_file:
        loop_stage = PROMPT_LOOPS.get(args.prompt_file.name)
        if loop_stage is None:
            parser.error("select one of the four supplied loop prompt files")
    output_file, tool_log_file, evaluation_file = artifact_paths(
        config.output_dir, loop_stage, args.prompt_file is not None
    )

    # Prompt-file runs pair one shared user request with loop-specific system instructions.
    user_prompt = None
    loop_instructions = ""
    if args.prompt_file:
        try:
            user_prompt = read_prompt_file(MASTER_PROMPT_FILE)
            loop_instructions = read_prompt_file(args.prompt_file)
        except (OSError, ValueError) as exc:
            parser.error(f"cannot load prompts: {exc}")

    # Build the single configured LLM client, skills catalog, tools, and loop.
    client, deployment, base_url = create_llm_client()
    state = RuntimeState()
    skills = SkillCatalog(config.skills_dir)
    handlers = ToolHandlers(config, state, skills)
    registry = ToolRegistry(handlers.dispatch)
    loop_name, loop_class, loop_note = LOOP_STAGES[loop_stage]
    loop = loop_class(
        client=client,
        deployment=deployment,
        instructions=lambda: build_system_prompt(config, skills, loop_instructions),
        handlers=handlers,
        registry=registry,
        state=state,
        loop_pause=args.loop_pause,
    )

    print(f"\nVehicle EDA Harness: {loop_name}")
    print("=" * (22 + len(loop_name)))
    print(f"Loop stage: {loop_stage}")
    print(f"LLM: {deployment} ({base_url})")
    print(f"Output folder: {output_file.parent}")
    print(loop_note)
    print(f"Tools available: {len(registry.definitions)}")
    print(f"Skills available: {len(skills.discover())}")
    print("Flow: model -> progressive skills/tools -> observation")
    if args.loop_pause:
        print("Loop pause: press Return after each cycle to continue.")
    if user_prompt is not None:
        print(f"User prompt: {MASTER_PROMPT_FILE}")
        print(f"Loop system prompt: {args.prompt_file}")
    if loop_stage == "self-evaluation":
        print(
            "Self-evaluation flow: completed EDA -> second LLM review of the "
            "prompt, trace, tool evidence, and final response"
        )
    if loop_stage == "hooks":
        print(
            "Hook flow: pre-tool validation -> tool execution -> "
            "post-tool deterministic antidote evidence"
        )
    if loop_stage == "permissions":
        print(
            "Permission flow: allow bounded EDA -> require scoped user approval "
            "for plots and inventory rankings"
        )

    # RuntimeState keeps local control state across loop iterations. This ID
    # separately lets the LLM continue its prior loop conversation.
    previous_response_id = None
    if user_prompt is not None:
        run_harness(
            loop,
            state,
            user_prompt,
            previous_response_id,
            output_file,
            tool_log_file,
            evaluation_file,
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
            output_file,
            tool_log_file,
            evaluation_file,
        )


if __name__ == "__main__":
    main()
