"""Actor-scoped managed-agent instance-state commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import click

from houmao.agents.instance_state import (
    InstanceStateStore,
    migrate_instance_state,
    resolve_verified_self,
)
from houmao.agents.realm_controller.registry_storage import (
    load_managed_agent_record_by_agent_id,
    resolve_managed_agent_records_by_name,
)
from houmao.agents.private_workspace import PrivateWorkspace

from ..common import get_managed_agent_scope_context
from ..output import emit


def _self_store() -> InstanceStateStore:
    """Resolve the verified caller's state store."""

    identity = resolve_verified_self()
    if not identity.state_db.is_file():
        raise click.ClickException(
            f"Verified managed self has no initialized instance state: {identity.state_db}"
        )
    return InstanceStateStore(identity.state_db)


def _admin_store() -> InstanceStateStore:
    """Resolve one explicitly selected agent's state store."""

    scope = get_managed_agent_scope_context()
    if scope is None or scope.scope != "single":
        raise click.ClickException("Instance-state administration requires one explicit target.")
    if scope.agent_id is not None:
        record = load_managed_agent_record_by_agent_id(scope.agent_id)
    else:
        assert scope.agent_name is not None
        matches = resolve_managed_agent_records_by_name(scope.agent_name)
        if len(matches) != 1:
            raise click.ClickException(
                f"Expected one managed-agent target named `{scope.agent_name}`, got {len(matches)}."
            )
        record = matches[0]
    if record is None:
        raise click.ClickException("The explicit managed-agent target was not found.")
    manifest_path = Path(record.runtime.manifest_path)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        runtime = payload["runtime"]
        memory_root = Path(runtime["memory_root"]).resolve()
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise click.ClickException(
            "The selected managed-agent manifest has no usable memory authority."
        ) from exc
    state_db = memory_root / "state.sqlite"
    if not state_db.is_file():
        raise click.ClickException(
            f"The selected managed agent has no initialized instance state: {state_db}"
        )
    return InstanceStateStore(state_db)


def _parse_scalar(raw_value: str) -> Any:
    """Parse a JSON scalar with a string fallback."""

    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise click.ClickException("Runtime-variable values must be JSON scalars.")
    return value


def _workspace_for_store(store: InstanceStateStore) -> PrivateWorkspace:
    """Resolve one instance state's associated private workspace."""

    association = store.private_workspace_association()
    if association is None:
        raise click.ClickException("This managed-agent instance has no active private workspace.")
    return PrivateWorkspace(Path(association["workspace_root"]))


def _build_workspace_group(
    store_factory: Callable[[], InstanceStateStore], *, mutable: bool
) -> click.Group:
    """Build actor-scoped private-workspace operations."""

    @click.group(name="workspace")
    def workspace_group() -> None:
        """Resolve semantic private-workspace paths."""

    @workspace_group.command(name="inspect")
    def inspect_workspace() -> None:
        """Inspect stable topology and mutable index health."""

        try:
            store = store_factory()
            workspace = _workspace_for_store(store)
            emit(
                {
                    "root": str(workspace.root),
                    "manifest": workspace.load_manifest().model_dump(mode="json"),
                    "validation": workspace.validate(),
                }
            )
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    @workspace_group.command(name="resolve")
    @click.argument("label")
    def resolve_workspace_path(label: str) -> None:
        """Resolve one semantic label to its current confined path."""

        try:
            workspace = _workspace_for_store(store_factory())
            emit({"label": label, "path": str(workspace.resolve(label))})
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    if mutable:

        @workspace_group.command(name="validate")
        def validate_workspace() -> None:
            """Cross-validate the manifest, index, bindings, and payloads."""

            try:
                emit(_workspace_for_store(store_factory()).validate())
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc

        @workspace_group.command(name="doctor")
        def doctor_workspace() -> None:
            """Report private-workspace drift without changing content."""

            try:
                report = _workspace_for_store(store_factory()).validate()
            except (OSError, ValueError) as exc:
                emit({"healthy": False, "error": str(exc)})
                return
            emit({"healthy": bool(report["valid"]), "report": report})

        @workspace_group.command(name="remap")
        @click.argument("label")
        @click.argument("relative_path")
        @click.option("--expected-generation", type=click.IntRange(min=1), required=True)
        def remap_workspace(label: str, relative_path: str, expected_generation: int) -> None:
            """Optimistically remap one existing semantic label."""

            try:
                emit(
                    _workspace_for_store(store_factory()).remap(
                        label=label,
                        relative_path=relative_path,
                        expected_generation=expected_generation,
                    )
                )
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc

        @workspace_group.command(name="materialize")
        @click.argument("label")
        def materialize_workspace_path(label: str) -> None:
            """Materialize one declared semantic file or directory."""

            try:
                path = _workspace_for_store(store_factory()).materialize(label)
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
            emit({"label": label, "path": str(path)})

        @workspace_group.command(name="tracking")
        @click.argument("posture", type=click.Choice(("local-untracked", "tracked-permitted")))
        def set_workspace_tracking(posture: str) -> None:
            """Change tracking permission without staging or committing."""

            try:
                manifest = _workspace_for_store(store_factory()).set_tracking_posture(
                    posture  # type: ignore[arg-type]
                )
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
            emit({"tracking_posture": manifest.tracking_posture})

        @workspace_group.command(name="project-mindset")
        @click.argument("mindset_name")
        @click.option("--label", required=True)
        def project_workspace_mindset(mindset_name: str, label: str) -> None:
            """Publish one immutable canonical mindset revision into the workspace."""

            try:
                store = store_factory()
                emit(
                    _workspace_for_store(store).project_mindset(
                        state_store=store,
                        mindset_name=mindset_name,
                        semantic_label=label,
                    )
                )
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc

        @workspace_group.command(name="cleanup")
        @click.option("--confirm", is_flag=True, help="Confirm irreversible content deletion.")
        def cleanup_workspace(confirm: bool) -> None:
            """Delete one drift-free owned private workspace."""

            try:
                store = store_factory()
                workspace = _workspace_for_store(store)
                workspace_id = workspace.load_manifest().workspace_id
                result = workspace.cleanup(confirmed=confirm)
                store.clear_private_workspace_association(expected_workspace_id=workspace_id)
                emit({**result, "association_removed": True})
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc

    return workspace_group


