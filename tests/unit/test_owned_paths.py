from __future__ import annotations

from pathlib import Path

import pytest

from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    HOUMAO_LOCAL_JOBS_DIR_ENV_VAR,
    resolve_mailbox_root,
    resolve_registry_root,
    resolve_runtime_root,
    resolve_session_job_dir,
)


def test_explicit_override_wins_over_env_override(tmp_path: Path) -> None:
    explicit_root = tmp_path / "explicit-runtime"
    env = {HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR: str(tmp_path / "env-runtime")}

    resolved = resolve_runtime_root(
        explicit_root=explicit_root,
        env=env,
    )

    assert resolved == explicit_root.resolve()


def test_runtime_root_uses_env_override_when_no_explicit_override(tmp_path: Path) -> None:
    resolved = resolve_runtime_root(
        env={HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR: str(tmp_path / "runtime-root")},
    )

    assert resolved == (tmp_path / "runtime-root").resolve()


def test_runtime_root_uses_default_override_when_no_explicit_or_env(tmp_path: Path) -> None:
    resolved = resolve_runtime_root(default_root=tmp_path / "project-runtime")

    assert resolved == (tmp_path / "project-runtime").resolve()


def test_runtime_env_override_still_wins_over_default_override(tmp_path: Path) -> None:
    resolved = resolve_runtime_root(
        env={HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR: str(tmp_path / "env-runtime")},
        default_root=tmp_path / "project-runtime",
    )

    assert resolved == (tmp_path / "env-runtime").resolve()


def test_registry_root_defaults_under_platformdirs_home_anchor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_home = tmp_path / "home-anchor"
    fake_user_data_path = fake_home / ".local" / "share" / "houmao"
    monkeypatch.setattr(
        "houmao.owned_paths.platformdirs.user_data_path",
        lambda **kwargs: fake_user_data_path,
    )

    assert resolve_registry_root() == (fake_home / ".houmao" / "registry").resolve()


def test_mailbox_root_uses_env_override_when_no_explicit_override(tmp_path: Path) -> None:
    resolved = resolve_mailbox_root(
        env={HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR: str(tmp_path / "mailbox-root")},
    )

    assert resolved == (tmp_path / "mailbox-root").resolve()


def test_job_dir_defaults_under_working_directory(tmp_path: Path) -> None:
    resolved = resolve_session_job_dir(
        session_id="session-20260314-120000Z-abcd1234",
        working_directory=tmp_path / "repo",
    )

    assert (
        resolved
        == (tmp_path / "repo" / ".houmao" / "jobs" / "session-20260314-120000Z-abcd1234").resolve()
    )


def test_job_dir_uses_env_override_when_no_explicit_override(tmp_path: Path) -> None:
    resolved = resolve_session_job_dir(
        session_id="session-20260314-120000Z-abcd1234",
        working_directory=tmp_path / "repo",
        env={HOUMAO_LOCAL_JOBS_DIR_ENV_VAR: str(tmp_path / "custom-jobs")},
    )

    assert resolved == (tmp_path / "custom-jobs" / "session-20260314-120000Z-abcd1234").resolve()


def test_job_dir_uses_default_jobs_root_when_no_explicit_or_env(tmp_path: Path) -> None:
    resolved = resolve_session_job_dir(
        session_id="session-20260314-120000Z-abcd1234",
        working_directory=tmp_path / "repo",
        default_jobs_root=tmp_path / "project-jobs",
    )

    assert resolved == (tmp_path / "project-jobs" / "session-20260314-120000Z-abcd1234").resolve()


def test_env_override_requires_absolute_path() -> None:
    with pytest.raises(ValueError, match=HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR):
        resolve_registry_root(env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: "relative/path"})
