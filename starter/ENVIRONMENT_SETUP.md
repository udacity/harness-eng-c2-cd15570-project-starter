# RouteLine Vehicle EDA Harness: Environment Setup

## What You Receive

```text
starter/
├── data/                              # provided source data; do not modify
│   ├── synthetic_dealer_inventory.csv
│   ├── synthetic_vehicle_history.csv
│   └── vehicle_sales_reviews.csv
├── harness/                           # complete the staged harness components
│   ├── stage_00_runtime/              # runtime configuration and providers
│   ├── stage_01_loops/                # Loop 01 complete; complete stages 02-04
│   ├── stage_02_skills/               # provided progressive-disclosure skills
│   ├── stage_03_tools/                # registered EDA tools and handlers
│   ├── stage_04_evaluation/           # complete retrospective evaluation
│   ├── stage_05_antidotes/            # complete deterministic antidotes
│   └── stage_06_permissions/          # complete the permission policy
├── prompts/                           # Prompt 01 complete; complete prompts 02-04
├── outputs/                           # generated evidence; do not hand-edit
├── main.py                            # run the selected harness loop
├── requirements.txt                   # install dependencies ← do not modify
└── RUN_MAIN.md                        # command reference ← do not modify
```

## What You Submit

1. Completed loop, evaluation, antidote, and permission-policy source files.
2. Four loop-specific prompt files in `prompts/`.
3. Saved outputs, tool traces, retrospective evaluation, and chart artifacts.
4. A short written comparison of the four loop stages and their controls.

## What You Need

Use Python 3.12 with the packages in `requirements.txt`: the language-model
client, tabular analysis, statistical testing, plotting, device-code
authentication, and secret-storage client. Use either the course-managed
hosted-model configuration or an API key for the alternate provider. This
project is designed for a local machine; no hosted workspace is provided.

## Local Machine Instructions

1. Install Python 3.12 and create or activate a virtual environment.

   ```bash
   conda create -n route-line python=3.12
   conda activate route-line
   ```

2. Navigate to the `solution` directory.

   ```bash
   cd /path/to/starter
   ```

3. Install the project dependencies.

   ```bash
   pip install -r requirements.txt
   ```

4. Run the foundational loop with its dedicated prompt.

   ```bash
   python main.py \
     --loop non-production \
     --prompt-file prompts/prompt_01_non_production.txt
   ```

5. Run the self-evaluation loop with its dedicated prompt.

   ```bash
   python main.py \
     --loop self-evaluation \
     --prompt-file prompts/prompt_02_self_evaluation.txt
   ```

6. Run the hooks loop with its dedicated prompt.

   ```bash
   python main.py \
     --loop hooks \
     --prompt-file prompts/prompt_03_hooks.txt
   ```

7. Run the permissions loop with its dedicated prompt. Approve the plan, then
   approve the scoped chart and ranking requests when prompted.

   ```bash
   python main.py \
     --loop permissions \
     --prompt-file prompts/prompt_04_permissions.txt
   ```

## Cloud and External Resource Setup

- **AI Components:** Use the course-managed hosted model or configure the
  alternate provider with an API key.
- **Secrets:** Use the course-managed secret store when using device-code
  authentication. Do not place credentials in source files.

1. Run a command with the default hosted provider.
2. Open the device-code URL printed in the terminal and enter the displayed
   one-time code.
3. Complete browser sign-in, then return to the terminal and approve the
   requested harness actions.
4. For an alternate provider, follow the credential instructions supplied with
   your course environment, then run the matching loop command from
   `RUN_MAIN.md`.
