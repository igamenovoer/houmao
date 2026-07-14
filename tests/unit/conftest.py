"""Pytest configuration for unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "qualification"
    / "tui-prompt-admission"
)
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
