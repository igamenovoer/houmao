"""Verify reproducible receiver preparation and private grant-export boundaries."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import ModuleType

import httpx
import pytest


def _module(name: str) -> ModuleType:
    """Load utility source for focused tooling tests without packaging it."""

    path = Path(__file__).resolve().parents[3] / "tools/cccc" / (name + ".py")
    spec = importlib.util.spec_from_file_location("cccc_tool_" + name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(root: Path, *arguments: str) -> str:
    """Execute Git only against this test's disposable repository."""

    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True)


def test_preparation_pins_patch_and_detects_tampering(tmp_path: Path) -> None:
    """Reproduce new-file patches and reject reuse after source modification."""

    module = _module("prepare_receiver")
    repository = tmp_path / "upstream"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "main.txt").write_text("original\n")
    _git(repository, "add", ".")
    _git(
        repository,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    revision = _git(repository, "rev-parse", "HEAD").strip()
    (repository / "new.txt").write_text("new receiver\n")
    _git(repository, "add", "new.txt")
    patch = tmp_path / "receiver.patch"
    patch.write_text(_git(repository, "diff", "--cached", "--binary"))
    manifest = tmp_path / "upstream.json"
    manifest.write_text(
        json.dumps({"repository": str(repository), "revision": revision, "patches": [patch.name]})
    )
    output = tmp_path / "prepared"
    report = module.prepare(output, manifest_path=manifest)
    assert (output / "new.txt").read_text() == "new receiver\n"
    assert module.prepare(output, manifest_path=manifest) == report
    (output / "new.txt").write_text("tampered\n")
    with pytest.raises(ValueError, match="Source or patch selection changed"):
        module.prepare(output, manifest_path=manifest)


def test_preparation_rejects_checkout_output(tmp_path: Path) -> None:
    """Keep prepared dependencies outside tracked source even for valid manifests."""

    module = _module("prepare_receiver")
    manifest = tmp_path / "upstream.json"
    manifest.write_text(json.dumps({"repository": "unused", "revision": "a" * 40, "patches": []}))
    with pytest.raises(ValueError, match="outside"):
        module.prepare(module.PROJECT / "tmp/invalid-prepared", manifest_path=manifest)


def test_export_is_private_and_contains_only_selected_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Export synthetic credentials privately and refuse accidental replacement."""

    module = _module("provision")
    client_type = httpx.Client
    calls = []

    def respond(request: httpx.Request) -> httpx.Response:
        """Return an explicitly selected synthetic Actor grant."""

        assert request.url.path == "/api/v1/external-receiver/v2/grants"
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "token": "synthetic-token",
                    "group_id": "group",
                    "actor_id": "actor",
                    "actor_generation": "generation",
                    "grant_id": "grant",
                    "protocol_version": 2,
                },
            },
        )

    monkeypatch.setattr(
        module.httpx,
        "Client",
        lambda **kwargs: client_type(transport=httpx.MockTransport(respond), **kwargs),
    )
    output = tmp_path / "grant.json"
    result = module.provision("http://127.0.0.1:8849", "group", "actor", "owner", output)
    assert "token" not in result
    assert output.stat().st_mode & 0o777 == 0o600
    assert output.stat().st_uid == os.getuid()
    assert json.loads(output.read_text())["agent_id"] == "owner"
    with pytest.raises(ValueError, match="fresh private"):
        module.provision("http://127.0.0.1:8849", "group", "actor", "owner", output)
    assert len(calls) == 1


def test_stock_grant_route_returns_compatibility_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Diagnose a stock service before publishing a private profile."""

    module = _module("provision")
    client_type = httpx.Client
    monkeypatch.setattr(
        module.httpx,
        "Client",
        lambda **kw: client_type(
            transport=httpx.MockTransport(lambda _: httpx.Response(404)), **kw
        ),
    )
    output = tmp_path / "grant.json"
    with pytest.raises(module.IncompatibleReceiverError, match="external receiver v2"):
        module.provision("http://127.0.0.1:8849", "group", "actor", "owner", output)
    assert not output.exists()


def test_remote_export_requires_explicit_operator_credential(tmp_path: Path) -> None:
    """Never discover ambient remote administrative authentication."""

    module = _module("provision")
    with pytest.raises(ValueError, match="explicit operator"):
        module.provision(
            "https://cccc.example.test", "group", "actor", "owner", tmp_path / "grant.json"
        )
