"""Safe, deterministic handlers exposed to the Vehicle EDA model."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable

import pandas as pd

from harness.stage_00_runtime.config import AppConfig
from harness.stage_00_runtime.state import RuntimeState
from harness.stage_02_skills import SkillCatalog


class ToolHandlers:
    def __init__(self, config: AppConfig, state: RuntimeState, skills: SkillCatalog):
        self.config = config
        self.state = state
        self.skills = skills

    @property
    def dispatch(self) -> dict[str, Callable[[dict[str, Any]], str]]:
        return {
            "list_skills": self.list_skills,
            "load_skill": self.load_skill,
            "write_plan": self.write_plan,
            "request_approval": self.request_approval,
            "dataset_info": self.dataset_info,
            "sample_rows": self.sample_rows,
            "describe_numeric": self.describe_numeric,
            "data_quality_report": self.data_quality_report,
            "hypothesis_test": self.hypothesis_test,
            "value_counts": self.value_counts,
            "plot_data": self.plot_data,
            "filter_inventory": self.filter_inventory,
            "lookup_vehicle": self.lookup_vehicle,
            "model_history": self.model_history,
            "compare_vehicles": self.compare_vehicles,
            "rank_inventory": self.rank_inventory,
        }

    def _load_dataset(self, dataset: str) -> pd.DataFrame:
        if dataset == "inventory":
            return pd.read_csv(self.config.inventory_file)
        if dataset == "history":
            return pd.read_csv(self.config.history_file)
        if dataset == "sales_reviews":
            return pd.read_csv(self.config.sales_reviews_file)
        raise ValueError("dataset must be 'inventory', 'history', or 'sales_reviews'")

    @staticmethod
    def _apply_filter(df: pd.DataFrame, rule: dict[str, Any]) -> pd.DataFrame:
        column, operator, value = rule["column"], rule["operator"], rule["value"]
        if column not in df.columns:
            raise ValueError(f"unknown column '{column}'")
        series = df[column]
        operations = {
            "eq": lambda: df[series == value],
            "ne": lambda: df[series != value],
            "lt": lambda: df[series < value],
            "lte": lambda: df[series <= value],
            "gt": lambda: df[series > value],
            "gte": lambda: df[series >= value],
            "contains": lambda: df[series.fillna("").astype(str).str.contains(str(value), case=False, regex=False)],
        }
        if operator == "in":
            if not isinstance(value, list):
                raise ValueError("'in' requires a list value")
            return df[series.isin(value)]
        if operator not in operations:
            raise ValueError(f"unsupported operator '{operator}'")
        return operations[operator]()

    def list_skills(self, _: dict[str, Any]) -> str:
        try:
            skills = self.skills.discover()
            return "\n".join(f"- {name}: {description}" for name, description in skills.items()) or "(no skills available)"
        except Exception as exc:
            return f"ERROR list_skills: {type(exc).__name__}: {exc}"

    def load_skill(self, inp: dict[str, Any]) -> str:
        try:
            name = inp["name"]
            loaded = self.skills.load(name)
            if loaded is None:
                available = ", ".join(self.skills.discover())
                return f"ERROR load_skill: skill '{name}' not found. Available: {available}"
            description, content = loaded
            self.state.loaded_skills[name] = description
            return f"=== SKILL LOADED: {name} ===\n{content}"
        except Exception as exc:
            return f"ERROR load_skill: {type(exc).__name__}: {exc}"

    def write_plan(self, inp: dict[str, Any]) -> str:
        try:
            tasks = inp["tasks"]
            if not isinstance(tasks, list) or not tasks:
                return "ERROR write_plan: tasks must be a non-empty list."
            self.state.plan = [
                {"id": index + 1, "task": str(task)}
                for index, task in enumerate(tasks)
            ]
            self.state.approval_required = False
            self.state.approval_message = None
            task_text = "\n".join(
                f"{item['id']}. {item['task']}" for item in self.state.plan
            )
            return f"Plan created:\n{task_text}"
        except Exception as exc:
            return f"ERROR write_plan: {type(exc).__name__}: {exc}"

    def request_approval(self, inp: dict[str, Any]) -> str:
        try:
            if not self.state.plan:
                return "ERROR request_approval: write_plan must be called first."
            self.state.approval_required = True
            self.state.approval_message = inp.get(
                "message", "Please approve the plan before analysis continues."
            )
            return f"APPROVAL_REQUIRED: {self.state.approval_message}"
        except Exception as exc:
            return f"ERROR request_approval: {type(exc).__name__}: {exc}"

    def dataset_info(self, inp: dict[str, Any]) -> str:
        try:
            dataset = inp["dataset"]
            df = self._load_dataset(dataset)
            return json.dumps({"dataset": dataset, "rows": len(df), "columns": list(df.columns), "dtypes": {key: str(value) for key, value in df.dtypes.items()}}, indent=2)
        except Exception as exc:
            return f"ERROR dataset_info: {type(exc).__name__}: {exc}"

    def sample_rows(self, inp: dict[str, Any]) -> str:
        try:
            limit = min(max(int(inp.get("limit", 5)), 1), 20)
            return self._load_dataset(inp["dataset"]).head(limit).to_json(orient="records", indent=2)
        except Exception as exc:
            return f"ERROR sample_rows: {type(exc).__name__}: {exc}"

    def describe_numeric(self, inp: dict[str, Any]) -> str:
        try:
            df = self._load_dataset(inp["dataset"])
            columns = inp.get("columns", [])
            unknown = [column for column in columns if column not in df.columns]
            if unknown:
                return f"ERROR describe_numeric: unknown columns {unknown}"
            numeric = (df[columns] if columns else df).select_dtypes(include="number")
            return "No numeric columns available." if numeric.empty else numeric.describe().round(2).to_json(indent=2)
        except Exception as exc:
            return f"ERROR describe_numeric: {type(exc).__name__}: {exc}"

    def data_quality_report(self, inp: dict[str, Any]) -> str:
        """Report structural data-quality issues without changing source records."""
        try:
            df = self._load_dataset(inp["dataset"])
            missing = {
                column: int(count)
                for column, count in df.isna().sum().items()
                if count
            }
            identifier_columns = [column for column in df.columns if column.endswith("_id")]
            duplicate_identifiers = {
                column: int(df[column].notna().sum() - df[column].nunique(dropna=True))
                for column in identifier_columns
                if df[column].notna().sum() != df[column].nunique(dropna=True)
            }

            numeric_hints = (
                "year", "price", "mileage", "mpg", "range", "horsepower",
                "seats", "cargo", "distance", "owners", "months", "days",
                "rating", "discount", "cost",
            )
            numeric_issues = {}
            for column in df.columns:
                if not any(hint in column.lower() for hint in numeric_hints):
                    continue
                raw = df[column]
                numeric = pd.to_numeric(raw, errors="coerce")
                non_numeric = raw.notna() & numeric.isna()
                negative = numeric < 0
                if non_numeric.any() or negative.any():
                    numeric_issues[column] = {
                        "non_numeric_count": int(non_numeric.sum()),
                        "non_numeric_examples": raw[non_numeric].astype(str).head(3).tolist(),
                        "negative_count": int(negative.sum()),
                    }

            boolean_issues = {}
            allowed_booleans = {"true", "false", "yes", "no", "y", "n", "1", "0"}
            for column in ("awd", "accident_free", "would_buy_again"):
                if column not in df.columns:
                    continue
                normalized = df[column].dropna().astype(str).str.strip().str.casefold()
                unexpected = sorted(set(normalized) - allowed_booleans)
                if unexpected:
                    boolean_issues[column] = unexpected[:10]

            category_variants = {}
            for column in df.select_dtypes(include="object"):
                values = df[column].dropna().astype(str).str.strip()
                if values.empty or values.nunique() > 30:
                    continue
                if values.nunique() > values.str.casefold().nunique():
                    category_variants[column] = sorted(values.unique().tolist())[:15]

            actions = []
            if duplicate_identifiers or int(df.duplicated().sum()):
                actions.append("Deduplicate identifiers or complete duplicate rows before aggregation.")
            if missing:
                actions.append("Decide whether missing fields require exclusion, correction, or documented imputation.")
            if numeric_issues or boolean_issues or category_variants:
                actions.append("Standardize types and categorical values before calculating statistics or rankings.")

            return json.dumps({
                "dataset": inp["dataset"],
                "rows": len(df),
                "duplicate_rows": int(df.duplicated().sum()),
                "duplicate_identifiers": duplicate_identifiers,
                "missing_values": missing,
                "numeric_issues": numeric_issues,
                "boolean_issues": boolean_issues,
                "category_variants": category_variants,
                "recommended_actions": actions or ["No structural issues were detected by this report."],
            }, indent=2)
        except Exception as exc:
            return f"ERROR data_quality_report: {type(exc).__name__}: {exc}"

    def hypothesis_test(self, inp: dict[str, Any]) -> str:
        try:
            from scipy.stats import ttest_ind

            dataset, value_column, group_column = inp["dataset"], inp["value_column"], inp["group_column"]
            group_a, group_b = inp["group_a"], inp["group_b"]
            alternative, alpha = inp.get("alternative", "two-sided"), float(inp.get("alpha", 0.05))
            df = self._load_dataset(dataset)
            if value_column not in df.columns or group_column not in df.columns:
                missing = value_column if value_column not in df.columns else group_column
                return f"ERROR hypothesis_test: unknown column '{missing}'"
            if group_a == group_b:
                return "ERROR hypothesis_test: group_a and group_b must be different."
            if alternative not in {"two-sided", "less", "greater"} or not 0 < alpha < 1:
                return "ERROR hypothesis_test: invalid alternative or alpha."
            values = pd.to_numeric(df[value_column], errors="coerce")
            values_a, values_b = values[df[group_column] == group_a].dropna(), values[df[group_column] == group_b].dropna()
            if len(values_a) < 2 or len(values_b) < 2:
                return "ERROR hypothesis_test: each group needs at least two numeric observations."
            result = ttest_ind(values_a, values_b, equal_var=False, alternative=alternative)
            p_value = float(result.pvalue)
            return json.dumps({
                "test": "Welch's two-sample t-test", "dataset": dataset,
                "value_column": value_column, "group_column": group_column,
                "alternative": alternative, "alpha": alpha,
                "group_a": {"value": group_a, "n": len(values_a), "mean": round(float(values_a.mean()), 4)},
                "group_b": {"value": group_b, "n": len(values_b), "mean": round(float(values_b.mean()), 4)},
                "t_statistic": round(float(result.statistic), 4), "p_value": p_value,
                "p_value_display": "<0.000001" if p_value < 0.000001 else f"{p_value:.6f}",
                "reject_null": p_value < alpha,
                "conclusion": "Reject the null hypothesis of equal group means." if p_value < alpha else "Do not reject the null hypothesis of equal group means.",
                "caveat": "This tests association between groups, not causation.",
            }, indent=2)
        except Exception as exc:
            return f"ERROR hypothesis_test: {type(exc).__name__}: {exc}"

    def value_counts(self, inp: dict[str, Any]) -> str:
        try:
            df, column = self._load_dataset(inp["dataset"]), inp["column"]
            if column not in df.columns:
                return f"ERROR value_counts: unknown column '{column}'"
            limit = min(max(int(inp.get("limit", 15)), 1), 50)
            return df[column].fillna("<MISSING>").value_counts().head(limit).to_json(indent=2)
        except Exception as exc:
            return f"ERROR value_counts: {type(exc).__name__}: {exc}"

    def plot_data(self, inp: dict[str, Any]) -> str:
        """Create a filtered chart without allowing arbitrary plotting code."""
        try:
            self.config.plot_dir.mkdir(exist_ok=True)
            cache_dir = self.config.plot_dir / ".cache"
            cache_dir.mkdir(exist_ok=True)
            os.environ.setdefault("MPLCONFIGDIR", str(cache_dir / "matplotlib"))
            os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir))
            import matplotlib

            show = bool(inp.get("show", True))
            if not show:
                matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            dataset, x, y, kind = inp["dataset"], inp["x"], inp.get("y"), inp.get("kind", "bar")
            limit = min(max(int(inp.get("limit", 15)), 1), 50)
            df = self._load_dataset(dataset)
            for rule in inp.get("filters", []):
                df = self._apply_filter(df, rule)
            if df.empty:
                return "ERROR plot_data: no rows remain after filters."
            if x not in df.columns or (y is not None and y not in df.columns):
                return f"ERROR plot_data: unknown column '{x if x not in df.columns else y}'"
            if kind not in {"bar", "scatter", "line", "hist"} or (kind in {"scatter", "line"} and y is None):
                return "ERROR plot_data: invalid chart kind or missing y column."

            figure, axis = plt.subplots(figsize=(10, 6))
            if kind == "hist":
                values = pd.to_numeric(df[x], errors="coerce").dropna()
                if values.empty:
                    return f"ERROR plot_data: '{x}' must be numeric for a histogram."
                axis.hist(values, bins=min(limit, 30), color="#216869", edgecolor="white")
                axis.set_ylabel("Vehicle count")
            elif kind == "bar" and y is None:
                df[x].fillna("<MISSING>").value_counts().head(limit).plot(kind="bar", ax=axis, color="#216869")
                axis.set_ylabel("Vehicle count")
            elif kind == "bar":
                grouped = df.assign(_plot_value=pd.to_numeric(df[y], errors="coerce")).dropna(subset=["_plot_value"]).groupby(x, dropna=False)["_plot_value"].mean().sort_values(ascending=False).head(limit)
                if grouped.empty:
                    return f"ERROR plot_data: '{y}' must be numeric for a bar chart."
                grouped.plot(kind="bar", ax=axis, color="#216869")
                axis.set_ylabel(f"Average {y}")
            else:
                chart_data = pd.DataFrame({"x": pd.to_numeric(df[x], errors="coerce"), "y": pd.to_numeric(df[y], errors="coerce")}).dropna().sort_values("x")
                if chart_data.empty:
                    return f"ERROR plot_data: '{x}' and '{y}' must be numeric for a {kind} chart."
                if kind == "scatter":
                    axis.scatter(chart_data["x"], chart_data["y"], alpha=0.7, color="#216869")
                else:
                    axis.plot(chart_data["x"], chart_data["y"], marker="o", color="#216869")
                axis.set_ylabel(y)
            axis.set_xlabel(x)
            axis.set_title(inp.get("title") or f"{kind.title()} chart: {x}" + (f" by {y}" if y else ""))
            figure.tight_layout()
            output_path = self.config.plot_dir / f"vehicle_plot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
            figure.savefig(output_path, dpi=150)
            backend, displayed = matplotlib.get_backend(), False
            if show and backend.lower() != "agg":
                # Keep the harness paused until the user closes the chart window.
                plt.show(block=True)
                plt.close(figure)
                displayed = True
            else:
                plt.close(figure)
            return json.dumps({"dataset": dataset, "kind": kind, "x": x, "y": y, "output_path": str(output_path), "displayed": displayed, "display_message": f"Displayed using the {backend} backend." if displayed else "PNG saved, but no interactive Matplotlib backend is available in this environment."}, indent=2)
        except Exception as exc:
            return f"ERROR plot_data: {type(exc).__name__}: {exc}"

    def plot_evidence(self, inp: dict[str, Any]) -> str:
        """Return the numeric evidence underlying one constrained chart."""
        try:
            dataset, x = inp["dataset"], inp["x"]
            y, kind = inp.get("y"), inp.get("kind", "bar")
            limit = min(max(int(inp.get("limit", 15)), 1), 50)
            df = self._load_dataset(dataset)
            for rule in inp.get("filters", []):
                df = self._apply_filter(df, rule)
            if df.empty:
                return "ERROR plot_evidence: no rows remain after filters."

            population = {
                "dataset": dataset,
                "rows": len(df),
                "filters": inp.get("filters", []),
                "population": "full dataset" if not inp.get("filters") else "filtered dataset",
            }
            if kind == "bar" and y is not None:
                values = pd.to_numeric(df[y], errors="coerce")
                grouped = (
                    df.assign(_plot_value=values)
                    .dropna(subset=["_plot_value"])
                    .groupby(x, dropna=False)["_plot_value"]
                    .agg(["mean", "count"])
                    .sort_values("mean", ascending=False)
                    .head(limit)
                    .round(2)
                )
                if grouped.empty:
                    return f"ERROR plot_evidence: '{y}' has no numeric values."
                return json.dumps({
                    **population,
                    "kind": kind,
                    "x": x,
                    "y": y,
                    "grouped_means": grouped.reset_index().to_dict(orient="records"),
                }, indent=2)

            if kind in {"scatter", "line"} and y is not None:
                points = pd.DataFrame({
                    "x": pd.to_numeric(df[x], errors="coerce"),
                    "y": pd.to_numeric(df[y], errors="coerce"),
                }).dropna()
                if points.empty:
                    return f"ERROR plot_evidence: '{x}' and '{y}' have no numeric pairs."
                return json.dumps({
                    **population,
                    "kind": kind,
                    "x": x,
                    "y": y,
                    "point_count": len(points),
                    "x_range": [round(float(points.x.min()), 2), round(float(points.x.max()), 2)],
                    "y_range": [round(float(points.y.min()), 2), round(float(points.y.max()), 2)],
                    "pearson_correlation": round(float(points.x.corr(points.y)), 4),
                }, indent=2)

            return json.dumps({
                **population,
                "kind": kind,
                "x": x,
                "y": y,
                "message": "The chart was created, but this antidote has no additional numeric summary for this chart type.",
            }, indent=2)
        except Exception as exc:
            return f"ERROR plot_evidence: {type(exc).__name__}: {exc}"

    def filter_inventory(self, inp: dict[str, Any]) -> str:
        try:
            df = self._load_dataset("inventory")
            for rule in inp.get("filters", []):
                df = self._apply_filter(df, rule)
            sort_by = inp.get("sort_by")
            if sort_by:
                if sort_by not in df.columns:
                    return f"ERROR filter_inventory: unknown sort column '{sort_by}'"
                df = df.sort_values(sort_by, ascending=bool(inp.get("ascending", True)))
            columns = inp.get("columns", [])
            unknown = [column for column in columns if column not in df.columns]
            if unknown:
                return f"ERROR filter_inventory: unknown columns {unknown}"
            if columns:
                df = df[columns]
            limit = min(max(int(inp.get("limit", 20)), 1), 50)
            return json.dumps({"matching_rows": len(df), "rows": json.loads(df.head(limit).to_json(orient="records"))}, indent=2)
        except Exception as exc:
            return f"ERROR filter_inventory: {type(exc).__name__}: {exc}"

    def lookup_vehicle(self, inp: dict[str, Any]) -> str:
        try:
            stock_id = inp["stock_id"]
            inventory, history = self._load_dataset("inventory"), self._load_dataset("history")
            match = inventory[inventory["stock_id"] == stock_id]
            if match.empty:
                return f"No vehicle found with stock_id '{stock_id}'."
            vehicle = match.iloc[0]
            history_match = history[(history["brand"] == vehicle["brand"]) & (history["model"] == vehicle["model"]) & (history["model_year"] == vehicle["year"])]
            return json.dumps({"inventory": json.loads(match.to_json(orient="records"))[0], "history": json.loads(history_match.to_json(orient="records"))[0] if not history_match.empty else None}, indent=2)
        except Exception as exc:
            return f"ERROR lookup_vehicle: {type(exc).__name__}: {exc}"

    def model_history(self, inp: dict[str, Any]) -> str:
        try:
            df = self._load_dataset("history")
            df = df[(df["brand"] == inp["brand"]) & (df["model"] == inp["model"])]
            if inp.get("start_year") is not None:
                df = df[df["model_year"] >= int(inp["start_year"])]
            if inp.get("end_year") is not None:
                df = df[df["model_year"] <= int(inp["end_year"])]
            return df.sort_values("model_year").to_json(orient="records", indent=2)
        except Exception as exc:
            return f"ERROR model_history: {type(exc).__name__}: {exc}"

    def compare_vehicles(self, inp: dict[str, Any]) -> str:
        try:
            stock_ids = inp["stock_ids"]
            if not stock_ids or len(stock_ids) > 10:
                return "ERROR compare_vehicles: provide 1-10 stock_ids."
            inventory, history = self._load_dataset("inventory"), self._load_dataset("history")
            merged = inventory[inventory["stock_id"].isin(stock_ids)].merge(history, left_on=["brand", "model", "year"], right_on=["brand", "model", "model_year"], how="left", suffixes=("_inventory", "_history"))
            useful = ["stock_id", "year", "brand", "model", "trim", "price_usd", "mileage", "horsepower", "awd", "cargo_cuft", "distance_miles", "accident_free", "previous_owners", "warranty_months_remaining", "reliability_score_10", "owner_satisfaction_10", "avg_annual_repair_cost_usd", "three_year_value_retention_pct", "five_year_value_retention_pct", "avg_annual_insurance_usd", "avg_annual_fuel_or_energy_usd", "most_liked", "most_disliked"]
            return merged[[column for column in useful if column in merged.columns]].to_json(orient="records", indent=2)
        except Exception as exc:
            return f"ERROR compare_vehicles: {type(exc).__name__}: {exc}"

    def rank_inventory(self, inp: dict[str, Any]) -> str:
        try:
            inventory, history = self._load_dataset("inventory"), self._load_dataset("history")
            for rule in inp.get("filters", []):
                inventory = self._apply_filter(inventory, rule)
            if inventory.empty:
                return "No vehicles remain after constraints."
            df = inventory.merge(history, left_on=["brand", "model", "year"], right_on=["brand", "model", "model_year"], how="left", suffixes=("_inventory", "_history"))
            higher = {"reliability_score_10", "owner_satisfaction_10", "three_year_value_retention_pct", "five_year_value_retention_pct", "owners_who_would_buy_again_pct", "cargo_cuft", "horsepower", "warranty_months_remaining", "dealer_discount_usd", "year"}
            lower = {"price_usd", "mileage", "distance_miles", "avg_annual_repair_cost_usd", "complaints_per_100_vehicles", "avg_annual_insurance_usd", "avg_annual_fuel_or_energy_usd", "previous_owners"}
            weights = {name: float(value) for name, value in inp["weights"].items()}
            unknown = [name for name in weights if name not in higher | lower]
            if unknown:
                return f"ERROR rank_inventory: unsupported metrics {unknown}"
            total = sum(weights.values())
            if total <= 0:
                return "ERROR rank_inventory: weights must total > 0."
            weights = {name: value / total for name, value in weights.items()}
            df["score"] = 0.0
            for metric, weight in weights.items():
                series = pd.to_numeric(df[metric], errors="coerce").fillna(pd.to_numeric(df[metric], errors="coerce").median())
                normalized = pd.Series(0.5, index=series.index) if series.max() == series.min() else (series - series.min()) / (series.max() - series.min())
                if metric in lower:
                    normalized = 1 - normalized
                df["score"] += normalized * weight * 100
            columns = ["stock_id", "year", "brand", "model", "trim", "price_usd", "mileage", "horsepower", "awd", "cargo_cuft", "reliability_score_10", "owner_satisfaction_10", "three_year_value_retention_pct", "avg_annual_repair_cost_usd", "avg_annual_insurance_usd", "avg_annual_fuel_or_energy_usd", "score"]
            result = df.sort_values("score", ascending=False)[[column for column in columns if column in df.columns]].head(min(max(int(inp.get("limit", 10)), 1), 20)).copy()
            result["score"] = result["score"].round(2)
            return json.dumps({"vehicles_after_constraints": len(df), "normalized_weights": weights, "ranking": json.loads(result.to_json(orient="records"))}, indent=2)
        except Exception as exc:
            return f"ERROR rank_inventory: {type(exc).__name__}: {exc}"
