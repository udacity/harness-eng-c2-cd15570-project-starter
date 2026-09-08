# Production Vehicle EDA Harness

Build a basic vehicle EDA agent into a production-oriented harness with
evaluation, deterministic controls, and scoped permissions.

---

## Overview

### What You'll Learn

You will extend a working model-and-tools loop without replacing its core
orchestration. The project moves from a foundational Loop 01 to production
loops that evaluate completed work, intercept unsafe actions, and require
approval for consequential tool calls.

Learning objectives:
- Implement retrospective evaluation from a complete execution trace.
- Implement hooks and deterministic antidotes around tool execution.
- Enforce least-privilege permissions with scoped approval.

### Prerequisites

- Python 3.12 and the packages in `requirements.txt`.
- Access to a configured language-model provider.

---

## Understanding the Concept

### The Problem

A vehicle analyst can ask a model to inspect inventory, calculate a statistic,
or rank vehicles. A basic agent loop can complete those actions, but it does
not independently assess whether its final analysis is grounded, prevent a
repeated unsafe tool pattern, or distinguish a safe summary from a
buyer-impacting ranking.

### The Solution

This starter gives you a functioning Loop 01 with progressive skills, closed
tools, planning, approval, tracing, and output persistence. You add three
production layers around that shared foundation rather than duplicating the
agent loop for every new control.

### How It Works

**Step 1: Run the foundational loop.** Loop 01 sends the prompt and registered
tools to the model, dispatches selected tools, and returns observations.

**Step 2: Evaluate completed work.** Loop 02 uses the prompt, trace, tool log,
and final answer to create structured retrospective evidence.

**Step 3: Intercept tool activity.** Loop 03 runs hooks before and after tools
to block recurring failures and attach deterministic evidence.

**Step 4: Authorize protected actions.** Loop 04 permits bounded EDA, pauses
for scoped approval, and denies tools outside the policy.

### Key Terms

**Execution trace**: The ordered record of model responses and requested tool
categories during one task.

**Antidote**: A deterministic action that blocks, corrects, or enriches a tool
result after a hook identifies a known failure pattern.

**Scoped permission**: A user grant that applies only to one exact protected
tool request and its arguments.

---

## Exercise Instructions

### Your Task

Complete Loops 02 through 04 while preserving the working Loop 01 behavior.
Create a distinct prompt for every loop, run the resulting workflows, and save
the evaluation, hook, permission, ablation, failure-log, and cost evidence
required by the project instructions.

### Requirements

Your implementation must:
1. Add a second model call that evaluates a completed task using the full trace.
2. Add at least three deterministic hook checks and one post-tool antidote.
3. Add explicit allow, approval-required, and deny permission decisions.
4. Create reproducible prompts and complete the report templates in `reports/`.

### Repository Structure

```text
starter/
├── data/                         # provided datasets; do not modify
├── harness/
│   ├── stage_01_loops/           # modify Loops 02, 03, and 04
│   ├── stage_02_skills/          # provided skills; do not modify
│   ├── stage_03_tools/           # provided closed EDA tools
│   ├── stage_04_evaluation/      # implement evaluator TODOs
│   ├── stage_05_antidotes/       # implement hook defenses
│   └── stage_06_permissions/     # implement permission policy
├── prompts/                      # complete prompts 02 through 04
├── reports/                      # complete evidence templates
├── tests/                        # turn production contracts green
├── main.py                       # provided CLI and approval flow
└── requirements.txt              # provided dependencies
```

### Starter Code

Loop 02 preserves the Loop 01 contract but intentionally has no evaluator:

```python
class SelfEvaluationLoop(HarnessLoop):
    def agent_loop(self, user_query: str, previous_response_id: str | None = None):
        # TODO: Save the original prompt, run the primary loop, then evaluate a
        # completed or iteration-limited result with the full execution trace.
        return super().agent_loop(user_query, previous_response_id)
```

### Expected Behavior

After completion, Loop 02 saves structured evaluator output. Loop 03 records
hook and antidote activity in the tool trace. Loop 04 displays a separate
approval prompt for protected actions and rejects unsupported tools.

**Example usage:**

```bash
pip install -r requirements.txt
python main.py --loop non-production --prompt-file prompts/prompt_01_non_production.txt
pytest
```

**Expected output after completion:**

```text
4 passed
Saved retrospective evaluation to: outputs/retrospective_evaluation.json
HOOK post-tool evidence: plot_data
PERMISSION GRANTED: rank_inventory
```

### Implementation Hints

1. Use `HarnessLoop.before_tool_execution`,
   `after_tool_execution`, and `pause_status` instead of copying the loop.
2. Treat saved tool evidence as the evaluator's source of truth.
3. Store a protected request before approval and compare the retried request
   before consuming its grant.

---

## Important Details

### Common Misconceptions

**Misconception**: "Self-evaluation changes the primary answer."
**Reality**: The evaluator produces a separate critique artifact after the
primary task finishes.

**Misconception**: "A hook is the same as an antidote."
**Reality**: A hook detects the lifecycle event; an antidote performs the
deterministic prevention or evidence-producing action.

### Best Practices

1. **Preserve the closed registry**: Route all model actions through the
   registered handlers rather than adding arbitrary execution access.
2. **Persist evidence**: Save outputs and traces before comparing loop stages.

### Common Errors

**Error**: A protected tool runs before a user decision.
- **Cause**: The permission check does not return a pause status.
- **Solution**: Store the request, return `permission_required`, and resume
  only after the exact request receives a grant.

**Error**: A chart claim has no supporting values.
- **Cause**: The loop saves chart metadata but not the data behind the chart.
- **Solution**: Add a deterministic antidote that returns grouped values or
  numeric relationships to the next model observation.
