"""Prepare direct native DSH fixtures from their selected private home."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from houmao.agents.dsh_configuration import (
    MATERIALIZED_DSH_TOOL_PARAMS,
    DshConfigurationError,
    DshEffectiveToolParams,
    DshLoadedHome,
    DshPreparedHome,
    load_dsh_home,
)

from fixturelib.auth import private_write
from fixturelib.config import FixtureError


def prepare_raw_dsh_patch(prepared: DshPreparedHome) -> Path:
    """Add the literal role to the direct fixture's headless invocation."""

    patch = [
        {
            "insert": [
                {
                    "id": "houmao-fixture-role",
                    "name": str(Path(__file__).with_name("dsh-role.mjs")),
                    "config": {"roleFile": str(prepared.role_path)},
                }
            ]
        }
    ]
    target = prepared.patch_path.with_name("fixture-headless-role.patch.json")
    private_write(target, (json.dumps(patch, indent=2) + "\n").encode())
    return target


def load_raw_dsh_home(run: dict[str, Any], env: dict[str, str]) -> DshLoadedHome:
    """Read the isolated credentials and native profile selected for the raw worker."""

    home = Path(run["home_path"])
    try:
        setup = DshEffectiveToolParams.from_file(home / MATERIALIZED_DSH_TOOL_PARAMS)
        return load_dsh_home(home, setup, env, native_profile="headless")
    except DshConfigurationError:
        raise FixtureError("Selected native DSH headless home cannot be loaded") from None
