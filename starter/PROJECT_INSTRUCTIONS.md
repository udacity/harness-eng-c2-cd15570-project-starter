# RouteLine Vehicle EDA Harness: Instructions

## Your Task

Build the RouteLine Vehicle EDA Harness as four progressively controlled loop
variants. Start with a closed tools-and-skills loop, then add retrospective
self-evaluation, deterministic hooks with antidotes, and scoped permissions.
Use the supplied vehicle datasets and loop-specific prompts to create saved,
inspectable evidence for each stage. Keep the model constrained to registered
tools and preserve the plan-approval flow throughout the project.

## Requirements

1. Implement Loop 01 with progressive skill loading, registered EDA tools,
   planning, and plan approval before planned EDA actions run.
2. Implement Loop 02 so it makes a separate retrospective evaluation call after
   task completion and saves structured evaluation JSON.
3. Implement Loop 03 so hooks validate tool activity and deterministic
   antidotes add chart evidence or block invalid requests.
4. Implement Loop 04 with explicit `allow`, `require_approval`, and `deny`
   permission decisions, including scoped approval for plot and ranking calls.
5. Create `prompt_01_non_production.txt` through `prompt_04_permissions.txt`,
   each designed to demonstrate the component added in its matching loop.
6. Submit generated answer files, tool traces, evaluation JSON, chart artifacts,
   and a written comparison of what each loop adds.

## Repository Structure

```text
starter/
├── data/
│   ├── synthetic_dealer_inventory.csv       # current synthetic dealer stock
│   ├── synthetic_vehicle_history.csv        # reliability and ownership history
│   ├── vehicle_sales_reviews.csv             # intentionally inconsistent records
│   └── README.md                             # data-use constraints
├── harness/
│   ├── stage_00_runtime/
│   │   ├── client_azure.py                   # device-code provider client
│   │   ├── client_openai.py                  # alternate provider client
│   │   ├── config.py                         # paths and runtime configuration
│   │   ├── persistence.py                    # save output artifacts
│   │   ├── prompt.py                         # system instructions
│   │   └── state.py                          # per-session harness state
│   ├── stage_01_loops/
│   │   ├── loop_01_non_production.py         # foundational loop
│   │   ├── loop_02_self_evaluation.py        # retrospective loop
│   │   ├── loop_03_hooks.py                  # hook and antidote loop
│   │   └── loop_04_permissions.py            # permission loop
│   ├── stage_02_skills/                      # provided skill files ← do not modify
│   ├── stage_03_tools/                       # registered tool contracts and handlers
│   ├── stage_04_evaluation/                  # TODO: evaluation component
│   ├── stage_05_antidotes/                   # TODO: deterministic antidotes
│   └── stage_06_permissions/                 # TODO: permission policy
├── prompts/                                  # Prompt 01 supplied; complete prompts 02-04
├── outputs/                                  # generated answers, traces, and plots
├── main.py                                   # CLI entry point
├── requirements.txt                          # dependencies ← do not modify
└── RUN_MAIN.md                               # command reference ← do not modify
```

Do not modify files in `data/` or `harness/stage_02_skills/`. Do not edit
generated files in `outputs/`; recreate them by rerunning a loop.

## Starter Code

Complete the control points in the supplied starter implementation. Keep the
public method contracts unchanged.

```python
# harness/stage_01_loops/loop_02_self_evaluation.py
class SelfEvaluationLoop(HarnessLoop):
    def _evaluate_if_finished(self, result: dict):
        # TODO: evaluate only a completed or iteration-limited task.
        # TODO: pass prompt, trace, tool log, and final response to the evaluator.
        # TODO: attach the validated JSON result to result["evaluation"].
        ...
```

```python
# harness/stage_06_permissions/policy.py
class PermissionPolicy:
    # TODO: define explicit allowed and approval-required tool sets.
    def decide(self, tool_name: str, tool_input: dict[str, Any]):
        # TODO: return allow, require_approval, or deny with a reason.
        ...
```

## Step-by-Step Guide

### Step 1: Prepare the runtime and data boundary

Complete `stage_00_runtime/config.py`, `state.py`, and `prompt.py`. Resolve
the three provided data paths from configuration. Maintain local state for the
current plan, loaded skills, tool trace, approval status, and permission state.
Keep model conversation continuity separate from local harness state.

Complete the provider client modules. Use device-code authentication and the
course-managed secret store for the default provider. Read alternate-provider
credentials from environment variables. Never hard-code a key.

### Step 2: Build the foundational loop

Complete `loop_01_non_production.py`, `stage_03_tools/registry.py`, and
`stage_03_tools/handlers.py`. Send the model the current system instructions,
the registered tool schemas, and either the user prompt or prior tool
observations. Dispatch only tools found in the closed registry.

Implement the plan gate. When the model calls `write_plan` and
`request_approval`, return control to `main.py`. Resume only after the user
approves. Record every tool request, input, status, and output in the run log.

