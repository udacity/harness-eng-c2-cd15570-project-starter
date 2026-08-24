import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from openai import OpenAI


# ============================================================
# Configuration
# ============================================================

AZURE_OPENAI_ENDPOINT = "https://XXXXXX"
AZURE_OPENAI_API_KEY = "XXXXXXX"
MODEL_DEPLOYMENT = "gpt-5.4"

INVENTORY_FILE = os.environ.get(
    "INVENTORY_FILE",
    "synthetic_dealer_inventory.csv",
)
HISTORY_FILE = os.environ.get(
    "HISTORY_FILE",
    "synthetic_vehicle_history.csv",
)

TODO_FILE = Path(".agent_todo.json")
SKILLS_DIR = Path(__file__).parent / "skills"

LOADED_SKILLS: dict[str, str] = {}

APPROVAL_STATE = {
    "required": False,
    "approved": False,
    "request": None,
}

client = OpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    base_url=f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/v1/",
)


# ============================================================
# Skills: progressive disclosure
# ============================================================

def discover_skills() -> dict[str, str]:
    """
    Read only skill metadata at startup.

    The full SKILL.md body is NOT loaded into the system prompt.
    """
    skills: dict[str, str] = {}

    if not SKILLS_DIR.exists():
        return skills

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_file = skill_dir / "SKILL.md"

        if not skill_dir.is_dir() or not skill_file.exists():
            continue

        name = skill_dir.name
        description = "No description."

        lines = skill_file.read_text(encoding="utf-8").splitlines()

        in_frontmatter = False
        for line in lines:
            stripped = line.strip()

            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue

            if in_frontmatter and stripped.startswith("name:"):
                name = stripped.split(":", 1)[1].strip()

            if in_frontmatter and stripped.startswith("description:"):
                description = stripped.split(":", 1)[1].strip()

        skills[name] = description

    return skills


def run_list_skills(inp: dict[str, Any]) -> str:
    try:
        skills = discover_skills()

        if not skills:
            return "(no skills available)"

        return "\n".join(
            f"- {name}: {description}"
            for name, description in skills.items()
        )
    except Exception as exc:
        return f"ERROR list_skills: {type(exc).__name__}: {exc}"


def run_load_skill(inp: dict[str, Any]) -> str:
    """
    Load full skill instructions only when the model decides they are needed.
    """
    try:
        name = inp["name"]
        registry = discover_skills()

        if name not in registry:
            return (
                f"ERROR load_skill: skill '{name}' not found. "
                f"Available: {', '.join(registry)}"
            )

        skill_path = SKILLS_DIR / name / "SKILL.md"
        skill_content = skill_path.read_text(encoding="utf-8")

        # Persist loaded skill metadata for this CLI session.
        LOADED_SKILLS[name] = registry[name]

        return (
            f"=== SKILL LOADED: {name} ===\n"
            f"{skill_content}"
        )
    except Exception as exc:
        return f"ERROR load_skill: {type(exc).__name__}: {exc}"


def build_system_prompt() -> str:
    registry = discover_skills()

    skill_list = "\n".join(
        f"  - {name}: {description}"
        for name, description in registry.items()
    )

    return f"""
You are a vehicle-market EDA agent.

You help a fictional car dealer identify the exact vehicle that best fits
a buyer using two synthetic datasets:

1. {INVENTORY_FILE}
   Current dealer inventory.

2. {HISTORY_FILE}
   Historical model ownership, reliability, satisfaction, operating-cost,
   and resale data.

You do NOT have arbitrary Python or shell access.
You must perform analysis only through the defined tools.

SKILLS:
The list below contains lightweight descriptions only.
When a task requires specialized vehicle knowledge, call load_skill(name)
to load the full instructions before relying on that expertise.
Do NOT guess specialized vehicle-domain guidance when a relevant skill exists.
Loading a skill is knowledge acquisition, not execution, so it may happen
before the plan is committed.
When you load a skill, explicitly use its terminology, criteria, and decision
guidance when creating the plan.

Available skills:
{skill_list}

PLANNING AND APPROVAL:
- For every multi-step task, ALWAYS call todo_write before EDA execution.
- The plan must describe the complete intended analysis.
- After todo_write, ALWAYS call request_approval.
- Do NOT use EDA execution tools until the user explicitly approves the plan.
- After approval, execute the plan in order.
- Call todo_update when a step starts and when it is completed.
- The current todo plan is re-injected after every tool call.

EDA BEHAVIOR:
- Separate hard buyer constraints from preferences.
- Filter inventory using hard constraints first.
- Use historical data for reliability, satisfaction, repair cost, resale,
  ownership duration, and owner feedback.
- Compare finalists rather than simply selecting the cheapest vehicle.
- Use ranking when several criteria compete.
- Never invent dataset values.
- Finish with an exact stock_id and explain meaningful trade-offs.
""".strip()


