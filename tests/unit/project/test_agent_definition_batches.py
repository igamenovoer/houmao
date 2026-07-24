"""Tests for bounded all-or-nothing Agent Definition batch deployment."""

from __future__ import annotations

from pathlib import Path

import pytest

from houmao.project import agent_definition_batches
from houmao.project.agent_definition_batches import (
    BatchDelegation,
    apply_batch_deployment,
    create_batch_request,
    doctor_batch_operations,
    inspect_batch_operation,
    plan_batch_deployment,
)
from houmao.project.agent_definitions import (
    DeployBinding,
    DeployInput,
    MaterializationSpec,
    approve_derivation,
    derive_intent,
    init_intent,
    materialize_revision,
)
from houmao.project.catalog import ProjectCatalog
from houmao.project.overlay import HoumaoProjectOverlay, bootstrap_project_overlay_at_root


def _revision(tmp_path: Path) -> Path:
    """Author one minimal reusable revision."""

    workspace = init_intent(
        tmp_path / "authoring",
        overview_text="Use [role](role.md) and [memo](memo.md).\n",
    )
    (workspace.source_root / "role.md").write_text(
        "Objective: {{houmao.deploy.objective}}\n", encoding="utf-8"
    )
    (workspace.source_root / "memo.md").write_text("# Memo\n", encoding="utf-8")
    derive_intent(
        workspace,
        interpretation_text="Create reviewers.",
        materialization=MaterializationSpec(
            definition_id="batch-reviewer",
            revision_id="1",
            purpose="Review changes.",
            role_prompt_source="role.md",
            memo_seed_source="memo.md",
            role_prompt="materials/prompts/system.md",
            memo_seed="materials/memo/houmao-memo.md",
            deploy_inputs=(
                DeployInput(
                    key="objective",
                    bindings=(
                        DeployBinding(
                            target="role_prompt",
                            mode="text",
                            marker="{{houmao.deploy.objective}}",
                        ),
                    ),
                ),
            ),
        ),
    )
    approve_derivation(workspace, approved_by="operator")
    return materialize_revision(workspace).root


def _project(tmp_path: Path) -> HoumaoProjectOverlay:
    """Create one project with an existing compatible credential reference."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    overlay = bootstrap_project_overlay_at_root(project_root / ".houmao").project_overlay
    auth = tmp_path / "auth"
    auth.mkdir()
    (auth / "credentials.json").write_text("{}", encoding="utf-8")
    ProjectCatalog.from_overlay(overlay).create_auth_profile_from_source(
        tool="claude",
        display_name="credential",
        source_path=auth,
    )
    return overlay


def _plan(tmp_path: Path) -> tuple[HoumaoProjectOverlay, Path]:
    """Create a three-member delegated-name batch plan."""

    revision = _revision(tmp_path)
    overlay = _project(tmp_path)
    request = create_batch_request(
        revision_root=revision,
        overlay=overlay,
        count=3,
        shared_values={"objective": "Inspect the patch"},
        workdir=".",
        tool="claude",
        credential="credential",
        name_prefix="reviewer",
        delegation=BatchDelegation(names=True),
    )
    _, plan_root = plan_batch_deployment(request, overlay=overlay)
    return overlay, plan_root


def test_batch_apply_creates_ordinary_members_with_operation_provenance(
    tmp_path: Path,
) -> None:
    """Successful apply returns handoffs and correlates otherwise independent rows."""

    overlay, plan_root = _plan(tmp_path)
    result = apply_batch_deployment(plan_root, overlay=overlay)
    operation = inspect_batch_operation(plan_root, overlay=overlay)

    assert result["member_count"] == 3
    assert result["launched"] is False
    assert all(not item["launched"] for item in result["launch_handoffs"])
    assert [item["batch_member_ordinal"] for item in operation["visible_members"]] == [
        1,
        2,
        3,
    ]
    assert operation["durable_batch_entity"] is False


def test_batch_without_name_delegation_requires_fixed_names(tmp_path: Path) -> None:
    """Plural quantity alone does not authorize generated selections."""

    revision = _revision(tmp_path)
    overlay = _project(tmp_path)
    request = create_batch_request(
        revision_root=revision,
        overlay=overlay,
        count=2,
        shared_values={"objective": "Inspect"},
        tool="claude",
        credential="credential",
        delegation=BatchDelegation(),
    )
    with pytest.raises(ValueError, match="delegated name"):
        plan_batch_deployment(request, overlay=overlay)


def test_batch_catalog_commit_rolls_back_all_members_on_late_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late insert failure leaves no Agent Deployment member visible."""

    overlay, plan_root = _plan(tmp_path)
    original = agent_definition_batches._register_agent_deployment
    calls = 0

    def fail_second(*args: object, **kwargs: object) -> str:
        """Inject failure after one row has entered the still-open transaction."""

        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected late member failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        agent_definition_batches,
        "_register_agent_deployment",
        fail_second,
    )
    with pytest.raises(RuntimeError, match="injected"):
        apply_batch_deployment(plan_root, overlay=overlay)

    catalog = ProjectCatalog.from_overlay(overlay)
    with pytest.raises(FileNotFoundError):
        catalog.load_launch_profile("reviewer-01")
    with pytest.raises(FileNotFoundError):
        catalog.load_specialist("reviewer-01")
    assert inspect_batch_operation(plan_root, overlay=overlay)["visible_members"] == []


def test_batch_doctor_finishes_postcommit_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doctor completes projection after an injected postcommit failure."""

    overlay, plan_root = _plan(tmp_path)
    original = ProjectCatalog.materialize_projection
    calls = 0

    def fail_once(self: ProjectCatalog) -> object:
        """Fail the first projection after the catalog transaction commits."""

        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected projection failure")
        return original(self)

    monkeypatch.setattr(ProjectCatalog, "materialize_projection", fail_once)
    with pytest.raises(RuntimeError, match="injected projection"):
        apply_batch_deployment(plan_root, overlay=overlay)

    operation = inspect_batch_operation(plan_root, overlay=overlay)
    assert len(operation["visible_members"]) == 3
    report = doctor_batch_operations(overlay)

    assert report["healthy"] is True
    assert any(item["code"] == "recovered-publication" for item in report["findings"])
    assert inspect_batch_operation(plan_root, overlay=overlay)["state"] == "applied"
