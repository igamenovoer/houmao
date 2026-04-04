from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.server.models import HoumaoRegisterLaunchRequest
from houmao.server.tui.registry import known_session_record_from_registration


def _registration(
    tmp_path: Path,
    *,
    observed_tool_version: str | None,
) -> HoumaoRegisterLaunchRequest:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    return HoumaoRegisterLaunchRequest(
        session_name="cao-gpu",
        terminal_id="abcd1234",
        tool="claude",
        observed_tool_version=observed_tool_version,
        manifest_path=str(manifest_path),
        tmux_session_name="HOUMAO-gpu",
        tmux_window_name="developer-1",
    )


def test_known_session_record_prefers_top_level_manifest_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "houmao.server.tui.registry.load_session_manifest",
        lambda path: SimpleNamespace(
            path=path,
            payload={
                "tool": "claude",
                "launch_policy_provenance": {"detected_tool_version": "2.1.81"},
                "launch_plan": {"launch_policy_provenance": {"detected_tool_version": "2.1.80"}},
            },
        ),
    )

    record = known_session_record_from_registration(
        registration=_registration(tmp_path, observed_tool_version="2.1.70"),
        allow_shared_registry_enrichment=False,
    )

    assert record is not None
    assert record.observed_tool_version == "2.1.81"
    assert record.to_identity().observed_tool_version == "2.1.81"


def test_known_session_record_falls_back_to_launch_plan_manifest_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "houmao.server.tui.registry.load_session_manifest",
        lambda path: SimpleNamespace(
            path=path,
            payload={
                "tool": "claude",
                "launch_plan": {"launch_policy_provenance": {"detected_tool_version": "2.1.80"}},
            },
        ),
    )

    record = known_session_record_from_registration(
        registration=_registration(tmp_path, observed_tool_version=None),
        allow_shared_registry_enrichment=False,
    )

    assert record is not None
    assert record.observed_tool_version == "2.1.80"


def test_known_session_record_falls_back_to_registration_version_when_manifest_omits_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "houmao.server.tui.registry.load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={"tool": "claude"}),
    )

    record = known_session_record_from_registration(
        registration=_registration(tmp_path, observed_tool_version="2.1.70"),
        allow_shared_registry_enrichment=False,
    )

    assert record is not None
    assert record.observed_tool_version == "2.1.70"
