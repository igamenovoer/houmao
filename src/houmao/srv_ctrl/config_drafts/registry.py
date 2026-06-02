"""Registry assembly for config-draft generators."""

from __future__ import annotations

from collections.abc import Iterable

import click

from houmao.srv_ctrl.config_drafts.families import project_agent_config
from houmao.srv_ctrl.config_drafts.models import ConfigDraft

_FAMILY_MODULES = (project_agent_config,)


def list_config_drafts() -> dict[str, object]:
    """Return the compact config-draft inventory payload."""

    drafts = sorted(_registry().values(), key=lambda draft: draft.draft_id)
    return {
        "drafts": [draft.summary_payload() for draft in drafts],
        "count": len(drafts),
        "scope": "concrete project config drafts only",
    }


def get_config_draft(draft_id: str) -> ConfigDraft:
    """Return one registered config draft or raise a CLI-facing error."""

    normalized_id = draft_id.strip()
    draft = _registry().get(normalized_id)
    if draft is None:
        raise click.ClickException(
            f"Config draft id `{normalized_id}` is not registered. "
            "Run `houmao-mgr internals config-drafts list` to inspect supported ids."
        )
    return draft


def _registry() -> dict[str, ConfigDraft]:
    """Build the config-draft registry."""

    drafts: list[ConfigDraft] = []
    for family_module in _FAMILY_MODULES:
        drafts.extend(family_module.drafts())
    return build_config_draft_registry(drafts)


def build_config_draft_registry(drafts: Iterable[ConfigDraft]) -> dict[str, ConfigDraft]:
    """Return config drafts keyed by id, failing clearly on duplicate ids."""

    registry: dict[str, ConfigDraft] = {}
    duplicates: list[str] = []
    for draft in drafts:
        if draft.draft_id in registry:
            duplicates.append(draft.draft_id)
            continue
        registry[draft.draft_id] = draft
    if duplicates:
        duplicate_list = ", ".join(sorted(set(duplicates)))
        raise click.ClickException(f"Duplicate config-draft id(s): {duplicate_list}")
    return registry
