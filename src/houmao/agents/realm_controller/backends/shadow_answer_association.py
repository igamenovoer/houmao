"""Optional caller-side helpers for answer association over dialog projection.

These helpers are intentionally caller-owned best-effort escape hatches. When a
downstream path needs reliable machine-readable output, prefer schema-shaped
prompting plus explicit sentinel or pattern extraction over generic
``dialog_projection.dialog_text`` cleanup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from .shadow_parser_core import DialogProjection


class DialogAssociator(Protocol):
    """Associate caller-owned answer text from projected dialog content."""

    def associate(self, dialog_projection: DialogProjection | str) -> str | None:
        """Return caller-associated text from projected dialog, if any."""


@dataclass(frozen=True)
class TailRegexExtractAssociator:
    """Extract caller-owned text by regex-searching projected dialog.

    This remains a best-effort helper over projected dialog text rather than a
    runtime-owned exact-text contract.
    """

    tail_chars: int
    pattern: str
    flags: int = 0

    def __post_init__(self) -> None:
        if self.tail_chars <= 0:
            raise ValueError("tail_chars must be positive")
        if not self.pattern:
            raise ValueError("pattern must not be empty")

    def associate(self, dialog_projection: DialogProjection | str) -> str | None:
        """Return the regex match from the last ``tail_chars`` of dialog text."""

        dialog_text = (
            dialog_projection.dialog_text
            if isinstance(dialog_projection, DialogProjection)
            else dialog_projection
        )
        if not dialog_text:
            return None

        tail_window = dialog_text[-self.tail_chars :]
        match = re.search(self.pattern, tail_window, self.flags)
        if match is None:
            return None

        if match.lastindex:
            for index in range(match.lastindex, 0, -1):
                group_value = match.group(index)
                if group_value is not None:
                    return group_value
        return match.group(0)
