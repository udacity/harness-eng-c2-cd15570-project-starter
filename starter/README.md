# RouteLine Vehicle EDA Harness

Cedar Lane Motors wants a harness that explores its vehicle data and shows how an agent reaches its conclusions. You will start with a non-production model-and-tools loop, then add self-evaluation, hooks, and scoped permissions. All four loops must answer the same question:

> What patterns and trade-offs in performance, price, vehicle condition, and ownership costs appear in the dealership's inventory and vehicle-history data?

Your submission must show the answer from each loop and evidence that its added component actually ran. The Loop 04 inventory ranking is an illustration of the permission flow; it is not a purchase recommendation.

## The four loops

| Loop | What it does | Evidence you will show |
| --- | --- | --- |
| 01 — Non-production | Loads a vehicle skill, plans the analysis, asks for plan approval, calls registered EDA tools, and returns tool results to the model. | Skill load, approval before analysis, tool results, chart, answer, and trace. |
| 02 — Self-evaluation | Runs Loop 01's task, then makes a separate model call to review the completed answer and execution evidence. | Answer plus structured retrospective evaluation JSON. |
| 03 — Hooks | Checks requests before tools run and adds deterministic evidence after chart calls. | Pre-tool decision, post-chart antidote values, and an answer grounded in those values. |
| 04 — Permissions | Allows bounded read-only analysis and asks for a one-use grant before each protected plot or inventory ranking. | Allowed decision and separate, exact-request approvals for plots and ranking. |

The [rubric](RUBRIC.md) grades the observed runs and their artifacts. Prompt instructions alone do not prove that a component ran.

## What the starter contains

The starter includes three synthetic datasets, vehicle skill files, a closed EDA tool registry, the working non-production loop, and all five prompt files. Its CLI already selects a loop from the prompt filename, uses one Vocareum OpenAI client, prints each model cycle, and saves per-loop artifacts. Loops 02–04 contain TODOs for the components you will build. Their prompt files select the right classes now, but those loops stop at unfinished component methods until you complete them.

Keep the supplied CSVs and `harness/stage_02_skills/` files intact. Use the registered tools; do not give the model arbitrary Python, shell, network, or file-system access. Generate evidence by running the harness rather than editing output files by hand.

## Set up your environment

Use Python 3.12 and a Conda environment named `harness`. Run commands from the `starter` directory:

```bash
conda create -n harness python=3.12
conda activate harness
cd /path/to/project/starter
pip install -r requirements.txt
```

Skip `conda create` if the environment already exists.

Copy `.env.example` to `.env` in `starter/`, then set your Vocareum API key:

```bash
cp .env.example .env
```

```text
OPENAI_API_KEY=your-vocareum-api-key
OPENAI_MODEL=gpt-4.1-mini
```

`OPENAI_MODEL` is optional and defaults to `gpt-4.1-mini`. The provided runtime loads `.env` and uses `https://openai.vocareum.com/v1`. Keep the key out of source files and submitted evidence.

## How the prompts work

The supplied `prompts/master_prompt.txt` contains Cedar Lane Motors' shared EDA question. In a prompt-file run, this is the **user prompt**. The selected `prompt_01_non_production.txt` through `prompt_04_permissions.txt` file supplies **system instructions** in addition to the shared runtime instructions. Each system file requests work that makes its loop's component observable while keeping the user question the same.

`main.py` maps the four supplied filenames to their Python loop classes. `--prompt-file` selects both the system prompt and the loop; there is no separate `--loop` option. With no arguments, `python main.py` starts the non-production loop interactively and uses your typed request as the user prompt.

| System prompt file | Loop | Work to request |
| --- | --- | --- |
| `prompt_01_non_production.txt` | Non-production | Skill, plan, dataset inspection, statistics, test, and charts. |
| `prompt_02_self_evaluation.txt` | Self-evaluation | Traceable analysis that the separate evaluator can review. |
| `prompt_03_hooks.txt` | Hooks | Charts with an explicit population and claims supported by hook evidence. |
| `prompt_04_permissions.txt` | Permissions | Read-only inspection, protected plots, and an illustrative full-inventory ranking. |

Do not make the system prompt pretend to implement evaluation, hooks, or permissions. The Python loop class must perform those actions.

## Complete the harness

### 1. Run and inspect the foundation

