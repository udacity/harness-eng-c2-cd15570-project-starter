"""TODO: Add scoped permission enforcement to Loop 01."""

from __future__ import annotations

from .loop_01_non_production import HarnessLoop


class PermissionsLoop(HarnessLoop):
    """Extend Loop 01 with allow, approval-required, and deny decisions."""

    # TODO: Use PermissionPolicy before executing each registered tool.
    # TODO: Pause for an approval-required action and consume a grant only when
    # the model reissues the exact approved tool request.
    pass
