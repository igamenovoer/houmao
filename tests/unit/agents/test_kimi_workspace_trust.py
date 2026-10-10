"""Unit tests for Kimi workspace-trust pre-seeding."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from houmao.agents.kimi_workspace_trust import (
    KimiWorkspaceTrustError,
    ensure_kimi_workspace_trust,
    kimi_workdir_key,
    kimi_workdir_slug,
    render_kimi_workspace_trust,
)

LIVE_VECTOR_WORKDIR = (
    "/data/ssd2/huangzhe/code/houmao/tmp/kimi-native-prompt-smoke/run-20260809T123938Z"
)
LIVE_VECTOR_KEY = "wd_run-20260809t123938z_8f56092721df"


def test_workdir_key_matches_recorded_kimi_0_34_live_vector() -> None:
    """Pin the algorithm against a record written by Kimi Code 0.34.0 itself."""

    assert kimi_workdir_key(LIVE_VECTOR_WORKDIR) == LIVE_VECTOR_KEY


def test_workdir_key_normalizes_trailing_slash() -> None:
    assert kimi_workdir_key(LIVE_VECTOR_WORKDIR + "/") == LIVE_VECTOR_KEY


def test_workdir_slug_edge_cases() -> None:
    assert kimi_workdir_slug("My Project") == "my-project"
    assert kimi_workdir_slug("UPPER_case.Dir") == "upper_case.dir"
    assert kimi_workdir_slug("--lead--trail--") == "lead--trail"
    assert kimi_workdir_slug("") == "workspace"
    assert kimi_workdir_slug(".") == "workspace"
    assert kimi_workdir_slug("..") == "workspace"
    long_slug = kimi_workdir_slug("a" * 50)
    assert len(long_slug) == 40
    truncated_with_dash = kimi_workdir_slug("a" * 39 + "-bcdef")
    assert truncated_with_dash == "a" * 39
    assert not truncated_with_dash.endswith("-")


def test_render_matches_kimi_json_document_shape() -> None:
    rendered = render_kimi_workspace_trust(Path("/tmp/example"), trusted_at_ms=1786282531421)
    assert rendered == '{"root":"/tmp/example","trustedAt":1786282531421}'
    assert not rendered.endswith("\n")


def test_ensure_projects_record_atomically(tmp_path: Path) -> None:
    home = tmp_path / "home"
    workdir = tmp_path / "work"
    workdir.mkdir()

    projection = ensure_kimi_workspace_trust(
        home_path=home, working_directory=workdir, trusted_at_ms=1700000000000
    )

    assert projection.state == "projected"
    assert projection.changed is True
    assert projection.workspace_key == kimi_workdir_key(workdir.resolve())
    assert projection.path.parent == home.resolve() / "workspace-trust"
    payload = json.loads(projection.path.read_text(encoding="utf-8"))
    assert payload == {"root": str(workdir.resolve()), "trustedAt": 1700000000000}
    assert oct(os.stat(projection.path).st_mode & 0o777) == "0o600"


def test_ensure_is_unchanged_for_matching_record(tmp_path: Path) -> None:
    home = tmp_path / "home"
    workdir = tmp_path / "work"
    workdir.mkdir()
    first = ensure_kimi_workspace_trust(
        home_path=home, working_directory=workdir, trusted_at_ms=1700000000000
    )
    before = first.path.read_bytes()

    second = ensure_kimi_workspace_trust(
        home_path=home, working_directory=workdir, trusted_at_ms=1899999999999
    )

    assert second.state == "unchanged"
    assert second.changed is False
    assert second.path.read_bytes() == before  # trustedAt is not churned


def test_ensure_repairs_drifted_record(tmp_path: Path) -> None:
    home = tmp_path / "home"
    workdir = tmp_path / "work"
    workdir.mkdir()
    projection = ensure_kimi_workspace_trust(
        home_path=home, working_directory=workdir, trusted_at_ms=1700000000000
    )
    projection.path.write_text('{"root":"/somewhere/else","trustedAt":1}', encoding="utf-8")

    repaired = ensure_kimi_workspace_trust(
        home_path=home, working_directory=workdir, trusted_at_ms=1700000000001
    )

    assert repaired.state == "projected"
    payload = json.loads(repaired.path.read_text(encoding="utf-8"))
    assert payload["root"] == str(workdir.resolve())


def test_ensure_repairs_unparseable_record(tmp_path: Path) -> None:
    home = tmp_path / "home"
    workdir = tmp_path / "work"
    workdir.mkdir()
    projection = ensure_kimi_workspace_trust(
        home_path=home, working_directory=workdir, trusted_at_ms=1700000000000
    )
    projection.path.write_text("not json", encoding="utf-8")

    repaired = ensure_kimi_workspace_trust(
        home_path=home, working_directory=workdir, trusted_at_ms=1700000000001
    )

    assert repaired.state == "projected"


def test_ensure_rejects_non_regular_target(tmp_path: Path) -> None:
    home = tmp_path / "home"
    workdir = tmp_path / "work"
    workdir.mkdir()
    key = kimi_workdir_key(workdir.resolve())
    (home / "workspace-trust" / key).mkdir(parents=True)

    with pytest.raises(KimiWorkspaceTrustError):
        ensure_kimi_workspace_trust(home_path=home, working_directory=workdir)


def test_distinct_workdirs_get_distinct_keys(tmp_path: Path) -> None:
    home = tmp_path / "home"
    work_a = tmp_path / "alpha"
    work_b = tmp_path / "beta"
    work_a.mkdir()
    work_b.mkdir()

    first = ensure_kimi_workspace_trust(home_path=home, working_directory=work_a)
    second = ensure_kimi_workspace_trust(home_path=home, working_directory=work_b)

    assert first.workspace_key != second.workspace_key
    assert first.path.is_file() and second.path.is_file()


def test_hash_prefix_matches_sha256_of_normalized_path() -> None:
    normalized = "/some/dir"
    expected = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    assert kimi_workdir_key(normalized) == f"wd_dir_{expected}"
