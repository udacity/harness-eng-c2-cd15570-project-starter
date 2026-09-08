# RouteLine Vehicle EDA Harness

Build a staged agent harness that turns a language-model-driven vehicle EDA
workflow into an observable and controlled analysis system.

## Project Overview

### Hero

## RouteLine Vehicle EDA Harness

Build a vehicle-market analysis harness that progresses from a basic agent loop
to production controls for evaluation, deterministic recovery, and permissions.

Cedar Lane Motors operates in six growing lake-region towns and has asked its
RouteLine Analytics team to standardize how analysts explore inventory,
ownership history, and sales-review data. The team needs useful EDA outputs,
but it also needs to know what the agent did, whether its conclusions are
grounded in evidence, when an automated control changed its trajectory, and
when a buyer-facing action received human consent. A single free-form agent
cannot provide that operational record. RouteLine must deliver a harness whose
behavior can be inspected one stage at a time.

### Overview

You receive three synthetic vehicle datasets: active inventory, model-level
ownership history, and sales/review records with realistic data-quality issues.
The harness gives the model a closed set of EDA tools and a progressive catalog
of vehicle-domain skills. The model can inspect data, calculate summaries,
run a hypothesis test, create a chart, compare vehicles, or rank inventory, but
it cannot execute arbitrary code or access the shell.

The work is organized as four runnable loops. The first loop demonstrates
planning, approval, skills, and tools. The second adds a retrospective model
evaluation using the prompt, trace, tool activity, and final response. The
third adds deterministic hooks and antidotes, including chart evidence that
prevents unsupported chart claims. The fourth adds least-privilege decisions:
read-only analysis is allowed, output-generating plots and rankings need scoped
approval, and unsupported actions are denied.

You will build a staged Vehicle EDA harness with reproducible prompts, saved
traces, evaluation evidence, hook evidence, and permission decisions.

### The Solution

The solution places a runtime layer beneath four loop variants, then separates
skills, tools, evaluation, antidotes, and permissions into clear harness
stages. Each loop delegates model tool calls to registered handlers and returns
the resulting observations to the model. Later stages add controls without
changing the core EDA tools.

### How It Works

1. **Load a request.** The CLI reads an EDA prompt from a file or accepts an
   interactive request, then creates the selected loop variant.
2. **Reveal skills progressively.** The model sees skill metadata and loads a
   full vehicle-domain skill only when it needs that guidance.
3. **Plan and approve analysis.** The model writes an analysis plan and pauses
   when the request requires human approval before EDA execution.
4. **Execute constrained tools.** Registered handlers read the supplied data,
   produce summaries or charts, and return evidence through the loop.
5. **Evaluate completed work.** The self-evaluation loop makes a second model
   call that critiques the finished trajectory and saves structured results.
6. **Apply deterministic controls.** The hooks loop validates selected calls
   and attaches deterministic chart evidence to later model observations.
7. **Authorize consequential actions.** The permissions loop pauses for a
   scoped user decision before a plot or inventory ranking can run.

### Key Technologies

- **Python 3.12:** runs the CLI, loop variants, policies, and tool handlers.
- **Language-model Responses API:** drives tool selection and retrospective
  evaluation.
- **Pandas and SciPy:** provide tabular EDA and Welch two-sample testing.
- **Matplotlib:** produces bounded chart artifacts in `outputs/plots/`.
- **Device-code cloud authentication and secret storage:** obtain the hosted
  model configuration without storing credentials in source files.
