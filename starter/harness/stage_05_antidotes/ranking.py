"""Deterministic check for unsafe inventory-ranking arguments."""

from __future__ import annotations

from typing import Any


SUPPORTED_METRICS = frozenset({
    "reliability_score_10", "owner_satisfaction_10",
    "three_year_value_retention_pct", "five_year_value_retention_pct",
    "owners_who_would_buy_again_pct", "cargo_cuft", "horsepower",
    "warranty_months_remaining", "dealer_discount_usd", "year",
    "price_usd", "mileage", "distance_miles",
    "avg_annual_repair_cost_usd", "complaints_per_100_vehicles",
    "avg_annual_insurance_usd", "avg_annual_fuel_or_energy_usd",
    "previous_owners",
})


def validate(tool_input: dict[str, Any]) -> str | None:
    """Return a reason for unsupported or negative ranking weights."""
    # TODO: Check weight names against SUPPORTED_METRICS and reject any
    # negative weight. The ranking handler already handles metrics where
    # lower values are better; a negative weight would reverse them twice.
    return None
