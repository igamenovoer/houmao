"""Persistence helpers for the manual Kimi writer-team demo pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import DemoParameters, DemoState


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write one JSON object with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def load_demo_parameters(path: Path) -> DemoParameters:
    """Load tracked demo parameters."""

    return DemoParameters.model_validate_json(path.read_text(encoding="utf-8"))


def save_demo_state(path: Path, state: DemoState) -> None:
    """Persist the active demo state."""

    write_json(path, state.model_dump(mode="json"))


def load_demo_state(path: Path) -> DemoState:
    """Load persisted demo state."""

    return DemoState.model_validate_json(path.read_text(encoding="utf-8"))
