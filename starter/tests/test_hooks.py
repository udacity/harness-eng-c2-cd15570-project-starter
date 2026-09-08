"""Target contract for deterministic hook enforcement."""

from harness.stage_05_antidotes import AntidoteRegistry


def test_antidote_registry_blocks_negative_ranking_weights():
    registry = AntidoteRegistry()
    decision = registry.pre_tool(
        "rank_inventory",
        {"weights": {"price_usd": -1}},
    )
    assert decision is not None