Create `prompts/prompt_01_non_production.txt`. Require one skill, a plan, data
inspection, summaries, a hypothesis test, and charts. Run it with Loop 01 and
verify that `outputs/agent_output.txt`, `outputs/agent_tools.json`, and chart
artifacts are generated.

### Step 3: Add retrospective self-evaluation

Complete `stage_04_evaluation/retrospective_evaluation.py` and
`loop_02_self_evaluation.py`. After the primary model returns a completed
response, make a second model call that receives the original prompt, complete
execution trace, tool-run log, task status, and final answer.

Validate the evaluator response against the required JSON schema:
`task_status`, `efficiency_score`, `critique`,
`systemic_failure_root_cause`, and `workflow_adjustments`. Save the result to
`outputs/retrospective_evaluation.json`. Create `prompt_02_self_evaluation.txt`
so the evaluator can identify an evidence or efficiency weakness in the run.

### Step 4: Add hooks and deterministic antidotes

Complete `stage_05_antidotes/` and `loop_03_hooks.py`. Add pre-tool hooks that
block invalid ranking weights, duplicate comparison IDs, or charts without a
declared population. Add post-tool hooks that append deterministic evidence to
the model observation after a chart runs.

Make the plotting antidote return chart population details, grouped means and
counts for a bar chart, or ranges and correlation for a scatter plot. Create
`prompt_03_hooks.txt` that explicitly creates charts and requires the final
answer to use the hook-provided evidence. Save the resulting tool trace.

### Step 5: Add scoped permissions

Complete `stage_06_permissions/policy.py` and `loop_04_permissions.py`. Define
an explicit allow list for read-only tools, require approval for `plot_data`
and `rank_inventory`, and deny tools outside the policy. Record each decision
in the tool trace.

When a protected tool is requested, return a permission-required result to
`main.py`. Display the exact tool name and arguments, collect the user's
decision, and grant one use only when the retried call exactly matches the
approved request. Create `prompt_04_permissions.txt` that uses an allowed
inspection tool, a protected plot, and a protected ranking.

### Step 6: Run and compare the stages

Run all four prompts with their matching loop option. Preserve the generated
artifacts under `outputs/`. Write a short comparison that identifies the added
control, evidence source, and observed intervention for each loop.

```bash
python main.py --loop non-production --prompt-file prompts/prompt_01_non_production.txt
python main.py --loop self-evaluation --prompt-file prompts/prompt_02_self_evaluation.txt
python main.py --loop hooks --prompt-file prompts/prompt_03_hooks.txt
python main.py --loop permissions --prompt-file prompts/prompt_04_permissions.txt
```

## Implementation Hints

1. Preserve the same tool dispatcher in every loop; extend lifecycle methods
   instead of copying the agent loop for each stage.
2. Treat an empty chart filter list as an explicit full-dataset population, not
   as a missing population declaration.
3. Return structured error messages to the model for malformed tool arguments;
   do not raise unhandled exceptions from a handler.
4. Store the original protected request before requesting permission, then
   compare the retried call against it before consuming the grant.
5. Keep the evaluator separate from the primary response path so it cannot
   silently rewrite the original answer.

## Best Practices

1. Use JSON for tool, evaluator, hook, and permission evidence so artifacts are
   easy to inspect and compare.
2. Keep write operations bounded to `outputs/` and deny arbitrary execution.
3. Use each loop's dedicated prompt so the added component has observable work
   to perform.

## Submission Checklist

- [ ] Loop 01 supports skills, tools, planning, and plan approval.
- [ ] Loop 02 saves a valid retrospective evaluation JSON artifact.
- [ ] Loop 03 records hook intervention and deterministic chart evidence.
- [ ] Loop 04 records allow, approval-required, granted, and denied decisions.
- [ ] Four loop-specific prompt files exist and run with their matching loop.
- [ ] `outputs/` contains completed answers, tool traces, evaluation JSON, and
  generated chart artifacts.
- [ ] A written comparison of the four loop controls is included.

## Stand-Out Suggestions

1. Add tests that prove a changed protected request cannot consume a prior grant.
2. Add an ablation table comparing output quality and tool use across the four
   loop stages.
3. Add a failure log that maps repeated agent mistakes to a hook or antidote.
4. Add per-run cost and token accounting to the persisted trace.
5. Add a data-quality prompt using `vehicle_sales_reviews.csv` and document how
   malformed fields affect the analysis.

## Example Queries and Test Cases

| Loop | Prompt behavior to verify | Expected evidence |
|---|---|---|
| Loop 01 | Load a skill, create a plan, use summaries and a chart. | Tool trace and PNG chart. |
| Loop 02 | Complete a chart-based EDA with a traceable weakness. | Retrospective JSON with critique and adjustment. |
| Loop 03 | Create a scatter and a grouped bar chart. | Hook records and deterministic chart statistics. |
| Loop 04 | Inspect data, plot, and rank inventory. | Allowed decision plus two separate scoped approvals. |