# ============================================================
# Dataset helpers
# ============================================================

def _load_dataset(dataset: str) -> pd.DataFrame:
    if dataset == "inventory":
        return pd.read_csv(INVENTORY_FILE)
    if dataset == "history":
        return pd.read_csv(HISTORY_FILE)
    raise ValueError("dataset must be 'inventory' or 'history'")


def _apply_filter(df: pd.DataFrame, rule: dict[str, Any]) -> pd.DataFrame:
    column = rule["column"]
    operator = rule["operator"]
    value = rule["value"]

    if column not in df.columns:
        raise ValueError(f"unknown column '{column}'")

    s = df[column]

    if operator == "eq":
        return df[s == value]
    if operator == "ne":
        return df[s != value]
    if operator == "lt":
        return df[s < value]
    if operator == "lte":
        return df[s <= value]
    if operator == "gt":
        return df[s > value]
    if operator == "gte":
        return df[s >= value]
    if operator == "contains":
        return df[
            s.fillna("").astype(str).str.contains(
                str(value), case=False, regex=False
            )
        ]
    if operator == "in":
        if not isinstance(value, list):
            raise ValueError("'in' requires a list value")
        return df[s.isin(value)]

    raise ValueError(f"unsupported operator '{operator}'")


# ============================================================
# Safe EDA tool handlers
# All handlers: dict in -> string out
# ============================================================

def run_dataset_info(inp: dict[str, Any]) -> str:
    try:
        dataset = inp["dataset"]
        df = _load_dataset(dataset)
        result = {
            "dataset": dataset,
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": {k: str(v) for k, v in df.dtypes.items()},
        }
        return json.dumps(result, indent=2)
    except Exception as exc:
        return f"ERROR dataset_info: {type(exc).__name__}: {exc}"


def run_sample_rows(inp: dict[str, Any]) -> str:
    try:
        df = _load_dataset(inp["dataset"])
        limit = min(max(int(inp.get("limit", 5)), 1), 20)
        return df.head(limit).to_json(orient="records", indent=2)
    except Exception as exc:
        return f"ERROR sample_rows: {type(exc).__name__}: {exc}"


def run_describe_numeric(inp: dict[str, Any]) -> str:
    try:
        df = _load_dataset(inp["dataset"])
        columns = inp.get("columns", [])

        if columns:
            unknown = [c for c in columns if c not in df.columns]
            if unknown:
                return f"ERROR describe_numeric: unknown columns {unknown}"
            df = df[columns]

        numeric = df.select_dtypes(include="number")

        if numeric.empty:
            return "No numeric columns available."

        return numeric.describe().round(2).to_json(indent=2)
    except Exception as exc:
        return f"ERROR describe_numeric: {type(exc).__name__}: {exc}"


def run_value_counts(inp: dict[str, Any]) -> str:
    try:
        df = _load_dataset(inp["dataset"])
        column = inp["column"]
        limit = min(max(int(inp.get("limit", 15)), 1), 50)

        if column not in df.columns:
            return f"ERROR value_counts: unknown column '{column}'"

        return (
            df[column]
            .fillna("<MISSING>")
            .value_counts()
            .head(limit)
            .to_json(indent=2)
        )
    except Exception as exc:
        return f"ERROR value_counts: {type(exc).__name__}: {exc}"


