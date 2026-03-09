from __future__ import annotations

import pytest

from gig_agents.agents.brain_launch_runtime.backends.shadow_answer_association import (
    TailRegexExtractAssociator,
)
from gig_agents.agents.brain_launch_runtime.backends.shadow_parser_core import (
    DialogProjection,
    ProjectionMetadata,
    ShadowParserMetadata,
)


def _projection(dialog_text: str) -> DialogProjection:
    parser_metadata = ShadowParserMetadata(
        provider_id="codex",
        parser_preset_id="codex_shadow_v2",
        parser_preset_version="0.98.0",
        output_format="codex_shadow_v2",
        output_variant="codex_tui_bullet_v1",
        output_format_match=True,
    )
    projection_metadata = ProjectionMetadata(
        provider_id="codex",
        source_kind="tui_snapshot",
        projector_id="codex_dialog_projection_v1",
        parser_metadata=parser_metadata,
        dialog_line_count=len(dialog_text.splitlines()),
        head_line_count=len(dialog_text.splitlines()),
        tail_line_count=len(dialog_text.splitlines()),
    )
    return DialogProjection(
        raw_text=dialog_text,
        normalized_text=dialog_text,
        dialog_text=dialog_text,
        head=dialog_text,
        tail=dialog_text,
        projection_metadata=projection_metadata,
    )


def test_tail_regex_extract_associator_matches_last_capture_group() -> None:
    associator = TailRegexExtractAssociator(
        tail_chars=64,
        pattern=r"final_answer:\s*(.+)$",
        flags=0,
    )

    matched = associator.associate("prefix\nfinal_answer: done")

    assert matched == "done"


def test_tail_regex_extract_associator_accepts_dialog_projection() -> None:
    associator = TailRegexExtractAssociator(
        tail_chars=64,
        pattern=r"RESULT=(.+)$",
    )

    matched = associator.associate(_projection("context\nRESULT=success"))

    assert matched == "success"


def test_tail_regex_extract_associator_validates_input() -> None:
    with pytest.raises(ValueError, match="tail_chars"):
        TailRegexExtractAssociator(tail_chars=0, pattern="x")
