"""YAML export helpers for command-template metadata."""

from __future__ import annotations

from pathlib import Path

import yaml

from .registry import get_command_template
from .registry import _registry


def export_command_template_yaml(template_id: str) -> str:
    """Return a deterministic YAML view of one command template."""

    payload = get_command_template(template_id).to_payload()
    return _dump_yaml(payload)


def export_command_templates_yaml() -> str:
    """Return a deterministic YAML view of every command template."""

    payload = {
        "templates": [
            template.to_payload()
            for template in sorted(_registry().values(), key=lambda item: item.template_id)
        ]
    }
    return _dump_yaml(payload)


def write_command_template_yaml(template_id: str, output_path: Path) -> Path:
    """Write one command template YAML document and return the resolved path."""

    resolved = output_path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(export_command_template_yaml(template_id), encoding="utf-8")
    return resolved


def write_command_templates_yaml(output_dir: Path) -> tuple[Path, ...]:
    """Write one YAML document per command template and return written paths."""

    resolved_dir = output_dir.expanduser().resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for template in sorted(_registry().values(), key=lambda item: item.template_id):
        path = resolved_dir / f"{template.template_id}.yaml"
        path.write_text(_dump_yaml(template.to_payload()), encoding="utf-8")
        written.append(path)
    return tuple(written)


def _dump_yaml(payload: object) -> str:
    """Dump one payload as deterministic YAML with a trailing newline."""

    document = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    return document if document.endswith("\n") else f"{document}\n"
