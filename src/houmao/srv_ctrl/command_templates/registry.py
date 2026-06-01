"""Registry assembly for code-first command templates."""

from __future__ import annotations

import click

from .families import (
    agents_gateway,
    agents_lifecycle,
    credentials,
    mailbox,
    managed_agent_mail,
    project_agents,
    project_easy,
)
from collections.abc import Iterable

from .models import CommandTemplate

_FAMILY_MODULES = (
    project_easy,
    project_agents,
    credentials,
    agents_lifecycle,
    agents_gateway,
    mailbox,
    managed_agent_mail,
)


def list_command_templates() -> dict[str, object]:
    """Return the command-template inventory payload."""

    templates = sorted(_registry().values(), key=lambda template: template.template_id)
    return {
        "templates": [template.summary_payload() for template in templates],
        "count": len(templates),
        "scope": "existing houmao-mgr command surfaces only",
        "excluded_template_kinds": [
            "loop execplan scaffolds",
            "workspace layout scaffolds",
            "semantic workflow prompts",
            "tours and advanced examples",
        ],
    }


def get_command_template(template_id: str) -> CommandTemplate:
    """Return one registered command template or raise a CLI-facing error."""

    normalized_id = template_id.strip()
    template = _registry().get(normalized_id)
    if template is None:
        raise click.ClickException(
            f"Command template id `{normalized_id}` is not registered. "
            "Run `houmao-mgr internals command-templates list` to inspect supported ids."
        )
    return template


def show_command_template(template_id: str) -> dict[str, object]:
    """Return one full command-template metadata payload."""

    return get_command_template(template_id).to_payload()


def _registry() -> dict[str, CommandTemplate]:
    """Build the command-template registry."""

    templates: list[CommandTemplate] = []
    for family_module in _FAMILY_MODULES:
        templates.extend(family_module.templates())

    return build_template_registry(templates)


def build_template_registry(templates: Iterable[CommandTemplate]) -> dict[str, CommandTemplate]:
    """Return templates keyed by id, failing clearly on duplicate ids."""

    registry: dict[str, CommandTemplate] = {}
    duplicates: list[str] = []
    for template in templates:
        if template.template_id in registry:
            duplicates.append(template.template_id)
            continue
        registry[template.template_id] = template
    if duplicates:
        duplicate_list = ", ".join(sorted(set(duplicates)))
        raise click.ClickException(f"Duplicate command-template id(s): {duplicate_list}")
    return registry
