"""Tests for private per-instance workspace contracts and operations."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from houmao.agents.instance_state import InstanceStateStore, prepare_instance_state
from houmao.agents.private_workspace import PrivateWorkspace, prepare_private_workspace
from houmao.project.agent_definitions import (
    InstanceContract,
    MindsetContract,
    MindsetQuestionContract,
    PrivateWorkspaceContract,
    WorkspaceDirectoryContract,
)


def _contract() -> InstanceContract:
    """Return an instance contract with auxiliary private storage."""

    return InstanceContract(
        mindsets=(
            MindsetContract(
                name="review",
                expose_in_private_workspace=True,
                questions=(
                    MindsetQuestionContract(
                        question_id="risk",
                        text="What risk needs the most attention?",
                    ),
                ),
            ),
        ),
        private_workspace=PrivateWorkspaceContract(
            mode="optional",
            default_enabled=True,
            workdir_mode="project-root",
            directories=(
                WorkspaceDirectoryContract(
                    key="workspace.artifacts",
                    default_path="artifacts",
                ),
                WorkspaceDirectoryContract(
                    key="workspace.mindsets",
                    default_path="mindsets",
                ),
            ),
        ),
    )


def _prepare(tmp_path: Path) -> tuple[PrivateWorkspace, InstanceStateStore, Path]:
    """Prepare one Git-backed private workspace."""

    project_root = tmp_path / "project"
    project_root.mkdir()
    subprocess.run(["git", "init", "-q", str(project_root)], check=True)
    state_path = project_root / ".houmao" / "memory" / "agents" / "agent-a" / "state.sqlite"
    contract = _contract()
    prepare_instance_state(
        state_db=state_path,
        agent_id="agent-a",
        deployment_id="deployment-a",
        instance_contract_digest="sha256:instance",
        contract=contract,
        launch_values={},
    )
    store = InstanceStateStore(state_path)
    prepared = prepare_private_workspace(
        project_root=project_root,
        agent_id="agent-a",
        deployment_id="deployment-a",
        definition_id="reviewer",
        contract=contract.private_workspace,
        enabled=True,
        workdir_mode="project-root",
        state_store=store,
    )
    assert prepared is not None
    assert prepared.execution_workdir == project_root
    return PrivateWorkspace(prepared.root), store, project_root


def test_workspace_manifest_stays_stable_while_index_grows(tmp_path: Path) -> None:
    """Indexed projections do not add mutable generation or digests to TOML."""

    workspace, store, project_root = _prepare(tmp_path)
    manifest_before = workspace.manifest_path.read_text(encoding="utf-8")

    projection = workspace.project_mindset(
        state_store=store,
        mindset_name="review",
        semantic_label="workspace.mindsets",
    )
    manifest_after = workspace.manifest_path.read_text(encoding="utf-8")

    assert manifest_before == manifest_after
    assert "generation" not in manifest_after
    assert "database_digest" not in manifest_after
    assert Path(projection["path"]).is_file()
    assert workspace.validate()["valid"] is True
    ignored = subprocess.run(
        ["git", "-C", str(project_root), "check-ignore", "-q", str(workspace.root)],
        check=False,
    )
    assert ignored.returncode == 0


def test_workspace_remap_is_confined_and_generation_checked(tmp_path: Path) -> None:
    """Admin remapping preserves labels and rejects traversal or stale generation."""

    workspace, _, _ = _prepare(tmp_path)
    changed = workspace.remap(
        label="workspace.artifacts",
        relative_path="private/output",
        expected_generation=1,
    )

    assert changed["generation"] == 2
    assert workspace.resolve("workspace.artifacts") == workspace.root / "private" / "output"
    with pytest.raises(ValueError, match="Stale"):
        workspace.remap(
            label="workspace.artifacts",
            relative_path="other",
            expected_generation=1,
        )
    with pytest.raises(ValueError, match="relative"):
        workspace.remap(
            label="workspace.artifacts",
            relative_path="../escape",
            expected_generation=2,
        )


def test_tracking_transition_and_drift_checked_cleanup(tmp_path: Path) -> None:
    """Tracking opt-in removes only owned exclude state and cleanup preserves user files."""

    workspace, _, project_root = _prepare(tmp_path)
    workspace.set_tracking_posture("tracked-permitted")
    exclude = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--git-path", "info/exclude"],
        check=True,
        capture_output=True,
        text=True,
    )
    exclude_path = Path(exclude.stdout.strip())
    if not exclude_path.is_absolute():
        exclude_path = project_root / exclude_path
    assert workspace.load_manifest().tracking_posture == "tracked-permitted"
    assert workspace.load_manifest().workspace_id not in exclude_path.read_text(encoding="utf-8")

    user_file = workspace.resolve("workspace.artifacts") / "user.txt"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text("preserve me", encoding="utf-8")
    with pytest.raises(ValueError, match="unowned"):
        workspace.cleanup(confirmed=True)
    assert user_file.read_text(encoding="utf-8") == "preserve me"

    user_file.unlink()
    result = workspace.cleanup(confirmed=True)
    assert result["recoverable"] is False
    assert not workspace.root.exists()


def test_manifest_rejects_mutable_inventory_fields(tmp_path: Path) -> None:
    """Strict TOML validation rejects mutable index state."""

    workspace, _, _ = _prepare(tmp_path)
    payload = workspace.manifest_path.read_text(encoding="utf-8")
    workspace.manifest_path.write_text(
        payload + '\ndatabase_digest = "sha256:mutable"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="database_digest"):
        workspace.load_manifest()


def test_cleanup_rejects_tracked_workspace_content(tmp_path: Path) -> None:
    """Confirmed cleanup preserves workspace files that Git already tracks."""

    workspace, _, project_root = _prepare(tmp_path)
    workspace.set_tracking_posture("tracked-permitted")
    subprocess.run(
        ["git", "-C", str(project_root), "add", str(workspace.manifest_path)],
        check=True,
    )

    with pytest.raises(ValueError, match="tracked repository content"):
        workspace.cleanup(confirmed=True)
    assert workspace.manifest_path.is_file()
