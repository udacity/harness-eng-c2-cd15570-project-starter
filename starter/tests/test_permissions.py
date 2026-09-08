"""Target contract for least-privilege tool permissions."""

from harness.stage_06_permissions import PermissionPolicy


def test_permission_policy_allows_read_only_eda():
    decision, _ = PermissionPolicy().decide(
        "dataset_info",
        {"dataset": "inventory"},
    )
    assert decision == "allow"
