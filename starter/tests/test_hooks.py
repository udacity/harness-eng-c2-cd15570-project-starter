"""Target contract for deterministic hook enforcement."""

from harness.stage_05_antidotes import AntidoteRegistry
from harness.stage_05_antidotes import plotting


def test_antidote_registry_blocks_negative_ranking_weights():
    registry = AntidoteRegistry()
    decision = registry.pre_tool(
        "rank_inventory",
        {"weights": {"price_usd": -1}},
    )
    assert decision is not None


def test_chart_requires_a_declared_population_but_accepts_full_dataset():
    assert plotting.validate({"dataset": "inventory"}) is not None
    assert plotting.validate({"dataset": "inventory", "filters": []}) is None


def test_chart_antidote_returns_handler_values():
    class Handlers:
        def plot_evidence(self, tool_input):
            assert tool_input["filters"] == []
            return "population: 10; correlation: 0.42"

    assert "correlation: 0.42" in plotting.build_evidence(
        Handlers(), {"dataset": "inventory", "filters": []}
    )