def run_filter_inventory(inp: dict[str, Any]) -> str:
    try:
        df = _load_dataset("inventory")

        for rule in inp.get("filters", []):
            df = _apply_filter(df, rule)

        sort_by = inp.get("sort_by")
        if sort_by:
            if sort_by not in df.columns:
                return f"ERROR filter_inventory: unknown sort column '{sort_by}'"
            df = df.sort_values(
                sort_by,
                ascending=bool(inp.get("ascending", True)),
            )

        columns = inp.get("columns", [])
        if columns:
            unknown = [c for c in columns if c not in df.columns]
            if unknown:
                return f"ERROR filter_inventory: unknown columns {unknown}"
            df = df[columns]

        limit = min(max(int(inp.get("limit", 20)), 1), 50)

        result = {
            "matching_rows": len(df),
            "rows": json.loads(df.head(limit).to_json(orient="records")),
        }
        return json.dumps(result, indent=2)
    except Exception as exc:
        return f"ERROR filter_inventory: {type(exc).__name__}: {exc}"


def run_lookup_vehicle(inp: dict[str, Any]) -> str:
    try:
        stock_id = inp["stock_id"]
        inventory = _load_dataset("inventory")
        history = _load_dataset("history")

        match = inventory[inventory["stock_id"] == stock_id]

        if match.empty:
            return f"No vehicle found with stock_id '{stock_id}'."

        vehicle = match.iloc[0]

        hist = history[
            (history["brand"] == vehicle["brand"])
            & (history["model"] == vehicle["model"])
            & (history["model_year"] == vehicle["year"])
        ]

        result = {
            "inventory": json.loads(match.to_json(orient="records"))[0],
            "history": (
                json.loads(hist.to_json(orient="records"))[0]
                if not hist.empty
                else None
            ),
        }
        return json.dumps(result, indent=2)
    except Exception as exc:
        return f"ERROR lookup_vehicle: {type(exc).__name__}: {exc}"


def run_model_history(inp: dict[str, Any]) -> str:
    try:
        df = _load_dataset("history")
        df = df[
            (df["brand"] == inp["brand"])
            & (df["model"] == inp["model"])
        ]

        if inp.get("start_year") is not None:
            df = df[df["model_year"] >= int(inp["start_year"])]

        if inp.get("end_year") is not None:
            df = df[df["model_year"] <= int(inp["end_year"])]

        return df.sort_values("model_year").to_json(
            orient="records",
            indent=2,
        )
    except Exception as exc:
        return f"ERROR model_history: {type(exc).__name__}: {exc}"


def run_compare_vehicles(inp: dict[str, Any]) -> str:
    try:
        stock_ids = inp["stock_ids"]

        if not stock_ids or len(stock_ids) > 10:
            return "ERROR compare_vehicles: provide 1-10 stock_ids."

        inventory = _load_dataset("inventory")
        history = _load_dataset("history")

        selected = inventory[inventory["stock_id"].isin(stock_ids)]

        merged = selected.merge(
            history,
            left_on=["brand", "model", "year"],
            right_on=["brand", "model", "model_year"],
            how="left",
            suffixes=("_inventory", "_history"),
        )

        useful = [
            "stock_id", "year", "brand", "model", "trim",
            "price_usd", "mileage", "horsepower", "awd",
            "cargo_cuft", "distance_miles", "accident_free",
            "previous_owners", "warranty_months_remaining",
            "reliability_score_10", "owner_satisfaction_10",
            "avg_annual_repair_cost_usd",
            "three_year_value_retention_pct",
            "five_year_value_retention_pct",
            "avg_annual_insurance_usd",
            "avg_annual_fuel_or_energy_usd",
            "most_liked", "most_disliked",
        ]
        useful = [c for c in useful if c in merged.columns]

        return merged[useful].to_json(orient="records", indent=2)
    except Exception as exc:
        return f"ERROR compare_vehicles: {type(exc).__name__}: {exc}"


