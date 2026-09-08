"""Central registry for the Vehicle EDA tool contract."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "column": {"type": "string"},
        "operator": {"type": "string", "enum": ["eq", "ne", "lt", "lte", "gt", "gte", "contains", "in"]},
        "value": {},
    },
    "required": ["column", "operator", "value"],
    "additionalProperties": False,
}


def tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


def tool_definitions() -> list[dict[str, Any]]:
    dataset = {"dataset": {"type": "string", "enum": ["inventory", "history", "sales_reviews"]}}
    return [
        tool("list_skills", "List available specialized vehicle-domain skills and their descriptions.", {}),
        tool("load_skill", "Load one specialized vehicle-domain skill before using its guidance.", {"name": {"type": "string"}}, ["name"]),
        tool("write_plan", "Write the complete analysis plan before asking the user to approve it.", {"tasks": {"type": "array", "items": {"type": "string"}, "minItems": 1}}, ["tasks"]),
        tool("request_approval", "Pause for the user's approval after writing a plan and before executing its planned analysis.", {"message": {"type": "string"}}),
        tool("dataset_info", "Inspect dataset columns, data types, and row count.", dataset, ["dataset"]),
        tool("sample_rows", "Read a small sample of dataset rows.", {**dataset, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, ["dataset"]),
        tool("describe_numeric", "Calculate descriptive statistics for numeric fields.", {**dataset, "columns": {"type": "array", "items": {"type": "string"}}}, ["dataset"]),
        tool("data_quality_report", "Report duplicate records, missing values, malformed numeric fields, and inconsistent categories before analyzing a dataset.", dataset, ["dataset"]),
        tool("hypothesis_test", "Run a Welch two-sample t-test comparing one numeric metric across two named groups.", {**dataset, "value_column": {"type": "string"}, "group_column": {"type": "string"}, "group_a": {}, "group_b": {}, "alternative": {"type": "string", "enum": ["two-sided", "less", "greater"]}, "alpha": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1}}, ["dataset", "value_column", "group_column", "group_a", "group_b"]),
        tool("value_counts", "Count common values in a categorical column.", {**dataset, "column": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, ["dataset", "column"]),
        tool("plot_data", "Create and display a PNG bar, scatter, line, or histogram chart for a filtered dataset population.", {**dataset, "filters": {"type": "array", "items": FILTER_SCHEMA}, "x": {"type": "string"}, "y": {"type": "string"}, "kind": {"type": "string", "enum": ["bar", "scatter", "line", "hist"]}, "title": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}, "show": {"type": "boolean", "description": "Display the plot on screen; defaults to true."}}, ["dataset", "filters", "x"]),
        tool("filter_inventory", "Apply hard buyer constraints to current inventory before ranking preferences.", {"filters": {"type": "array", "items": FILTER_SCHEMA}, "columns": {"type": "array", "items": {"type": "string"}}, "sort_by": {"type": "string"}, "ascending": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, ["filters"]),
        tool("lookup_vehicle", "Inspect one exact stock ID and matching model-year history.", {"stock_id": {"type": "string"}}, ["stock_id"]),
        tool("model_history", "Inspect reliability and ownership history for one brand/model.", {"brand": {"type": "string"}, "model": {"type": "string"}, "start_year": {"type": "integer"}, "end_year": {"type": "integer"}}, ["brand", "model"]),
        tool("compare_vehicles", "Compare one to ten exact stock IDs using inventory and history evidence.", {"stock_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 10}}, ["stock_ids"]),
        tool("rank_inventory", "Filter and rank inventory using explicit weighted criteria.", {"filters": {"type": "array", "items": FILTER_SCHEMA}, "weights": {"type": "object", "additionalProperties": {"type": "number"}}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, ["weights"]),
    ]


class ToolRegistry:
    knowledge = frozenset({"list_skills", "load_skill"})
    planning = frozenset({"write_plan", "request_approval"})
    execution = frozenset({"dataset_info", "sample_rows", "describe_numeric", "data_quality_report", "hypothesis_test", "value_counts", "plot_data", "filter_inventory", "lookup_vehicle", "model_history", "compare_vehicles", "rank_inventory"})

    def __init__(self, handlers: dict[str, Callable[[dict[str, Any]], str]]):
        self.handlers = handlers
        self.definitions = tool_definitions()
