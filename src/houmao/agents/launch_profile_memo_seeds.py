"""Launch-profile memo-seed application helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from houmao.agents.agent_workspace import (
    AgentMemoryPaths,
    clear_memory_pages,
    ensure_agent_memory,
    ensure_memory_page_directory,
    memo_has_content,
    pages_have_content,
    write_memo,
    write_memory_page,
)
from houmao.project.launch_profiles import ResolvedLaunchProfileMemoSeed


@dataclass(frozen=True)
class LaunchProfileMemoSeedApplication:
    """Result metadata for one attempted memo-seed application."""

    status: Literal["applied", "skipped"]
    source_kind: str
    policy: str
    reason: str | None = None
    memo_written: bool = False
    page_file_count: int = 0
    page_directory_count: int = 0

    def to_payload(self) -> dict[str, object]:
        """Return one secret-free operator-facing memo-seed result payload."""

        payload: dict[str, object] = {
            "status": self.status,
            "source_kind": self.source_kind,
            "policy": self.policy,
            "memo_written": self.memo_written,
            "page_file_count": self.page_file_count,
            "page_directory_count": self.page_directory_count,
        }
        if self.reason is not None:
            payload["reason"] = self.reason
        return payload


class LaunchProfileMemoSeedError(RuntimeError):
    """Raised when a launch-profile memo seed cannot be applied safely."""


@dataclass(frozen=True)
class _LaunchProfileMemoSeedPayload:
    """Loaded memo-seed content plus the managed-memory components it represents."""

    memo_text: str | None
    pages_present: bool
    page_directories: list[str]
    page_files: list[tuple[str, str]]

    @property
    def has_memo(self) -> bool:
        """Return whether the seed explicitly represents the fixed memo file."""

        return self.memo_text is not None


def apply_launch_profile_memo_seed(
    *,
    paths: AgentMemoryPaths,
    memo_seed: ResolvedLaunchProfileMemoSeed,
) -> LaunchProfileMemoSeedApplication:
    """Apply one resolved launch-profile memo seed to managed memory paths."""

    payload = _load_memo_seed_payload(memo_seed)
    if memo_seed.policy == "initialize":
        if _represented_targets_have_content(paths=paths, payload=payload):
            return LaunchProfileMemoSeedApplication(
                status="skipped",
                source_kind=memo_seed.source_kind,
                policy=memo_seed.policy,
                reason="existing memo state present",
            )
        return _materialize_memo_seed(
            paths=paths,
            memo_seed=memo_seed,
            payload=payload,
            replace_existing=False,
        )
    if memo_seed.policy == "replace":
        return _materialize_memo_seed(
            paths=paths,
            memo_seed=memo_seed,
            payload=payload,
            replace_existing=True,
        )
    if memo_seed.policy == "fail-if-nonempty":
        if _represented_targets_have_content(paths=paths, payload=payload):
            raise LaunchProfileMemoSeedError(
                "Launch-profile memo seed policy `fail-if-nonempty` aborted launch because "
                "existing memo state is present."
            )
        return _materialize_memo_seed(
            paths=paths,
            memo_seed=memo_seed,
            payload=payload,
            replace_existing=False,
        )
    raise LaunchProfileMemoSeedError(
        f"Unsupported launch-profile memo seed policy: {memo_seed.policy!r}"
    )


def _represented_targets_have_content(
    *,
    paths: AgentMemoryPaths,
    payload: _LaunchProfileMemoSeedPayload,
) -> bool:
    """Return whether any target represented by the seed already has authored content."""

    if payload.has_memo and memo_has_content(paths):
        return True
    if payload.pages_present and pages_have_content(paths):
        return True
    return False


def _materialize_memo_seed(
    *,
    paths: AgentMemoryPaths,
    memo_seed: ResolvedLaunchProfileMemoSeed,
    payload: _LaunchProfileMemoSeedPayload,
    replace_existing: bool,
) -> LaunchProfileMemoSeedApplication:
    """Write one resolved memo-seed payload into the target memory paths."""

    ensure_agent_memory(paths)
    if replace_existing and payload.pages_present:
        clear_memory_pages(paths)
    if payload.has_memo:
        assert payload.memo_text is not None
        write_memo(paths, payload.memo_text, append=False)

    for relative_dir in payload.page_directories:
        ensure_memory_page_directory(paths, relative_path=relative_dir)
    for relative_path, page_text in payload.page_files:
        write_memory_page(paths, relative_path=relative_path, content=page_text, append=False)

    return LaunchProfileMemoSeedApplication(
        status="applied",
        source_kind=memo_seed.source_kind,
        policy=memo_seed.policy,
        memo_written=payload.has_memo,
        page_file_count=len(payload.page_files),
        page_directory_count=len(payload.page_directories),
    )


def _load_memo_seed_payload(
    memo_seed: ResolvedLaunchProfileMemoSeed,
) -> _LaunchProfileMemoSeedPayload:
    """Load one resolved memo seed into memo text plus contained page payloads."""

    if memo_seed.source_kind == "memo":
        if not memo_seed.source_path.is_file():
            raise LaunchProfileMemoSeedError(
                f"Launch-profile memo seed content is missing: {memo_seed.source_path}"
            )
        return _LaunchProfileMemoSeedPayload(
            memo_text=memo_seed.source_path.read_text(encoding="utf-8"),
            pages_present=False,
            page_directories=[],
            page_files=[],
        )
    if memo_seed.source_kind != "tree":
        raise LaunchProfileMemoSeedError(
            f"Unsupported launch-profile memo seed source kind: {memo_seed.source_kind!r}"
        )
    if not memo_seed.source_path.is_dir():
        raise LaunchProfileMemoSeedError(
            f"Launch-profile memo seed tree is missing: {memo_seed.source_path}"
        )
    memo_text = None
    memo_path = memo_seed.source_path / "houmao-memo.md"
    if memo_path.exists():
        if not memo_path.is_file():
            raise LaunchProfileMemoSeedError(
                f"Launch-profile memo seed memo file is invalid: {memo_path}"
            )
        memo_text = memo_path.read_text(encoding="utf-8")
    page_directories: list[str] = []
    page_files: list[tuple[str, str]] = []
    pages_root = memo_seed.source_path / "pages"
    if pages_root.exists():
        if not pages_root.is_dir():
            raise LaunchProfileMemoSeedError(
                f"Launch-profile memo seed pages directory is invalid: {pages_root}"
            )
        for candidate in sorted(pages_root.rglob("*"), key=lambda item: item.as_posix()):
            relative_path = candidate.relative_to(pages_root).as_posix()
            if candidate.is_dir():
                page_directories.append(relative_path)
                continue
            if not candidate.is_file():
                raise LaunchProfileMemoSeedError(
                    f"Launch-profile memo seed page path is invalid: {candidate}"
                )
            page_files.append((relative_path, candidate.read_text(encoding="utf-8")))
    return _LaunchProfileMemoSeedPayload(
        memo_text=memo_text,
        pages_present=pages_root.exists(),
        page_directories=page_directories,
        page_files=page_files,
    )