def run_rank_inventory(inp: dict[str, Any]) -> str:
    try:
        inventory = _load_dataset("inventory")
        history = _load_dataset("history")

        for rule in inp.get("filters", []):
            inventory = _apply_filter(inventory, rule)

        if inventory.empty:
            return "No vehicles remain after constraints."

        df = inventory.merge(
            history,
            left_on=["brand", "model", "year"],
            right_on=["brand", "model", "model_year"],
            how="left",
            suffixes=("_inventory", "_history"),
        )

        higher = {
            "reliability_score_10",
            "owner_satisfaction_10",
            "three_year_value_retention_pct",
            "five_year_value_retention_pct",
            "owners_who_would_buy_again_pct",
            "cargo_cuft",
            "horsepower",
            "warranty_months_remaining",
            "dealer_discount_usd",
            "year",
        }

        lower = {
            "price_usd",
            "mileage",
            "distance_miles",
            "avg_annual_repair_cost_usd",
            "complaints_per_100_vehicles",
            "avg_annual_insurance_usd",
            "avg_annual_fuel_or_energy_usd",
            "previous_owners",
        }

        weights = {
            k: float(v)
            for k, v in inp["weights"].items()
        }

        allowed = higher | lower
        unknown = [k for k in weights if k not in allowed]

        if unknown:
            return f"ERROR rank_inventory: unsupported metrics {unknown}"

        total = sum(weights.values())
        if total <= 0:
            return "ERROR rank_inventory: weights must total > 0."

        weights = {k: v / total for k, v in weights.items()}
        df["score"] = 0.0

        for metric, weight in weights.items():
            s = pd.to_numeric(df[metric], errors="coerce")
            s = s.fillna(s.median())

            if s.max() == s.min():
                normalized = pd.Series(0.5, index=s.index)
            else:
                normalized = (s - s.min()) / (s.max() - s.min())

            if metric in lower:
                normalized = 1 - normalized

            df["score"] += normalized * weight * 100

        df = df.sort_values("score", ascending=False)
        limit = min(max(int(inp.get("limit", 10)), 1), 20)

        cols = [
            "stock_id", "year", "brand", "model", "trim",
            "price_usd", "mileage", "horsepower", "awd",
            "cargo_cuft", "reliability_score_10",
            "owner_satisfaction_10",
            "three_year_value_retention_pct",
            "avg_annual_repair_cost_usd",
            "avg_annual_insurance_usd",
            "avg_annual_fuel_or_energy_usd",
            "score",
        ]
        cols = [c for c in cols if c in df.columns]

        result = df[cols].head(limit).copy()
        result["score"] = result["score"].round(2)

        return json.dumps(
            {
                "vehicles_after_constraints": len(df),
                "normalized_weights": weights,
                "ranking": json.loads(
                    result.to_json(orient="records")
                ),
            },
            indent=2,
        )
    except Exception as exc:
        return f"ERROR rank_inventory: {type(exc).__name__}: {exc}"


# ============================================================
# Todo planning tools
# ============================================================

def run_todo_write(inp: dict[str, Any]) -> str:
    try:
        tasks = inp["tasks"]

        if not isinstance(tasks, list) or not tasks:
            return "ERROR todo_write: tasks must be a non-empty list."

        data = {
            "skills": list(LOADED_SKILLS.keys()),
            "tasks": [
                {
                    "id": i,
                    "task": str(task),
                    "status": "pending",
                }
                for i, task in enumerate(tasks)
            ],
        }

        TODO_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

        # A new plan invalidates any prior approval.
        APPROVAL_STATE["required"] = False
        APPROVAL_STATE["approved"] = False
        APPROVAL_STATE["request"] = None

        skill_text = (
            ", ".join(data["skills"])
            if data["skills"]
            else "(none)"
        )

        task_text = "\n".join(
            f"  [{item['id']}] {item['task']}"
            for item in data["tasks"]
        )

        return (
            f"Plan written.\n"
            f"Skills applied: {skill_text}\n"
            f"{task_text}"
        )

    except Exception as exc:
        return f"ERROR todo_write: {type(exc).__name__}: {exc}"


