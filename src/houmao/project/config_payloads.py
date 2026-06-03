"""Shared payload builders for project configuration YAML views."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def build_launch_profile_config_payload(
    *,
    name: str | None = None,
    profile_lane: str,
    source_kind: str,
    source_name: str,
    defaults: Mapping[str, Any],
    relaunch: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the shared YAML payload shape for launch-profile-like config."""

    payload: dict[str, Any] = {}
    if name is not None:
        payload["name"] = name
    payload["profile_lane"] = profile_lane
    payload["source"] = {
        "kind": source_kind,
        "name": source_name,
    }
    payload["defaults"] = dict(defaults)
    if relaunch:
        payload["relaunch"] = dict(relaunch)
    return payload
