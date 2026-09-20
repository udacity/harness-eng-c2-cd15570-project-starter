"""Deterministic check for duplicate vehicle comparisons."""

from __future__ import annotations

from typing import Any


def validate(tool_input: dict[str, Any]) -> str | None:
    """Return a reason when compare_vehicles repeats a stock ID."""
    # TODO: Compare stock_ids with its unique set. Repeating a vehicle can
    # make a comparison look broader than it is.
    return None
