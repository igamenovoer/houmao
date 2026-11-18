"""Remove credentials from native DSH messages before public presentation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import quote, quote_plus

_REDACTED = "[REDACTED]"
_PERCENT_ESCAPE = re.compile(r"%[0-9A-Fa-f]{2}")
_TERMINAL_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_CONTROL_CHAR = re.compile(r"[\x00-\x08\x0e-\x1f\x7f-\x9f]")
_BEARER = re.compile(r"(?i)(\bbearer(?:\s+|%20|\+))(?:\[REDACTED\]|[^\s,;&\"'<>\]}]+)")
_API_KEY = re.compile(r"(?i)\bsk-[a-z0-9_-]+")
_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:authorization|api[\s_-]?key|x-api-key|access[\s_-]?token|"
    r"launch[\s_-]?token|token|(?:set-)?cookie)\b[\"']?\s*[:=]\s*)"
    r"(?:bearer[ \t]+)?"
    r"(?:\[REDACTED\]|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;&\"'<>\]}]+)"
)
_COOKIE_HEADER = re.compile(r"(?im)(\b(?:set-)?cookie[\"']?[ \t]*:[ \t]*+)(?!\[REDACTED\])[^\r\n]+")
_AUTHORIZATION_KEY_NAMES = (
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "HOUMAO_DSH_LOCAL_API_KEY",
)


def dsh_diagnostic_secrets(
    environment: Mapping[str, str], *, key_name: str | None = None
) -> tuple[str, ...]:
    """Select the configured API key and standard private provider environment values."""

    names = (
        (*_AUTHORIZATION_KEY_NAMES, key_name) if key_name is not None else _AUTHORIZATION_KEY_NAMES
    )
    return tuple(environment[name] for name in names if environment.get(name))


def sanitize_dsh_diagnostic(
    text: str, *, secret_values: Iterable[str] = (), max_length: int = 512
) -> str:
    """Return a bounded single line with exact and recognizable credentials removed."""

    text = _CONTROL_CHAR.sub("", _TERMINAL_ESCAPE.sub("", text))
    spellings: set[str] = set()
    for value in secret_values:
        if not value:
            continue
        normalized = _CONTROL_CHAR.sub("", _TERMINAL_ESCAPE.sub("", value))
        spellings.update((value, normalized, " ".join(normalized.split())))
        spellings.add(json.dumps(value, ensure_ascii=False)[1:-1])
        for encoded in (quote(value, safe=""), quote_plus(value)):
            spellings.add(encoded)
            spellings.add(_PERCENT_ESCAPE.sub(lambda match: match[0].lower(), encoded))
    spellings.discard("")
    exact = None
    if spellings:
        longest_first = sorted(spellings, key=lambda value: (-len(value), value))
        exact = re.compile("|".join(re.escape(value) for value in longest_first))
        text = exact.sub(_REDACTED, text)
    text = _COOKIE_HEADER.sub(lambda match: f"{match[1]}{_REDACTED}", text)
    text = _BEARER.sub(lambda match: f"{match[1]}{_REDACTED}", text)
    text = _API_KEY.sub(_REDACTED, text)
    text = _CREDENTIAL_ASSIGNMENT.sub(lambda match: f"{match[1]}{_REDACTED}", text)
    summary = " ".join(text.split())
    if exact is not None:
        summary = exact.sub(_REDACTED, summary)
    if max_length <= 0:
        return ""
    return summary if len(summary) <= max_length else summary[: max_length - 1] + "…"


def dsh_diagnostic_tail(path: Path) -> str:
    """Read complete trailing lines from an owned private diagnostic artifact."""

    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077
            ):
                return ""
            size = stream.seek(0, 2)
            offset = max(0, size - 64 * 1024)
            stream.seek(offset)
            if offset:
                stream.readline(64 * 1024)
            return stream.read(64 * 1024).decode("utf-8", errors="replace")
    except OSError:
        return ""
