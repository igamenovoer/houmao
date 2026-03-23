"""Shared response-text extraction helpers for repo-owned CAO demos.

These helpers intentionally distinguish between:

- schema/sentinel-shaped extraction, which is reliable enough for downstream
  demo verification when the prompt requests it explicitly, and
- best-effort extraction from shadow dialog projection, which remains a
  human-facing fallback rather than an exact-text contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Iterable


@dataclass(frozen=True)
class ResponseTextExtraction:
    """Extracted response text plus a source label for caller diagnostics."""

    response_text: str
    response_text_source: str


def load_response_text_from_jsonl(
    path: Path,
    *,
    sentinel_begin: str | None = None,
    sentinel_end: str | None = None,
) -> ResponseTextExtraction:
    """Load runtime events from one JSONL file and extract response text."""

    events: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            events.append(payload)
    return extract_response_text_from_events(
        events,
        sentinel_begin=sentinel_begin,
        sentinel_end=sentinel_end,
    )


def extract_response_text_from_events(
    events: Iterable[dict[str, Any]],
    *,
    sentinel_begin: str | None = None,
    sentinel_end: str | None = None,
) -> ResponseTextExtraction:
    """Extract response text from runtime event payloads.

    Sentinel extraction runs first over closer-to-source text surfaces. If no
    sentinel contract was provided or no sentinel payload is found, the helper
    falls back to one best-effort shadow-aware summary from the final
    ``dialog_projection.dialog_text`` line or, finally, from ``done.message``.
    """

    event_list = list(events)
    if sentinel_begin and sentinel_end:
        for source_id, text in _candidate_text_surfaces(event_list):
            extracted = _extract_sentinel_payload(
                text=text,
                sentinel_begin=sentinel_begin,
                sentinel_end=sentinel_end,
            )
            if extracted is not None:
                return ResponseTextExtraction(
                    response_text=extracted,
                    response_text_source=f"{source_id}:sentinel",
                )

    for event in reversed(event_list):
        if event.get("kind") != "done":
            continue

        payload = event.get("payload")
        if isinstance(payload, dict):
            dialog_projection = payload.get("dialog_projection")
            if isinstance(dialog_projection, dict):
                dialog_text = dialog_projection.get("dialog_text")
                if isinstance(dialog_text, str):
                    lines = [line.strip() for line in dialog_text.splitlines() if line.strip()]
                    if lines:
                        return ResponseTextExtraction(
                            response_text=lines[-1],
                            response_text_source="dialog_projection_last_line_best_effort",
                        )

        done_message = str(event.get("message", "")).strip()
        if done_message:
            return ResponseTextExtraction(
                response_text=done_message,
                response_text_source="done_message_best_effort",
            )

    return ResponseTextExtraction(
        response_text="",
        response_text_source="unavailable",
    )


def _candidate_text_surfaces(events: list[dict[str, Any]]) -> tuple[tuple[str, str], ...]:
    """Return ordered text surfaces for sentinel extraction."""

    surfaces: list[tuple[str, str]] = []

    for event in reversed(events):
        if event.get("kind") != "done":
            continue

        payload = event.get("payload")
        if isinstance(payload, dict):
            dialog_projection = payload.get("dialog_projection")
            if isinstance(dialog_projection, dict):
                for key in ("normalized_text", "raw_text", "dialog_text", "tail"):
                    value = dialog_projection.get(key)
                    if isinstance(value, str) and value.strip():
                        surfaces.append((f"done_payload.dialog_projection.{key}", value))

            output_text = payload.get("output_text")
            if isinstance(output_text, str) and output_text.strip():
                surfaces.append(("done_payload.output_text", output_text))

        message = str(event.get("message", "")).strip()
        if message:
            surfaces.append(("done.message", message))

    return tuple(surfaces)


def _extract_sentinel_payload(
    *,
    text: str,
    sentinel_begin: str,
    sentinel_end: str,
) -> str | None:
    """Extract the text between one sentinel pair from one candidate surface."""

    begin_count = text.count(sentinel_begin)
    end_count = text.count(sentinel_end)
    if begin_count != 1 or end_count != 1:
        return None

    begin_index = text.find(sentinel_begin)
    end_index = text.find(sentinel_end, begin_index + len(sentinel_begin))
    if begin_index < 0 or end_index <= begin_index:
        return None

    extracted = text[begin_index + len(sentinel_begin) : end_index].strip()
    if not extracted:
        return None
    return extracted
