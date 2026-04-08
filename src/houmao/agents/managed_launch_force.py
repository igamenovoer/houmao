"""Shared managed-launch force-mode helpers."""

from __future__ import annotations

from typing import Literal, cast

ManagedLaunchForceMode = Literal["keep-stale", "clean"]

MANAGED_LAUNCH_FORCE_MODE_KEEP_STALE: ManagedLaunchForceMode = "keep-stale"
MANAGED_LAUNCH_FORCE_MODE_CLEAN: ManagedLaunchForceMode = "clean"
MANAGED_LAUNCH_FORCE_MODE_VALUES: tuple[ManagedLaunchForceMode, ...] = (
    MANAGED_LAUNCH_FORCE_MODE_KEEP_STALE,
    MANAGED_LAUNCH_FORCE_MODE_CLEAN,
)


def normalize_managed_launch_force_mode(
    value: str | None,
    *,
    source: str,
) -> ManagedLaunchForceMode | None:
    """Validate one optional managed-launch force mode."""

    if value is None:
        return None
    if value not in MANAGED_LAUNCH_FORCE_MODE_VALUES:
        expected = ", ".join(repr(item) for item in MANAGED_LAUNCH_FORCE_MODE_VALUES)
        raise ValueError(f"{source} must be one of {expected}; got {value!r}.")
    return cast(ManagedLaunchForceMode, value)