def run_todo_read(inp: dict[str, Any]) -> str:
    try:
        if not TODO_FILE.exists():
            return "(no plan)"

        data = json.loads(
            TODO_FILE.read_text(encoding="utf-8")
        )

        # Backward-compatible handling if an old todo file is still present.
        if isinstance(data, list):
            skills = "(none)"
            tasks = data
        else:
            skills = ", ".join(data.get("skills", [])) or "(none)"
            tasks = data.get("tasks", [])

        task_text = "\n".join(
            f"  [{item['id']}] [{item['status']:11s}] {item['task']}"
            for item in tasks
        )

        return (
            f"Skills applied: {skills}\n"
            f"{task_text}"
        )

    except Exception as exc:
        return f"ERROR todo_read: {type(exc).__name__}: {exc}"


def run_todo_update(inp: dict[str, Any]) -> str:
    try:
        if not TODO_FILE.exists():
            return "ERROR todo_update: no plan exists."

        data = json.loads(
            TODO_FILE.read_text(encoding="utf-8")
        )

        index = int(inp["index"])
        status = inp["status"]

        if status not in {"pending", "in_progress", "done"}:
            return f"ERROR todo_update: invalid status '{status}'."

        # Backward compatibility for an older list-shaped todo file.
        if isinstance(data, list):
            tasks = data
        else:
            tasks = data.get("tasks", [])

        if not 0 <= index < len(tasks):
            return f"ERROR todo_update: task {index} not found."

        tasks[index]["status"] = status

        if isinstance(data, list):
            output_data = tasks
        else:
            data["tasks"] = tasks
            output_data = data

        TODO_FILE.write_text(
            json.dumps(output_data, indent=2),
            encoding="utf-8",
        )

        return f"Task {index} marked {status}."

    except Exception as exc:
        return f"ERROR todo_update: {type(exc).__name__}: {exc}"


def current_todo_state() -> str:
    return run_todo_read({})


def plan_exists() -> bool:
    return TODO_FILE.exists()


def plan_is_approved() -> bool:
    return plan_exists() and bool(APPROVAL_STATE["approved"])


# ============================================================
# Human approval tool
# ============================================================

def run_request_approval(inp: dict[str, Any]) -> str:
    try:
        message = inp.get(
            "message",
            "Please review and approve the plan before I continue.",
        )

        APPROVAL_STATE["required"] = True
        APPROVAL_STATE["approved"] = False
        APPROVAL_STATE["request"] = message

        return f"APPROVAL_REQUIRED: {message}"
    except Exception as exc:
        return f"ERROR request_approval: {type(exc).__name__}: {exc}"


def clear_approval_state() -> None:
    APPROVAL_STATE["required"] = False
    APPROVAL_STATE["approved"] = False
    APPROVAL_STATE["request"] = None


# ============================================================
# Tool definitions shown to the model
# ============================================================

FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "column": {"type": "string"},
        "operator": {
            "type": "string",
            "enum": ["eq", "ne", "lt", "lte", "gt", "gte", "contains", "in"],
        },
        "value": {},
    },
    "required": ["column", "operator", "value"],
    "additionalProperties": False,
}

