"""Deterministic checks and evidence for chart calls."""

from __future__ import annotations

from typing import Any


def validate(tool_input: dict[str, Any]) -> str | None:
    """Return a blocking reason when the chart population is not declared."""
    # TODO: Require the filters key. An empty list is an explicit full-dataset
    # population and must be accepted; a missing key is not.
    return None


def build_evidence(handlers: Any, tool_input: dict[str, Any]) -> str:
    """Return numbers behind a successfully generated chart."""
    # TODO: Use handlers.plot_evidence(tool_input). It reports population and
    # deterministic grouped means/counts or ranges/correlation as applicable.
    # Do not ask the model to infer those values from the image.
    raise NotImplementedError("Add deterministic chart evidence.")