- Run `python main.py` with a free-form question, then run the Loop 01 prompt file. Both use the supplied `HarnessLoop` in `harness/stage_01_loops/loop_01_non_production.py`.
- Inspect `run_model`, `dispatch_tools`, and the plan approval pause. The model can use only registered tools, and planned EDA tools wait for human approval. Tool results become the model's next input.
- Use `--loop-pause` to inspect the raw prompt, raw model output, selected calls, full tool results, and next observation one cycle at a time. The foundation already prints and saves these records.
- Preserve the foundation and its output contract as you add later loops. Prompt-file answers and traces go in `outputs/<loop>/prompt/`; free-form evidence goes in `outputs/non-production/interactive/`.

### 2. Add retrospective self-evaluation

Complete `harness/stage_01_loops/loop_02_self_evaluation.py` and `harness/stage_04_evaluation/retrospective_evaluation.py`. After the primary analysis completes or reaches its iteration limit, make a second model call using the original prompt, execution trace, tool log, task status, and final answer. Do not evaluate a run that is waiting for approval. Keep the review separate from the primary answer.

Validate and save JSON with `task_status`, `efficiency_score`, `critique`, `systemic_failure_root_cause`, and `workflow_adjustments`. The target artifact is `outputs/self-evaluation/prompt/retrospective_evaluation.json`.

### 3. Add hooks and antidotes

Complete `harness/stage_01_loops/loop_03_hooks.py` and `harness/stage_05_antidotes/` through the foundational loop's before- and after-tool extension points. Implement deterministic pre-tool checks for invalid ranking weights, duplicate comparison IDs, and a chart without a declared population. Treat `filters: []` as an explicit full-dataset population. A failed check must block the handler with a reason.

After a chart runs, add deterministic population details and numeric support such as grouped means and counts, or a range and correlation. Return that evidence to the model in its tool observation and record the hook decision and antidote output in `tool_trace.json`. The supplied hooks prompt should use valid chart requests, so the normal run should show `continue` and post-chart evidence; a blocked request is not required for this prompt run.

### 4. Add scoped permissions

Complete `harness/stage_06_permissions/policy.py` and `harness/stage_01_loops/loop_04_permissions.py`. Return an explicit `allow`, `require_approval`, or `deny` decision with a reason. Allow bounded read-only EDA, require approval for `plot_data` and `rank_inventory`, and deny unsupported actions.

Before a protected call executes, pause and display its tool name and exact arguments. Approving one request grants one use of that exact request only; changed arguments require a new decision. Record the decisions and grants in the trace. The supplied prompt should exercise allowed actions and separate approvals for plots and ranking. A denied action is not required in the submitted prompt run.

### 5. Verify and preserve the evidence

Run `pytest` while implementing the provided contracts. Baseline and prompt-routing tests should pass at the start; tests for Loops 02–04 expose unfinished TODOs and should pass after you implement them. Also inspect the live run evidence below. Keep the four answers, four prompt-file traces, retrospective JSON, relevant chart images, and a short comparison that cites what each component did.

## Run and show the loops

Run these commands from `starter/`. The Loop 01 runs are ready after setup. Finish each later loop's TODOs before using its run as rubric evidence.

### Default loop in free form

```bash
python main.py
```

At `vehicle-eda >>`, type your own vehicle EDA request. Ask for a plan and approval so you can see the pause; enter `y` to continue. Show more than one model cycle, a tool result sent back to the model, and the completed answer. Use `quit` to exit. Save or point to `outputs/non-production/interactive/answer.md` and `tool_trace.json`.

### Loop 01: non-production prompt

```bash
python main.py --prompt-file prompts/prompt_01_non_production.txt
```

Approve the plan. Show `outputs/non-production/prompt/answer.md` and `tool_trace.json`. Point to `load_skill`, the plan approval, the EDA tool calls and results, and a chart in `outputs/plots/`. The approval must occur before planned analysis.

### Loop 02: self-evaluation prompt

```bash
python main.py --prompt-file prompts/prompt_02_self_evaluation.txt
```

Approve the plan and let the primary task finish. Show `outputs/self-evaluation/prompt/answer.md`, `tool_trace.json`, and `retrospective_evaluation.json`. Point to the separate review after the answer, with all required JSON fields.

### Loop 03: hooks prompt

```bash
python main.py --prompt-file prompts/prompt_03_hooks.txt
```

