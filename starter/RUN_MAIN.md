# Run the RouteLine Starter

Install dependencies and run the completed foundational loop:

```bash
pip install -r requirements.txt
python main.py \
  --loop non-production \
  --prompt-file prompts/prompt_01_non_production.txt
```

The starter provides Loop 01. Complete Loops 02 through 04 and replace their
prompt TODOs before running them:

```bash
python main.py --loop self-evaluation --prompt-file prompts/prompt_02_self_evaluation.txt
python main.py --loop hooks --prompt-file prompts/prompt_03_hooks.txt
python main.py --loop permissions --prompt-file prompts/prompt_04_permissions.txt
```

Run the checks while building the production stages:

```bash
pytest
```

Save generated answers, tool traces, evaluator JSON, charts, and comparison
reports under `outputs/` and `reports/`.
