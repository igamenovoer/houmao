"""Shared Codex home bootstrap helpers for non-interactive launches."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any, Final

from ..errors import BackendExecutionError

_CONFIG_FILENAME: Final[str] = "config.toml"
_TOP_LEVEL_KEY_RE_TEMPLATE: Final[str] = r"^\s*{key}\s*="
_TABLE_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*\[([^\[\]]+)\]\s*(?:#.*)?$"
)


def ensure_codex_home_bootstrap(*, home_path: Path, working_directory: Path) -> None:
    """Ensure Codex runtime-home bootstrap invariants before launch.

    Parameters
    ----------
    home_path:
        Runtime Codex home path (`CODEX_HOME`).
    working_directory:
        Launch working directory used to resolve the trust target.
    """

    home_path.mkdir(parents=True, exist_ok=True)
    config_path = home_path / _CONFIG_FILENAME
    original_text = (
        config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    )
    parsed = _parse_config_toml(config_path=config_path, raw_text=original_text)
    trust_target = _resolve_trust_target(working_directory)

    updated_text = original_text
    updated_text = _upsert_table_key(
        raw_text=updated_text,
        table_name="notice",
        key="hide_full_access_warning",
        value_literal="true",
    )
    updated_text = _upsert_table_key(
        raw_text=updated_text,
        table_name=f"projects.{_toml_string_literal(str(trust_target))}",
        key="trust_level",
        value_literal=_toml_string_literal("trusted"),
    )

    for key in ("approval_policy", "sandbox_mode"):
        configured_value = parsed.get(key)
        if isinstance(configured_value, str) and configured_value.strip():
            updated_text = _upsert_top_level_key(
                raw_text=updated_text,
                key=key,
                value_literal=_toml_string_literal(configured_value.strip()),
            )

    if updated_text != original_text:
        config_path.write_text(updated_text, encoding="utf-8")


def _parse_config_toml(*, config_path: Path, raw_text: str) -> dict[str, Any]:
    """Parse existing Codex config and fail fast on malformed TOML."""

    if not raw_text.strip():
        return {}
    try:
        payload = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:
        raise BackendExecutionError(
            f"Malformed Codex config `{config_path}`: {exc}."
        ) from exc
    if not isinstance(payload, dict):
        raise BackendExecutionError(
            f"Codex config `{config_path}` must contain a top-level TOML table."
        )
    return payload


def _resolve_trust_target(working_directory: Path) -> Path:
    """Resolve workspace trust target to agent-definition root when available."""

    resolved_workdir = working_directory.resolve()
    for candidate in (resolved_workdir, *resolved_workdir.parents):
        if (candidate / ".git").exists():
            return candidate
    return resolved_workdir


def _upsert_top_level_key(*, raw_text: str, key: str, value_literal: str) -> str:
    """Set one top-level scalar key while preserving unrelated config text."""

    lines = raw_text.splitlines()
    key_re = re.compile(_TOP_LEVEL_KEY_RE_TEMPLATE.format(key=re.escape(key)))
    current_table: str | None = None
    first_table_index: int | None = None

    for index, line in enumerate(lines):
        table_name = _table_header_name(line)
        if table_name is not None:
            current_table = table_name
            if first_table_index is None:
                first_table_index = index
            continue
        if current_table is not None:
            continue
        if key_re.match(line):
            lines[index] = f"{key} = {value_literal}"
            return _join_lines(lines)

    insert_index = first_table_index if first_table_index is not None else len(lines)
    lines.insert(insert_index, f"{key} = {value_literal}")
    return _join_lines(lines)


def _upsert_table_key(
    *,
    raw_text: str,
    table_name: str,
    key: str,
    value_literal: str,
) -> str:
    """Set one key in a target table while preserving unrelated config text."""

    lines = raw_text.splitlines()
    key_re = re.compile(_TOP_LEVEL_KEY_RE_TEMPLATE.format(key=re.escape(key)))

    section_start, section_end = _section_bounds(lines, table_name=table_name)
    if section_start is None or section_end is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"[{table_name}]")
        lines.append(f"{key} = {value_literal}")
        return _join_lines(lines)

    for index in range(section_start, section_end):
        if key_re.match(lines[index]):
            lines[index] = f"{key} = {value_literal}"
            return _join_lines(lines)

    insert_index = section_end
    while insert_index > section_start and not lines[insert_index - 1].strip():
        insert_index -= 1
    lines.insert(insert_index, f"{key} = {value_literal}")
    return _join_lines(lines)


def _section_bounds(
    lines: list[str], *, table_name: str
) -> tuple[int | None, int | None]:
    """Return `(start, end)` line indexes for a named table section."""

    header_index: int | None = None
    for index, line in enumerate(lines):
        if _table_header_name(line) == table_name:
            header_index = index
            break
    if header_index is None:
        return None, None

    section_start = header_index + 1
    section_end = len(lines)
    for index in range(section_start, len(lines)):
        if _table_header_name(lines[index]) is not None:
            section_end = index
            break
    return section_start, section_end


def _table_header_name(line: str) -> str | None:
    """Extract a plain table header name from one TOML line."""

    match = _TABLE_HEADER_RE.match(line)
    if match is None:
        return None
    return match.group(1).strip()


def _toml_string_literal(value: str) -> str:
    """Render one TOML basic string literal."""

    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _join_lines(lines: list[str]) -> str:
    """Join text lines and keep the output newline-terminated."""

    if not lines:
        return ""
    return "\n".join(lines) + "\n"
