"""Tests for Agent Definition authoring and single-deployment lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from houmao.project.agent_definitions import (
    AgentDefinitionWorkspace,
    DeployBinding,
    DeployInput,
    MaterializationSpec,
    apply_deployment,
    approve_derivation,
    create_deployment_request,
    derive_intent,
    doctor_agent_deployments,
    init_intent,
    inspect_agent_deployment,
    materialize_revision,
    plan_deployment,
    remove_agent_deployment,
    validate_revision,
)
from houmao.agents.instance_state import prepare_instance_state
from houmao.project.catalog import ProjectCatalog
from houmao.project.overlay import bootstrap_project_overlay_at_root


def _author_revision(tmp_path: Path) -> Path:
    """Create one validating revision through the complete authoring lifecycle."""

    workspace_root = tmp_path / "authoring"
    overview = "# Reviewer\n\nUse [the role prompt](role.md) and [memo seed](memo.md).\n"
    workspace = init_intent(workspace_root, overview_text=overview)
    (workspace.source_root / "role.md").write_text(
        "Review this objective: {{houmao.deploy.task_objective}}\n", encoding="utf-8"
    )
    (workspace.source_root / "memo.md").write_text("# Working Memory\n", encoding="utf-8")
    skill = tmp_path / "skills" / "review-checklist"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: review-checklist\ndescription: Review a change.\n---\n\n# Review\n",
        encoding="utf-8",
    )
    spec = MaterializationSpec(
        definition_id="repository-reviewer",
        revision_id="1.0.0",
        purpose="Review repository changes.",
        role_prompt_source="role.md",
        memo_seed_source="memo.md",
        role_prompt="materials/prompts/system.md",
        memo_seed="materials/memo/houmao-memo.md",
        skills=("materials/skills/review-checklist",),
        deploy_inputs=(
            DeployInput(
                key="task_objective",
                bindings=(
                    DeployBinding(
                        target="role_prompt",
                        mode="text",
                        marker="{{houmao.deploy.task_objective}}",
                    ),
                ),
            ),
        ),
    )
    derive_intent(
        workspace,
        interpretation_text="# Interpretation\n\nA repository reviewer.\n",
        materialization=spec,
        source_skill_roots=(skill,),
    )
    approve_derivation(workspace, approved_by="test-operator")
    materialize_revision(workspace)
    return workspace.definition_root


def test_authoring_is_digest_bound_and_revision_is_portable(tmp_path: Path) -> None:
    """Materialization copies skills and rejects a stale source approval."""

    definition_root = _author_revision(tmp_path)
    revision = validate_revision(definition_root)

    assert revision.definition.definition_id == "repository-reviewer"
    assert revision.revision_digest.startswith("sha256:")
    assert (definition_root / "assets" / "skills" / "review-checklist" / "SKILL.md").is_file()

    workspace = AgentDefinitionWorkspace(tmp_path / "authoring")
    (workspace.source_root / "role.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        materialize_revision(workspace, output_root=tmp_path / "second")


def test_overview_references_are_confined(tmp_path: Path) -> None:
    """The source set cannot escape the authoring source root."""

    workspace = init_intent(
        tmp_path / "authoring",
        overview_text="[outside](../outside.md)\n",
    )
    (workspace.root / "intent" / "outside.md").write_text("outside", encoding="utf-8")
    with pytest.raises(ValueError, match="remain beneath"):
        derive_intent(
            workspace,
            interpretation_text="unsafe",
            materialization=MaterializationSpec(
                definition_id="unsafe",
                revision_id="1",
                purpose="Unsafe",
                role_prompt_source="../outside.md",
                memo_seed_source="../outside.md",
                role_prompt="materials/prompts/system.md",
                memo_seed="materials/memo/houmao-memo.md",
            ),
        )


def test_packaged_reference_revision_validates() -> None:
    """The built-in reference definition is portable and digest-valid."""

    revision = validate_revision(Path("builtin:reference-reviewer"))

    assert revision.definition.definition_id == "reference-reviewer"
    assert revision.definition.revision_id == "1.0.0"
    assert revision.instance_contract.runtime_variables[0].key == "review_depth"
    assert revision.instance_contract.mindsets[0].name == "review-quality"
    assert revision.instance_contract.private_workspace.mode == "optional"


def test_plan_apply_and_remove_one_deployment(tmp_path: Path) -> None:
    """A plan applies once, returns a launch command, and preserves credentials."""

    definition_root = _author_revision(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    overlay = bootstrap_project_overlay_at_root(project_root / ".houmao").project_overlay
    auth_source = tmp_path / "auth"
    auth_source.mkdir()
    (auth_source / "credentials.json").write_text("{}", encoding="utf-8")
    ProjectCatalog.from_overlay(overlay).create_auth_profile_from_source(
        tool="claude",
        display_name="test-credential",
        source_path=auth_source,
    )
    request = create_deployment_request(
        revision_root=definition_root,
        overlay=overlay,
        deployment_name="reviewer",
        specialist_name="reviewer",
        profile_name="reviewer",
        tool="claude",
        credential="test-credential",
        workdir=".",
        values={"task_objective": "Check the patch"},
        setup="default",
    )
    plan, plan_root = plan_deployment(request, overlay=overlay)

    assert not plan.blockers
    assert "Check the patch" in (plan_root / "rendered" / "prompts" / "system.md").read_text(
        encoding="utf-8"
    )
    result = apply_deployment(plan_root, overlay=overlay)
    deployment = inspect_agent_deployment(overlay, "reviewer")

    assert result["launched"] is False
    assert "project agents launch --profile reviewer" in result["launch_command"]
    assert deployment["revision_digest"] == plan.revision_digest

    removed = remove_agent_deployment(overlay, "reviewer")
    assert removed["credentials_preserved"] is True
    assert (
        ProjectCatalog.from_overlay(overlay).load_auth_profile(
            tool="claude", name="test-credential"
        )
        is not None
    )


def test_registered_skill_cache_is_reused_by_content_digest(tmp_path: Path) -> None:
    """Deployments share one immutable project-contained skill cache object."""

    definition_root = _author_revision(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    overlay = bootstrap_project_overlay_at_root(project_root / ".houmao").project_overlay
    auth_source = tmp_path / "auth"
    auth_source.mkdir()
    (auth_source / "credentials.json").write_text("{}", encoding="utf-8")
    catalog = ProjectCatalog.from_overlay(overlay)
    catalog.create_auth_profile_from_source(
        tool="claude",
        display_name="test-credential",
        source_path=auth_source,
    )
    for suffix in ("one", "two"):
        request = create_deployment_request(
            revision_root=definition_root,
            overlay=overlay,
            deployment_name=f"reviewer-{suffix}",
            specialist_name=f"reviewer-{suffix}",
            profile_name=f"reviewer-{suffix}",
            tool="claude",
            credential="test-credential",
            workdir=".",
            values={"task_objective": f"Check patch {suffix}"},
        )
        _, plan_root = plan_deployment(request, overlay=overlay)
        apply_deployment(plan_root, overlay=overlay)

    skill = catalog.load_project_skill("review-checklist")
    cache_entries = list((overlay.content_root / "agent-definition-skill-cache").iterdir())

    assert skill.mode == "symlink"
    assert skill.source_path == cache_entries[0]
    assert len(cache_entries) == 1
    remove_agent_deployment(overlay, "reviewer-one")
    remove_agent_deployment(overlay, "reviewer-two")
    assert cache_entries[0].is_dir()


def test_update_preserves_deployment_identity_and_remove_checks_instance_state(
    tmp_path: Path,
) -> None:
    """Updates keep the deployment id and removal scans preserved state."""

    definition_root = _author_revision(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    overlay = bootstrap_project_overlay_at_root(project_root / ".houmao").project_overlay
    auth_source = tmp_path / "auth"
    auth_source.mkdir()
    (auth_source / "credentials.json").write_text("{}", encoding="utf-8")
    ProjectCatalog.from_overlay(overlay).create_auth_profile_from_source(
        tool="claude",
        display_name="test-credential",
        source_path=auth_source,
    )
    initial_request = create_deployment_request(
        revision_root=definition_root,
        overlay=overlay,
        deployment_name="reviewer",
        specialist_name="reviewer-v1",
        profile_name="reviewer-v1",
        tool="claude",
        credential="test-credential",
        workdir=".",
        values={"task_objective": "Check the patch"},
    )
    _, initial_plan_root = plan_deployment(initial_request, overlay=overlay)
    initial_result = apply_deployment(initial_plan_root, overlay=overlay)

    update_request = create_deployment_request(
        revision_root=definition_root,
        overlay=overlay,
        deployment_name="reviewer",
        specialist_name="reviewer-v2",
        profile_name="reviewer-v2",
        tool="claude",
        credential="test-credential",
        workdir=".",
        values={"task_objective": "Check the updated patch"},
        update_existing=True,
    )
    update_plan, update_plan_root = plan_deployment(update_request, overlay=overlay)
    assert not update_plan.blockers
    updated_result = apply_deployment(update_plan_root, overlay=overlay)

    assert updated_result["deployment_id"] == initial_result["deployment_id"]
    assert inspect_agent_deployment(overlay, "reviewer")["profile_name"] == "reviewer-v2"

    state_path = overlay.memory_root / "agents" / "agent-1" / "state.sqlite"
    revision = validate_revision(definition_root)
    prepare_instance_state(
        state_db=state_path,
        agent_id="agent-1",
        deployment_id=str(updated_result["deployment_id"]),
        instance_contract_digest=revision.instance_contract_digest,
        contract=revision.instance_contract,
        launch_values={},
    )
    with pytest.raises(ValueError, match="referenced"):
        remove_agent_deployment(overlay, "reviewer")

    state_path.unlink()
    remove_agent_deployment(overlay, "reviewer")


def test_revision_rejects_secret_assignments_in_markdown(tmp_path: Path) -> None:
    """Portable prompt and skill text cannot embed credential-secret values."""

    definition_root = _author_revision(tmp_path)
    prompt_path = definition_root / "assets" / "prompts" / "system.md"
    prompt_path.write_text("api_key: embedded-value\n", encoding="utf-8")

    with pytest.raises(ValueError, match="credential-secret"):
        validate_revision(definition_root)


def test_plan_blocks_missing_credential_reference(tmp_path: Path) -> None:
    """Planning reports a missing tool-scoped credential before apply."""

    definition_root = _author_revision(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    overlay = bootstrap_project_overlay_at_root(project_root / ".houmao").project_overlay
    request = create_deployment_request(
        revision_root=definition_root,
        overlay=overlay,
        deployment_name="reviewer",
        specialist_name="reviewer",
        profile_name="reviewer",
        tool="claude",
        credential="missing",
        workdir=".",
        values={"task_objective": "Check the patch"},
    )

    plan, _ = plan_deployment(request, overlay=overlay)

    assert any("not an existing compatible" in blocker for blocker in plan.blockers)


def test_doctor_recovers_single_postcommit_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A projection failure after catalog commit remains recoverable by doctor."""

    definition_root = _author_revision(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    overlay = bootstrap_project_overlay_at_root(project_root / ".houmao").project_overlay
    auth_source = tmp_path / "auth"
    auth_source.mkdir()
    (auth_source / "credentials.json").write_text("{}", encoding="utf-8")
    ProjectCatalog.from_overlay(overlay).create_auth_profile_from_source(
        tool="claude",
        display_name="test-credential",
        source_path=auth_source,
    )
    request = create_deployment_request(
        revision_root=definition_root,
        overlay=overlay,
        deployment_name="reviewer",
        specialist_name="reviewer",
        profile_name="reviewer",
        tool="claude",
        credential="test-credential",
        workdir=".",
        values={"task_objective": "Check the patch"},
    )
    _, plan_root = plan_deployment(request, overlay=overlay)
    original = ProjectCatalog.materialize_projection
    calls = 0

    def fail_once(self: ProjectCatalog) -> Path:
        """Fail only the publication attempt that follows catalog commit."""

        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected projection failure")
        return original(self)

    monkeypatch.setattr(ProjectCatalog, "materialize_projection", fail_once)
    with pytest.raises(RuntimeError, match="injected projection"):
        apply_deployment(plan_root, overlay=overlay)

    assert inspect_agent_deployment(overlay, "reviewer")["plan_path"] == str(plan_root)
    report = doctor_agent_deployments(overlay)

    assert report["healthy"] is True
    assert any(item["code"] == "recovered-publication" for item in report["findings"])


def test_doctor_distinguishes_source_and_output_drift(tmp_path: Path) -> None:
    """Doctor labels immutable source drift separately from rendered output drift."""

    definition_root = _author_revision(tmp_path)
    project_root = tmp_path / "project"
    project_root.mkdir()
    overlay = bootstrap_project_overlay_at_root(project_root / ".houmao").project_overlay
    auth_source = tmp_path / "auth"
    auth_source.mkdir()
    (auth_source / "credentials.json").write_text("{}", encoding="utf-8")
    ProjectCatalog.from_overlay(overlay).create_auth_profile_from_source(
        tool="claude",
        display_name="test-credential",
        source_path=auth_source,
    )
    request = create_deployment_request(
        revision_root=definition_root,
        overlay=overlay,
        deployment_name="reviewer",
        specialist_name="reviewer",
        profile_name="reviewer",
        tool="claude",
        credential="test-credential",
        workdir=".",
        values={"task_objective": "Check the patch"},
    )
    _, plan_root = plan_deployment(request, overlay=overlay)
    apply_deployment(plan_root, overlay=overlay)
    source_prompt = definition_root / "assets" / "prompts" / "system.md"
    original_prompt = source_prompt.read_text(encoding="utf-8")
    source_prompt.write_text(original_prompt + "\nchanged\n", encoding="utf-8")

    source_report = doctor_agent_deployments(overlay)

    assert any(item["code"] == "source-drift" for item in source_report["findings"])
    source_prompt.write_text(original_prompt, encoding="utf-8")
    rendered_prompt = plan_root / "rendered" / "prompts" / "system.md"
    rendered_prompt.write_text("changed output\n", encoding="utf-8")

    output_report = doctor_agent_deployments(overlay)

    assert any(item["code"] == "output-drift" for item in output_report["findings"])
    with pytest.raises(ValueError, match="drift"):
        remove_agent_deployment(overlay, "reviewer")
