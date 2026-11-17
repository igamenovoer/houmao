"""Execution contracts reject untrusted authority and ambiguous protocol documents."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
import yaml

from houmao.execution.models import (
    ContextPathV1,
    ControllerScopeV1,
    ExecutionBindingV1,
    ExecutionProfileV1,
    ExecutionRequestV1,
    ExecutionResponseV1,
    route_fingerprint,
)
from houmao.execution.profiles import ExecutionProfileError, load_execution_profile
from houmao.execution.protocol import (
    MAX_JSON_DEPTH,
    MAX_REQUEST_BYTES,
    ExecutionProtocolError,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)


def profile_payload(**changes: object) -> dict[str, object]:
    """Return one representative secret-free delegated route."""

    return {
        "schema_version": 1,
        "name": "worker-alice",
        "transport": "sudo",
        "account": "alice",
        "entrypoint": "/usr/local/bin/houmao-mgr",
        "policy_path": "/etc/houmao/executors/alice.json",
        "project_root": "/srv/alice/project",
        **changes,
    }


def test_transports_are_closed_and_independent_of_agent_backend() -> None:
    """Require typed native routes without accepting a backend or arbitrary command hook."""

    assert ExecutionProfileV1.model_validate(profile_payload()).transport == "sudo"
    ssh = ExecutionProfileV1.model_validate(
        profile_payload(
            transport="ssh", ssh_host="worker.example", known_hosts_file="/operator/known_hosts"
        )
    )
    assert ssh.account == "alice"
    docker = ExecutionProfileV1.model_validate(
        profile_payload(transport="docker", account="1000:1000", container_id="a" * 64)
    )
    assert docker.container_id == "a" * 64
    for changes in (
        {"transport": "podman"},
        {"backend": "codex_headless"},
        {"argv": ["sh", "-c", "id"]},
        {"transport": "docker", "container_id": "mutable-name"},
        {"transport": "ssh", "ssh_host": "host", "known_hosts_file": None},
        {"transport": "local", "ssh_host": "other"},
    ):
        with pytest.raises(ValidationError):
            ExecutionProfileV1.model_validate(profile_payload(**changes))


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "../escape"},
        {"account": "-root"},
        {"entrypoint": "houmao-mgr"},
        {"project_root": "/srv/project/../other"},
        {"expected_uid": "1000"},
        {"environment": {"HOME": "/operator"}},
        {"environment": {"SSH_AUTH_SOCK": "/agent"}},
        {"environment": {"PROVIDER_API_KEY": "secret"}},
        {"environment": {"SUDO_USER": "admin"}},
        {"environment": {"PYTHONPATH": "/untrusted"}},
    ],
)
def test_invalid_or_credential_bearing_route_fields_are_rejected(
    changes: dict[str, object],
) -> None:
    """Do not promote unsafe selectors or inline credentials into route authority."""

    with pytest.raises(ValidationError):
        ExecutionProfileV1.model_validate(profile_payload(**changes))


def test_fingerprint_pins_authority_but_allows_authentication_reference_rotation() -> None:
    """Keep an existing logical agent on its birth route when profiles are edited."""

    original = ExecutionProfileV1.model_validate(
        profile_payload(
            transport="ssh",
            ssh_host="worker.example",
            known_hosts_file="/operator/known_hosts",
            identity_file="/operator/key1",
        )
    )
    rotated = ExecutionProfileV1.model_validate(
        profile_payload(
            transport="ssh",
            ssh_host="worker.example",
            known_hosts_file="/operator/new_known_hosts",
            identity_file="/operator/key2",
            timeout_seconds=5.0,
        )
    )
    assert route_fingerprint(original) == route_fingerprint(rotated)
    retargeted = original.model_copy(update={"ssh_host": "other.example"})
    assert route_fingerprint(original) != route_fingerprint(retargeted)
    changed_roots = original.model_copy(
        update={"environment": {"HOUMAO_GLOBAL_RUNTIME_DIR": "/other"}}
    )
    assert route_fingerprint(original) != route_fingerprint(changed_roots)


def test_binding_and_context_path_roundtrip_without_credentials() -> None:
    """Keep owner/controller identity separate from agent IDs and authentication inputs."""

    scope = ControllerScopeV1(
        controller_id="operator",
        authority="sudo_policy",
        operations=("state", "stop"),
        project_roots=("/srv/project",),
    )
    binding = ExecutionBindingV1(
        context_id="context-alice",
        host_id="host-1",
        account="alice",
        uid=1001,
        gid=1001,
        groups=(1001,),
        registry_root="/home/alice/.config/houmao/registry",
        runtime_root="/home/alice/.config/houmao/runtime",
        project_root="/srv/project",
        profile_name="worker-alice",
        transport="sudo",
        controller=scope,
        route_fingerprint="f" * 64,
        tmux_socket="/run/user/1001/houmao/tmux.sock",
    )
    response = ExecutionResponseV1(
        request_id="request-1",
        outcome="completed",
        admitted=True,
        binding=binding,
        capabilities=("state", "stop"),
    )
    assert decode_response(encode_response(response)) == response
    assert "agent_id" not in binding.model_dump()
    assert "identity_file" not in binding.model_dump()
    path = ContextPathV1(context_id=binding.context_id, path="/home/alice/native")
    assert path.context_id == "context-alice"
    with pytest.raises(ValidationError):
        ContextPathV1(context_id=binding.context_id, path="../operator-native")


def test_profile_loading_is_operator_scoped_and_non_mutating(tmp_path: Path) -> None:
    """Resolve only the named configured profile and never create a missing collection."""

    root = tmp_path / "executors"
    root.mkdir(mode=0o700)
    profile = root / "worker-alice.yaml"
    profile.write_text(yaml.safe_dump(profile_payload()))
    profile.chmod(0o600)
    assert load_execution_profile("worker-alice", root=root).account == "alice"
    missing_root = tmp_path / "uncreated"
    with pytest.raises(ExecutionProfileError):
        load_execution_profile("unknown", root=missing_root)
    assert not missing_root.exists()
    with pytest.raises(ValueError):
        load_execution_profile("../worker-alice", root=root)
    profile.write_text(yaml.safe_dump(profile_payload(name="other-name")))
    with pytest.raises(ExecutionProfileError):
        load_execution_profile("worker-alice", root=root)


def test_profile_loading_rejects_symlinks_and_writable_configuration(tmp_path: Path) -> None:
    """Project-owned writable content cannot become a trusted execution route."""

    root = tmp_path / "executors"
    root.mkdir(mode=0o700)
    target = tmp_path / "project.yaml"
    target.write_text(yaml.safe_dump(profile_payload()))
    (root / "worker-alice.yaml").symlink_to(target)
    with pytest.raises(ExecutionProfileError):
        load_execution_profile("worker-alice", root=root)
    (root / "worker-alice.yaml").unlink()
    (root / "worker-alice.yaml").write_text(target.read_text())
    (root / "worker-alice.yaml").chmod(0o666)
    with pytest.raises(ExecutionProfileError):
        load_execution_profile("worker-alice", root=root)
    (root / "worker-alice.yaml").chmod(0o600)
    root.chmod(0o777)
    with pytest.raises(ExecutionProfileError):
        load_execution_profile("worker-alice", root=root)


def test_protocol_rejects_ambiguous_and_incompatible_documents() -> None:
    """Fail closed before dispatch for version, framing, operation, and authority errors."""

    request = ExecutionRequestV1(operation="state", agent_id="agent-1")
    assert decode_request(encode_request(request)) == request
    for payload in (
        b"{}{}",
        b'{"schema_version":2,"operation":"state"}',
        b'{"operation":"state","operation":"stop"}',
        b'{"operation":"kill-server"}',
        b'{"operation":"state","deadline_seconds":NaN}',
        b'{"operation":"state","arguments":{"argv":["id"]}}',
        b"\xff",
    ):
        with pytest.raises(ExecutionProtocolError):
            decode_request(payload)
    with pytest.raises(ExecutionProtocolError):
        decode_request(b" " * (MAX_REQUEST_BYTES + 1))
    nested: object = "secret-value"
    for _ in range(MAX_JSON_DEPTH + 2):
        nested = [nested]
    with pytest.raises(ExecutionProtocolError) as error:
        decode_request(json.dumps({"operation": "state", "arguments": {"value": nested}}).encode())
    assert "secret-value" not in str(error.value)


def test_uncertain_response_cannot_claim_confirmed_non_admission() -> None:
    """Represent lost owner results without inviting a safe automatic mutation replay."""

    response = ExecutionResponseV1(
        request_id="request-1", outcome="indeterminate", admitted=None, error_code="connection_lost"
    )
    assert decode_response(encode_response(response)).admitted is None
    with pytest.raises(ValidationError):
        response.model_validate({**response.model_dump(), "admitted": False})