Approve the plan. Show `outputs/hooks/prompt/answer.md`, `tool_trace.json`, and the related chart files. In the terminal and trace, identify the pre-tool check and its decision, followed by the post-chart antidote output. Explain which numeric values from that output support the answer's chart claims.

### Loop 04: permissions prompt

```bash
python main.py --prompt-file prompts/prompt_04_permissions.txt
```

Approve the plan. Review each protected tool name and arguments before granting permission. Show `outputs/permissions/prompt/answer.md` and `tool_trace.json`. Identify an allowed read-only call, a separate approval and grant for each protected plot, and a separate approval and grant for `rank_inventory`.

Add `--loop-pause` to any command when you want to stop after each model cycle and press Return to continue. A later run of the same loop and mode replaces its answer and trace, so preserve evidence before rerunning.

## Read a loop cycle

`RAW PROMPT TO MODEL` shows the system instructions and current input sent to the model. On the first cycle, the input is the user question; on later cycles, it contains observations from tools or approvals. `RAW MODEL OUTPUT` includes written text and structured tool calls. `MODEL TEXT` is only the written part, so it can be empty when the model returned tool calls. Under `COMPONENTS EXECUTED`, inspect the tool arguments, status, and full result. The harness sends that result to the model for the next cycle. The loop finishes when the model returns an answer without another tool call.

For Loop 03, look for a pre-tool check followed by a decision to continue, then `HOOK post-tool evidence: plot_data` and `ANTIDOTE plot-evidence: completed`. The numeric `--- HOOK EVIDENCE ---` is returned to the model and saved in the trace. For Loop 04, look for `PERMISSION CHECK` and `PERMISSION GRANTED` for each protected call.

## Submit your evidence

- [ ] The default loop ran interactively from a free-form question and completed more than one cycle.
- [ ] All four prompt-file runs used the shared EDA question in `prompts/master_prompt.txt` and their matching system prompt files.
- [ ] Each prompt-file run has `outputs/<loop>/prompt/answer.md` and `tool_trace.json`.
- [ ] Loop 01 shows skill loading, plan approval, registered EDA tool use, and its answer.
- [ ] Loop 02 has a separate, structured retrospective evaluation JSON artifact.
- [ ] Loop 03 has visible hook decisions and deterministic numeric chart evidence used in its answer.
- [ ] Loop 04 has allowed decisions and separate exact-request plot and ranking approvals.
- [ ] A short comparison names each loop's added control, cites its terminal or artifact evidence, and explains its observed effect.

Optional extensions include an ablation comparison, a failure log, token or cost accounting, a data-quality analysis of `vehicle_sales_reviews.csv`, or a test that changed protected arguments cannot reuse a grant. Run `data_quality_report` before statistical analysis of the sales/review dataset; it contains intentional recording and standardization issues.

## Repository map

```text
starter/
├── data/                         # supplied inventory, history, and sales/review CSVs
├── harness/
│   ├── stage_00_runtime/         # model client, configuration, prompts, state, persistence
│   ├── stage_01_loops/           # four loop variants
│   ├── stage_02_skills/          # supplied vehicle skills
│   ├── stage_03_tools/           # closed tool registry and EDA handlers
│   ├── stage_04_evaluation/      # retrospective evaluator TODOs
│   ├── stage_05_antidotes/       # hook and antidote TODOs
│   └── stage_06_permissions/     # permission policy TODOs
├── prompts/                      # supplied master user prompt and loop system prompts
├── outputs/                      # generated evidence and plots
├── tests/                        # starter contract checks
├── main.py                       # supplied CLI and prompt-file routing
├── requirements.txt
├── RUBRIC.md
└── README.md                     # project instructions
```

## Troubleshooting

- **Missing API key:** Set `OPENAI_API_KEY` in `starter/.env` and check that your runtime loads that file.
- **`--loop` is rejected:** Select one of the four supplied system prompt files with `--prompt-file`; the filename determines the loop.
- **Loop 02, 03, or 04 raises `NotImplementedError`:** Complete that loop's TODOs and rerun it. A selected prompt file does not implement its component.
- **No plan approval prompt:** Check that the request asks for a plan and approval and that the plan gate pauses tool execution.
- **A chart appears to pause the run:** Close the plot window to let the loop continue.
- **No final artifact after rejecting approval:** A rejected plan or protected call ends that request before a completed answer is saved.
