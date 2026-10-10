"""Load and expand iteration-1 promptfoo-format session specs.

The session YAML files under the campaign's iteration directory are
promptfoo ``TestSuiteConfig`` documents whose ``vars.ops`` carry a
tracker-blind operation vocabulary. This module parses them and resolves
``catalog_operation`` references verbatim against the reviewed UC-02 suite
catalog, expanding ``{{SAFE}}`` with the suite's ``safe_prefix``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
SUITE_PATH = REPO_ROOT / "scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json"

_BACKTICK_RE = re.compile(r"`([^`]+)`", re.DOTALL)
_CATALOG_REF_RE = re.compile(r"^(?P<proc>st-\d+):op(?P<num>\d+)$")
_OP_KINDS = frozenset(
    {
        "type_text",
        "submit_text",
        "send_key",
        "wait_seconds",
        "wait_for_pattern",
        "catalog_operation",
    }
)


@dataclass(frozen=True)
class SessionCase:
    """One promptfoo test case expanded to concrete drive operations."""

    case_id: str
    description: str
    ops: tuple[dict[str, Any], ...]
    asserts: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SessionSpec:
    """Expanded session spec ready for the runner."""

    path: Path
    description: str
    provider_config: dict[str, Any]
    default_asserts: tuple[dict[str, Any], ...]
    cases: tuple[SessionCase, ...]


def load_session_spec(path: Path) -> SessionSpec:
    """Load one session YAML and expand every case's operations."""

    resolved = path.resolve()
    document = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"Session spec `{resolved}` is not a mapping")
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    safe_prefix = str(suite["safe_prefix"]).strip()
    providers = document.get("providers") or []
    provider_config = dict(providers[0].get("config") or {}) if providers else {}
    default_asserts = tuple((document.get("defaultTest") or {}).get("assert") or ())
    cases: list[SessionCase] = []
    for raw_case in document.get("tests") or []:
        vars_block = raw_case.get("vars") or {}
        case_id = str(vars_block.get("case_id") or "").strip()
        if not case_id:
            raise ValueError(f"Case without vars.case_id in `{resolved}`")
        ops = tuple(
            _expand_op(op, suite=suite, safe_prefix=safe_prefix, case_id=case_id)
            for op in (vars_block.get("ops") or [])
        )
        cases.append(
            SessionCase(
                case_id=case_id,
                description=str(raw_case.get("description") or case_id),
                ops=ops,
                asserts=tuple(raw_case.get("assert") or ()),
            )
        )
    return SessionSpec(
        path=resolved,
        description=str(document.get("description") or ""),
        provider_config=provider_config,
        default_asserts=default_asserts,
        cases=tuple(cases),
    )


def _expand_op(
    op: dict[str, Any], *, suite: dict[str, Any], safe_prefix: str, case_id: str
) -> dict[str, Any]:
    """Expand one raw op mapping into a concrete drive operation."""

    kind = str(op.get("kind") or "")
    if kind not in _OP_KINDS:
        raise ValueError(f"Unknown op kind {kind!r} in case {case_id!r}")
    expanded = dict(op)
    if "text" in expanded and isinstance(expanded["text"], str):
        expanded["text"] = expanded["text"].replace("{{SAFE}}", safe_prefix)
    if kind == "catalog_operation":
        expanded = _resolve_catalog_op(
            ref=str(op["ref"]), suite=suite, safe_prefix=safe_prefix, case_id=case_id
        )
        expanded["name"] = op.get("name") or f"catalog-{op['ref']}"
        expanded["meaning"] = op.get("meaning") or ""
        expanded["catalog_ref"] = op["ref"]
    expanded.setdefault("name", f"{kind}-{case_id}")
    return expanded


def _resolve_catalog_op(
    *, ref: str, suite: dict[str, Any], safe_prefix: str, case_id: str
) -> dict[str, Any]:
    """Resolve one ``st-NN:opNN`` catalog reference to a concrete operation."""

    match = _CATALOG_REF_RE.match(ref.strip())
    if match is None:
        raise ValueError(f"Malformed catalog ref {ref!r} in case {case_id!r}")
    procedure = next(
        (item for item in suite["procedures"] if item.get("id") == match.group("proc")), None
    )
    if procedure is None:
        raise ValueError(f"Catalog procedure {match.group('proc')!r} not found (case {case_id!r})")
    number = int(match.group("num"))
    operation = next(
        (item for item in procedure["operations"] if int(item.get("number")) == number), None
    )
    if operation is None:
        raise ValueError(f"Catalog op {ref!r} not found (case {case_id!r})")
    instruction = str(operation["instruction"])
    quoted = _BACKTICK_RE.search(instruction)
    catalog_kind = str(operation["kind"])
    if catalog_kind in {"submit_text", "type_text"}:
        if quoted is None:
            raise ValueError(f"Catalog op {ref!r} has no backtick-quoted payload")
        text = quoted.group(1).replace("{{SAFE}}", safe_prefix)
        return {"kind": catalog_kind, "text": text}
    if catalog_kind == "send_keys":
        if quoted is None:
            raise ValueError(f"Catalog op {ref!r} has no backtick-quoted key")
        return {"kind": "send_key", "key": _normalize_key_name(quoted.group(1))}
    raise ValueError(f"Unsupported catalog op kind {catalog_kind!r} for {ref!r}")


def _normalize_key_name(name: str) -> str:
    """Map catalog key spellings (``Ctrl+C``) to runner key names (``C-c``)."""

    normalized = name.strip()
    ctrl_match = re.fullmatch(r"Ctrl\+([A-Za-z])", normalized)
    if ctrl_match:
        return f"C-{ctrl_match.group(1).lower()}"
    aliases = {"Backspace": "BSpace", "Esc": "Escape", "Shift+Tab": "BTab"}
    return aliases.get(normalized, normalized)
