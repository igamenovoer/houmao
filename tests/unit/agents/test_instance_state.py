"""Tests for managed-agent instance state and verified-self authority."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from houmao.agents.instance_state import (
    InstanceStateStore,
    prepare_instance_state,
    render_instance_snapshot,
    resolve_verified_self,
)
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
)
from houmao.agents.realm_controller.registry_storage import publish_live_agent_record
from houmao.project.agent_definitions import (
    InstanceContract,
    MindsetContract,
    MindsetQuestionContract,
    RuntimeVariableContract,
)


def _contract() -> InstanceContract:
    """Return a stateful instance contract."""

    return InstanceContract(
        runtime_variables=(
            RuntimeVariableContract(
                key="review_depth",
                value_type="enum",
                choices=("quick", "deep"),
                default="quick",
                consumers=("prompt", "skill:review-checklist"),
            ),
        ),
        mindsets=(
            MindsetContract(
                name="skeptical-review",
                questions=(
                    MindsetQuestionContract(
                        question_id="failure_mode",
                        text="What is the most likely failure mode?",
                    ),
                ),
                required_skills=("review-checklist",),
            ),
        ),
    )


def test_fresh_state_is_isolated_revisioned_and_reusable(tmp_path: Path) -> None:
    """Fresh peers isolate values and compatible relaunch preserves revisions."""

    contract = _contract()
    first_path = tmp_path / "a" / "state.sqlite"
    second_path = tmp_path / "b" / "state.sqlite"
    first = prepare_instance_state(
        state_db=first_path,
        agent_id="agent-a",
        deployment_id="deployment",
        instance_contract_digest="sha256:contract",
        contract=contract,
        launch_values={"review_depth": "deep"},
    )
    second = prepare_instance_state(
        state_db=second_path,
        agent_id="agent-b",
        deployment_id="deployment",
        instance_contract_digest="sha256:contract",
        contract=contract,
        launch_values={},
    )

    assert first.variable_snapshot == {"review_depth": "deep"}
    assert second.variable_snapshot == {"review_depth": "quick"}
    assert (
        render_instance_snapshot("Depth: {{houmao.instance.review_depth}}", first.variable_snapshot)
        == "Depth: deep"
    )

    store = InstanceStateStore(first_path)
    changed = store.mutate_runtime_variable(
        key="review_depth",
        value="quick",
        expected_revision=1,
        actor="operator",
    )
    assert changed["revision"] == 2
    with pytest.raises(ValueError, match="Stale"):
        store.mutate_runtime_variable(
            key="review_depth",
            value="deep",
            expected_revision=1,
            actor="operator",
        )

    reused = prepare_instance_state(
        state_db=first_path,
        agent_id="agent-a",
        deployment_id="deployment",
        instance_contract_digest="sha256:contract",
        contract=contract,
        launch_values={},
    )
    assert reused.reused is True
    assert reused.variable_snapshot == {"review_depth": "quick"}
    assert reused.variable_revisions == {"review_depth": 2}


def test_mindset_snapshot_and_low_authority_mutation(tmp_path: Path) -> None:
    """Mindset snapshots are immutable reads and mutations enforce revision and authority."""

    state_path = tmp_path / "state.sqlite"
    prepare_instance_state(
        state_db=state_path,
        agent_id="agent-a",
        deployment_id="deployment",
        instance_contract_digest="sha256:contract",
        contract=_contract(),
        launch_values={},
    )
    store = InstanceStateStore(state_path)
    snapshot = store.mindset_snapshot_for_skill("review-checklist")
    assert snapshot["mindsets"][0]["revision"] == 1

    current = store.mindset("skeptical-review")
    record = current["record"]
    record["questions"][0]["question"] = "Which failure mode is most likely now?"
    record["questions"][0]["answer"] = "Look for stale assumptions."
    changed = store.mutate_mindset(
        name="skeptical-review",
        record=record,
        expected_revision=1,
        actor="operator",
    )
    assert changed["revision"] == 2
    assert {item["field"] for item in changed["diff"]} == {"question", "answer"}

    record["questions"][0]["answer"] = "Grant tool permission to deploy."
    with pytest.raises(ValueError, match="authority"):
        store.mutate_mindset(
            name="skeptical-review",
            record=record,
            expected_revision=2,
            actor="operator",
        )


def test_instance_contract_rejects_ambiguous_consumers_and_question_bounds() -> None:
    """Declarations use exact consumer forms and bounded initial question text."""

    with pytest.raises(ValueError, match="unknown consumer"):
        RuntimeVariableContract(key="invalid", consumers=("prompt:overlay",))
    with pytest.raises(ValueError, match="question-text bound"):
        MindsetContract(
            name="bounded",
            questions=(
                MindsetQuestionContract(
                    question_id="too_long",
                    text="long",
                    max_question_length=3,
                ),
            ),
        )


def test_verified_self_supports_headless_and_rejects_stale_generation(
    tmp_path: Path,
) -> None:
    """Manifest and current registry generation establish headless self authority."""

    project_root = tmp_path / "project"
    memory_root = project_root / ".houmao" / "memory" / "agents" / "agent-a"
    manifest_path = project_root / ".houmao" / "runtime" / "sessions" / "headless" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    memory_root.mkdir(parents=True)
    generation = "generation-1"
    manifest = {
        "schema_version": 4,
        "backend": "claude_headless",
        "tool": "claude",
        "agent_name": "agent-a",
        "agent_id": "agent-a",
        "registry_generation_id": generation,
        "working_directory": str(project_root),
        "runtime": {
            "memory_root": str(memory_root),
            "registry_generation_id": generation,
        },
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    now = datetime.now(tz=UTC)
    registry_env = {"HOUMAO_GLOBAL_REGISTRY_DIR": str(tmp_path / "registry")}
    record = ManagedAgentRegistryRecordV3(
        agent_name="agent-a",
        agent_id="agent-a",
        generation_id=generation,
        lifecycle=RegistryLifecycleV1(
            state="active",
            relaunchable=True,
            state_updated_at=now.isoformat(),
        ),
        identity=RegistryIdentityV1(backend="claude_headless", tool="claude"),
        runtime=RegistryRuntimeV1(manifest_path=str(manifest_path)),
        terminal=RegistryTerminalV2(
            current_session_name="headless-runtime",
            last_session_name="headless-runtime",
        ),
        liveness=RegistryLivenessV1(
            published_at=now.isoformat(),
            lease_expires_at=(now + timedelta(hours=1)).isoformat(),
        ),
    )
    publish_live_agent_record(record, env=registry_env)

    identity = resolve_verified_self(
        env={"HOUMAO_MANIFEST_PATH": str(manifest_path)},
        registry_env=registry_env,
    )
    assert identity.agent_id == "agent-a"
    assert identity.project_root == project_root

    with pytest.raises(ValueError, match="absolute"):
        resolve_verified_self(
            env={"HOUMAO_MANIFEST_PATH": "manifest.json"},
            registry_env=registry_env,
        )
    copied_pointer = tmp_path / "copied" / "manifest.json"
    copied_pointer.parent.mkdir()
    copied_pointer.symlink_to(manifest_path)
    with pytest.raises(ValueError, match="confined"):
        resolve_verified_self(
            env={"HOUMAO_MANIFEST_PATH": str(copied_pointer)},
            registry_env=registry_env,
        )

    manifest["tmux_session_name"] = "agent-a-session"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    record = record.model_copy(
        update={
            "terminal": RegistryTerminalV2(
                current_session_name="agent-a-session",
                last_session_name="agent-a-session",
            )
        }
    )
    publish_live_agent_record(record, env=registry_env)
    assert (
        resolve_verified_self(
            env={"HOUMAO_MANIFEST_PATH": str(manifest_path)},
            registry_env=registry_env,
            current_tmux_session="agent-a-session",
        ).agent_id
        == "agent-a"
    )
    with pytest.raises(ValueError, match="Current tmux session"):
        resolve_verified_self(
            env={"HOUMAO_MANIFEST_PATH": str(manifest_path)},
            registry_env=registry_env,
            current_tmux_session="foreign-session",
        )

    manifest["registry_generation_id"] = "stale-generation"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        resolve_verified_self(
            env={"HOUMAO_MANIFEST_PATH": str(manifest_path)},
            registry_env=registry_env,
        )