def _build_variables_group(
    store_factory: Callable[[], InstanceStateStore], *, mutable: bool
) -> click.Group:
    """Build one actor-scoped runtime-variable command group."""

    @click.group(name="variables")
    def variables_group() -> None:
        """Inspect revisioned Agent Runtime Variables."""

    @variables_group.command(name="list")
    def list_variables() -> None:
        """List current values and revisions."""

        emit({"runtime_variables": store_factory().runtime_variables()})

    @variables_group.command(name="get")
    @click.argument("key")
    def get_variable(key: str) -> None:
        """Get one current value and revision."""

        try:
            emit(store_factory().runtime_variable(key))
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    @variables_group.command(name="explain")
    @click.argument("key")
    def explain_variable(key: str) -> None:
        """Show one declaration, value, and revision."""

        try:
            item = store_factory().runtime_variable(key)
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        emit(
            {
                "key": key,
                "revision": item["revision"],
                "value": item["value"],
                "declaration": item["declaration"],
                "authority": "non-secret behavior data",
            }
        )

    if mutable:

        @variables_group.command(name="set")
        @click.argument("key")
        @click.option("--value", required=True)
        @click.option("--expected-revision", type=click.IntRange(min=1), required=True)
        def set_variable(key: str, value: str, expected_revision: int) -> None:
            """Compare-and-set one explicit instance value."""

            try:
                payload = store_factory().mutate_runtime_variable(
                    key=key,
                    value=_parse_scalar(value),
                    expected_revision=expected_revision,
                    actor="operator",
                )
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
            emit(payload)

    return variables_group


def _build_mindsets_group(
    store_factory: Callable[[], InstanceStateStore], *, mutable: bool
) -> click.Group:
    """Build one actor-scoped mindset command group."""

    @click.group(name="mindsets")
    def mindsets_group() -> None:
        """Inspect named low-authority Agent Mindsets."""

    @mindsets_group.command(name="get")
    @click.argument("name")
    def get_mindset(name: str) -> None:
        """Get one named mindset record."""

        try:
            emit(store_factory().mindset(name))
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    @mindsets_group.command(name="snapshot")
    @click.option("--skill", "skill_name", required=True)
    def snapshot_mindsets(skill_name: str) -> None:
        """Snapshot all current mindsets required by one static skill."""

        try:
            emit(store_factory().mindset_snapshot_for_skill(skill_name))
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    if mutable:

        @mindsets_group.command(name="set")
        @click.argument("name")
        @click.option(
            "--record-file",
            required=True,
            type=click.Path(path_type=Path, exists=True, dir_okay=False),
        )
        @click.option("--expected-revision", type=click.IntRange(min=1), required=True)
        def set_mindset(name: str, record_file: Path, expected_revision: int) -> None:
            """Compare-and-set one explicit named mindset."""

            try:
                raw_record = json.loads(record_file.read_text(encoding="utf-8"))
                if not isinstance(raw_record, dict):
                    raise ValueError("Mindset record file must contain one JSON object.")
                payload = store_factory().mutate_mindset(
                    name=name,
                    record=raw_record,
                    expected_revision=expected_revision,
                    actor="operator",
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise click.ClickException(str(exc)) from exc
            emit(payload)

    return mindsets_group


@click.group(name="instance-state")
def self_instance_state_group() -> None:
    """Read verified-self runtime variables and mindset snapshots."""


self_instance_state_group.add_command(_build_variables_group(_self_store, mutable=False))
self_instance_state_group.add_command(_build_mindsets_group(_self_store, mutable=False))
self_instance_state_group.add_command(_build_workspace_group(_self_store, mutable=False))


@click.group(name="instance-state")
def admin_instance_state_group() -> None:
    """Inspect or revise one explicitly selected instance."""


admin_instance_state_group.add_command(_build_variables_group(_admin_store, mutable=True))
admin_instance_state_group.add_command(_build_mindsets_group(_admin_store, mutable=True))
admin_instance_state_group.add_command(_build_workspace_group(_admin_store, mutable=True))


@admin_instance_state_group.command(name="migrate")
def migrate_admin_state() -> None:
    """Run the maintained explicit instance-state migration check."""

    try:
        emit(migrate_instance_state(_admin_store().path))
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


__all__ = ["admin_instance_state_group", "self_instance_state_group"]