TOOLS = [
    {
        "type": "function",
        "name": "list_skills",
        "description": (
            "List available specialized vehicle-domain skills and their short "
            "descriptions. Use when unsure which skill is relevant."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "load_skill",
        "description": (
            "Load the complete instructions for one specialized vehicle skill. "
            "Use this when domain expertise is relevant; do not guess."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "todo_write",
        "description": (
            "Commit the complete plan for a multi-step task. "
            "This must happen before EDA execution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                }
            },
            "required": ["tasks"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "todo_read",
        "description": "Read the current committed plan and task statuses.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "todo_update",
        "description": (
            "Update one planned step. Mark it in_progress before work "
            "and done after completion."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "minimum": 0},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done"],
                },
            },
            "required": ["index", "status"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "request_approval",
        "description": (
            "Pause and ask the human to approve the committed plan. "
            "Call immediately after todo_write and before EDA execution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "dataset_info",
        "description": "Inspect dataset columns, data types, and row count.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["inventory", "history"],
                }
            },
            "required": ["dataset"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "sample_rows",
        "description": "Read a small sample of rows to understand actual records.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["inventory", "history"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["dataset"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "describe_numeric",
        "description": "Calculate descriptive statistics for numeric fields.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["inventory", "history"],
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["dataset"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "value_counts",
        "description": "Count common values in a categorical column.",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "enum": ["inventory", "history"],
                },
                "column": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["dataset", "column"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "filter_inventory",
        "description": (
            "Apply hard buyer constraints to current inventory. "
            "Use this before ranking preferences."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "array",
                    "items": FILTER_SCHEMA,
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "sort_by": {"type": "string"},
                "ascending": {"type": "boolean"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["filters"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "lookup_vehicle",
        "description": (
            "Inspect one exact stock_id and its matching model-year history."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stock_id": {"type": "string"},
            },
            "required": ["stock_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "model_history",
        "description": (
            "Inspect reliability, satisfaction, repair, resale, and owner "
            "history for one brand/model across years."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "brand": {"type": "string"},
                "model": {"type": "string"},
                "start_year": {"type": "integer"},
                "end_year": {"type": "integer"},
            },
            "required": ["brand", "model"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "compare_vehicles",
        "description": (
            "Compare 1-10 exact stock_ids using inventory and historical evidence."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stock_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 10,
                }
            },
            "required": ["stock_ids"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "rank_inventory",
        "description": (
            "Apply hard filters and transparently rank remaining vehicles using "
            "explicit weighted criteria. Supported higher-is-better metrics: "
            "year, reliability_score_10, owner_satisfaction_10, "
            "three_year_value_retention_pct, five_year_value_retention_pct, "
            "owners_who_would_buy_again_pct, cargo_cuft, horsepower, "
            "warranty_months_remaining, dealer_discount_usd. "
            "Supported lower-is-better metrics: price_usd, mileage, "
            "previous_owners, distance_miles, avg_annual_repair_cost_usd, "
            "complaints_per_100_vehicles, avg_annual_insurance_usd, "
            "avg_annual_fuel_or_energy_usd."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "array",
                    "items": FILTER_SCHEMA,
                },
                "weights": {
                    "type": "object",
                    "additionalProperties": {"type": "number"},
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["weights"],
            "additionalProperties": False,
        },
    },
]


# ============================================================
# Dispatch map
# The loop knows only: handler = dispatch[tool_name]
# ============================================================

DISPATCH: dict[str, Callable[[dict[str, Any]], str]] = {
    "list_skills":       run_list_skills,
    "load_skill":        run_load_skill,
    "todo_write":        run_todo_write,
    "todo_read":         run_todo_read,
    "todo_update":       run_todo_update,
    "request_approval":  run_request_approval,
    "dataset_info":      run_dataset_info,
    "sample_rows":       run_sample_rows,
    "describe_numeric":  run_describe_numeric,
    "value_counts":      run_value_counts,
    "filter_inventory":  run_filter_inventory,
    "lookup_vehicle":    run_lookup_vehicle,
    "model_history":     run_model_history,
    "compare_vehicles":  run_compare_vehicles,
    "rank_inventory":    run_rank_inventory,
}

KNOWLEDGE_TOOLS = {
    "list_skills",
    "load_skill",
}

PLANNING_TOOLS = {
    "todo_write",
    "todo_read",
    "todo_update",
    "request_approval",
}

EDA_EXECUTION_TOOLS = {
    "dataset_info",
    "sample_rows",
    "describe_numeric",
    "value_counts",
    "filter_inventory",
    "lookup_vehicle",
    "model_history",
    "compare_vehicles",
    "rank_inventory",
}


# ============================================================
# Generic dispatcher
# ============================================================

def dispatch_tools(
    response,
    dispatch: dict[str, Callable[[dict[str, Any]], str]],
    verbose: bool = False,
) -> list[dict[str, Any]]:

    results = []

    for item in response.output:
        if item.type != "function_call":
            continue

        tool_name = item.name

        print(f'\n  [DISPATCH] Received: "{tool_name}"')
        print(f'  [DISPATCH] Lookup: dispatch["{tool_name}"]')

        try:
            tool_input = json.loads(item.arguments)
        except json.JSONDecodeError as exc:
            tool_input = {}
            output = f"ERROR invalid tool arguments: {exc}"
        else:
            handler = dispatch.get(tool_name)

            if handler is None:
                output = f"ERROR unknown tool '{tool_name}'"
            else:
                print(f"  [DISPATCH] Resolved: {handler.__name__}()")

                if tool_name in EDA_EXECUTION_TOOLS and not plan_exists():
                    output = (
                        f"BLOCKED: '{tool_name}' cannot run because "
                        "no committed plan exists. Call todo_write first."
                    )
                    print("  [GATE] Blocked: no committed plan")

                elif tool_name in EDA_EXECUTION_TOOLS and not plan_is_approved():
                    output = (
                        f"BLOCKED: '{tool_name}' requires an approved plan "
                        "before execution can continue."
                    )
                    print("  [GATE] Blocked: plan not approved")

                else:
                    print("  [DISPATCH] Executing handler...")
                    output = handler(tool_input)
                    print("  [DISPATCH] Handler completed")

        input_preview = json.dumps(tool_input, default=str)
        if len(input_preview) > 180:
            input_preview = input_preview[:177] + "..."

        output_preview = str(output).replace("\n", " ")
        if len(output_preview) > 240:
            output_preview = output_preview[:237] + "..."

        print(f"  Input:  {input_preview}")
        print(f"  Result: {output_preview}")

        if tool_name == "load_skill":
            active = ", ".join(LOADED_SKILLS.keys()) or "(none)"
            print(f"  [SKILL] Active skills: {active}")

        if verbose:
            print("\n  [FULL TOOL RESULT]")
            print(output)

        todo_state = current_todo_state()
        active_skills = ", ".join(LOADED_SKILLS.keys()) or "(none)"

        observation = (
            f"{output}\n\n"
            f"--- ACTIVE SKILLS ---\n"
            f"{active_skills}\n\n"
            f"--- CURRENT TODO PLAN ---\n"
            f"{todo_state}"
        )

        results.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": observation,
            }
        )

        print("  [DISPATCH] Result packaged for next model loop")

    return results


# ============================================================
# Agent loop
# ============================================================

def run_model(
    request_input,
    previous_response_id: str | None,
):
    return client.responses.create(
        model=MODEL_DEPLOYMENT,
        instructions=build_system_prompt(),
        input=request_input,
        tools=TOOLS,
        previous_response_id=previous_response_id,
    )


def agent_loop(
    user_query: str,
    previous_response_id: str | None = None,
    verbose: bool = False,
):
    loop_number = 1
    request_input = user_query
    response = None

    while True:
        print(f"\n========== LOOP {loop_number} ==========")

        if loop_number == 1:
            print(f"Task: {str(request_input)[:180]}")
        else:
            print("Observation returned to model.")

        response = run_model(
            request_input=request_input,
            previous_response_id=previous_response_id,
        )

        if verbose:
            print("\n----- RAW MODEL RESPONSE -----")
            print(response.model_dump_json(indent=2))
            print("----- END RAW MODEL RESPONSE -----")

        tool_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            print("Decision: no more tools needed.")
            return {
                "status": "complete",
                "response": response,
                "loop_number": loop_number,
            }

        names = [item.name for item in tool_calls]
        print(
            f"Decision: tool needed "
            f"({len(names)} call{'s' if len(names) != 1 else ''})."
        )
        print(f"Selected: {', '.join(names)}")

        tool_results = dispatch_tools(
            response=response,
            dispatch=DISPATCH,
            verbose=verbose,
        )

        requested_approval = "request_approval" in names

        if requested_approval and APPROVAL_STATE["required"]:
            print("\n[GATE] Human approval required. Agent paused.")
            return {
                "status": "approval_required",
                "response": response,
                "tool_results": tool_results,
                "loop_number": loop_number,
            }

        request_input = tool_results
        previous_response_id = response.id
        loop_number += 1


def resume_after_approval(
    approval_response,
    tool_results,
    starting_loop: int,
    verbose: bool,
):
    loop_number = starting_loop

    # The approval tool result is followed by an explicit user message.
    request_input = tool_results + [
        {
            "type": "message",
            "role": "user",
            "content": (
                "The user explicitly approved the committed plan. "
                "Continue executing it."
            ),
        }
    ]

    previous_response_id = approval_response.id

    while True:
        print(f"\n========== LOOP {loop_number} ==========")
        print("Approved plan returned to model.")

        response = run_model(
            request_input=request_input,
            previous_response_id=previous_response_id,
        )

        if verbose:
            print("\n----- RAW MODEL RESPONSE -----")
            print(response.model_dump_json(indent=2))
            print("----- END RAW MODEL RESPONSE -----")

        tool_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            print("Decision: no more tools needed.")
            return response

        names = [item.name for item in tool_calls]
        print(f"Decision: tool needed ({len(names)} call(s)).")
        print(f"Selected: {', '.join(names)}")

        tool_results = dispatch_tools(
            response=response,
            dispatch=DISPATCH,
            verbose=verbose,
        )

        request_input = tool_results
        previous_response_id = response.id
        loop_number += 1


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Safe vehicle EDA agent with planning, approval, and skills."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show full tool results and raw API responses.",
    )
    args = parser.parse_args()

    if TODO_FILE.exists():
        TODO_FILE.unlink()

    LOADED_SKILLS.clear()
    clear_approval_state()

    print("\nVehicle EDA Agent — Skills Version")
    print("==================================")
    print(f"Defined tools: {len(TOOLS)}")
    print(f"Discovered skills: {len(discover_skills())}")
    print(f"Trace mode: {'VERBOSE' if args.verbose else 'COMPACT'}")

    print("\nAvailable skills (metadata only):")
    for name, description in discover_skills().items():
        print(f"  {name:<22} {description}")

    print("\nRegistered dispatch:")
    for name, handler in DISPATCH.items():
        print(f"  {name:<22} -> {handler.__name__}()")

    previous_response_id = None

    while True:
        try:
            query = input("\n\033[36mvehicle-eda >> \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if query.lower() in {"", "q", "quit", "exit"}:
            break

        result = agent_loop(
            user_query=query,
            previous_response_id=previous_response_id,
            verbose=args.verbose,
        )

        if result["status"] == "approval_required":
            print("\n========== PLAN APPROVAL ==========")
            active = ", ".join(LOADED_SKILLS.keys()) or "(none)"
            print(f"Active skills: {active}")
            print(current_todo_state())

            message = (
                APPROVAL_STATE["request"]
                or "Approve this plan?"
            )
            print(f"\n{message}")

            answer = input(
                "\033[36mApprove plan? [y/N]: \033[0m"
            ).strip().lower()

            if answer in {"y", "yes", "approve", "approved"}:
                APPROVAL_STATE["approved"] = True
                APPROVAL_STATE["required"] = False

                print("\n[GATE] Approved. Resuming execution.")

                response = resume_after_approval(
                    approval_response=result["response"],
                    tool_results=result["tool_results"],
                    starting_loop=result["loop_number"] + 1,
                    verbose=args.verbose,
                )

                previous_response_id = response.id

                print("\n========== FINAL ANSWER ==========")
                print(response.output_text)
            else:
                print("\n[GATE] Plan rejected. Execution stopped.")
                clear_approval_state()
                previous_response_id = None

        else:
            response = result["response"]
            previous_response_id = response.id

            print("\n========== FINAL ANSWER ==========")
            print(response.output_text)


if __name__ == "__main__":
    main()
