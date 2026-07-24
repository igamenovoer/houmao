"""Private per-instance workspace topology, indexing, and lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import tomllib
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
import tomli_w

from houmao.agents.instance_state import InstanceStateStore
from houmao.project.agent_definitions import (
    PrivateWorkspaceContract,
    workspace_contract_digest,
)

WORKSPACE_MANIFEST_FILENAME = "houmao-agent-workspace.toml"
WORKSPACE_INDEX_FILENAME = "houmao-agent-workspace.sqlite"
WORKSPACE_MANIFEST_SCHEMA = "houmao-agent-workspace.v1"
WORKSPACE_INDEX_SCHEMA_VERSION = 1
PRIVATE_WORKSPACE_ROOT = Path(".houmao") / "private-agents"
_EXCLUDE_BEGIN_PREFIX = "# BEGIN houmao-agent-workspace "
_EXCLUDE_END_PREFIX = "# END houmao-agent-workspace "


def _utcnow_iso() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(tz=UTC).isoformat()


def _digest_file(path: Path) -> str:
    """Return one tagged SHA-256 file digest."""

    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


class WorkspaceBinding(BaseModel):
    """One stable semantic label mapped to a confined concrete path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(pattern=r"^workspace\.[a-z][a-z0-9_.-]*$")
    relative_path: str
    path_kind: Literal["directory", "file"]
    required: bool
    materialize: bool

    @field_validator("relative_path")
    @classmethod
    def confined_relative_path(cls, value: str) -> str:
        """Reject absolute and parent-traversing bindings."""

        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
            raise ValueError("Workspace bindings must use confined relative paths.")
        return candidate.as_posix()


class WorkspaceManifest(BaseModel):
    """Stable TOML identity and topology for one private workspace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-workspace.v1"] = "houmao-agent-workspace.v1"
    workspace_id: str
    agent_id: str
    project_root: str
    deployment_id: str
    definition_id: str
    workspace_contract_digest: str
    tracking_posture: Literal["local-untracked", "tracked-permitted"]
    workdir_mode: Literal["project-root", "private-root"]
    index_filename: Literal["houmao-agent-workspace.sqlite"] = "houmao-agent-workspace.sqlite"
    index_schema_version: Literal[1] = 1
    bindings: tuple[WorkspaceBinding, ...]


@dataclass(frozen=True)
class PreparedPrivateWorkspace:
    """Resolved private workspace and independent execution workdir."""

    root: Path
    manifest: WorkspaceManifest
    execution_workdir: Path
    reused: bool


class PrivateWorkspace:
    """Operate on one manifested private workspace."""

    def __init__(self, root: Path) -> None:
        """Bind operations to one workspace root."""

        self.m_root = root.resolve()

    @property
    def root(self) -> Path:
        """Return the private workspace root."""

        return self.m_root

    @property
    def manifest_path(self) -> Path:
        """Return the stable TOML manifest path."""

        return self.m_root / WORKSPACE_MANIFEST_FILENAME

    @property
    def index_path(self) -> Path:
        """Return the mutable SQLite index path."""

        return self.m_root / WORKSPACE_INDEX_FILENAME

    def load_manifest(self) -> WorkspaceManifest:
        """Load and strictly validate the stable manifest."""

        return WorkspaceManifest.model_validate(
            tomllib.loads(self.manifest_path.read_text(encoding="utf-8"))
        )

    def validate(self) -> dict[str, Any]:
        """Cross-validate manifest, index identity, bindings, and indexed payloads."""

        manifest = self.load_manifest()
        project_root = Path(manifest.project_root).resolve()
        try:
            self.m_root.relative_to(project_root)
        except ValueError as exc:
            raise ValueError("Private workspace is outside its declared project.") from exc
        with sqlite3.connect(self.index_path) as connection:
            connection.row_factory = sqlite3.Row
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]) != "ok":
                raise ValueError("Private workspace index integrity check failed.")
            metadata = {
                str(row["key"]): str(row["value"])
                for row in connection.execute("SELECT key, value FROM workspace_meta")
            }
            records = connection.execute(
                "SELECT record_id, relative_path, digest FROM workspace_records ORDER BY record_id"
            ).fetchall()
        expected = {
            "schema_version": str(WORKSPACE_INDEX_SCHEMA_VERSION),
            "workspace_id": manifest.workspace_id,
            "agent_id": manifest.agent_id,
            "deployment_id": manifest.deployment_id,
            "workspace_contract_digest": manifest.workspace_contract_digest,
        }
        mismatches = [key for key, value in expected.items() if metadata.get(key) != value]
        if mismatches:
            raise ValueError(
                "Workspace TOML and SQLite identity mismatch: " + ", ".join(mismatches)
            )
        _validate_bindings(self.m_root, manifest.bindings, require_materialized=False)
        drift: list[str] = []
        for row in records:
            payload = _resolve_binding_path(self.m_root, str(row["relative_path"]))
            if not payload.is_file() or _digest_file(payload) != str(row["digest"]):
                drift.append(str(row["record_id"]))
        return {
            "valid": not drift,
            "workspace_id": manifest.workspace_id,
            "generation": int(metadata.get("generation", "0")),
            "payload_drift": drift,
        }

    def resolve(self, label: str) -> Path:
        """Resolve one current semantic label to a confined concrete path."""

        manifest = self.load_manifest()
        binding = next((item for item in manifest.bindings if item.label == label), None)
        if binding is None:
            raise FileNotFoundError(f"Workspace semantic label `{label}` was not declared.")
        path = _resolve_binding_path(self.m_root, binding.relative_path)
        if path.is_symlink():
            raise ValueError(f"Workspace semantic path crosses a symlink: {path}")
        return path

    def materialize(self, label: str) -> Path:
        """Materialize one declared semantic file or directory."""

        manifest = self.load_manifest()
        binding = next((item for item in manifest.bindings if item.label == label), None)
        if binding is None:
            raise FileNotFoundError(f"Workspace semantic label `{label}` was not declared.")
        path = self.resolve(label)
        if binding.path_kind == "directory":
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
        return path

    def remap(
        self,
        *,
        label: str,
        relative_path: str,
        expected_generation: int,
    ) -> dict[str, Any]:
        """Optimistically remap one existing label without redefining the contract."""

        manifest = self.load_manifest()
        candidate_binding = next((item for item in manifest.bindings if item.label == label), None)
        if candidate_binding is None:
            raise FileNotFoundError(f"Workspace semantic label `{label}` was not declared.")
        replacement = candidate_binding.model_copy(update={"relative_path": relative_path})
        updated_bindings = tuple(
            replacement if item.label == label else item for item in manifest.bindings
        )
        _validate_bindings(self.m_root, updated_bindings, require_materialized=False)
        with sqlite3.connect(self.index_path) as connection:
            row = connection.execute(
                "SELECT value FROM workspace_meta WHERE key = 'generation'"
            ).fetchone()
            generation = int(row[0]) if row is not None else 0
            if generation != expected_generation:
                raise ValueError(
                    f"Stale workspace generation: expected {expected_generation}, "
                    f"current {generation}."
                )
            next_generation = generation + 1
            connection.execute(
                "UPDATE workspace_meta SET value = ? WHERE key = 'generation'",
                (str(next_generation),),
            )
            connection.commit()
        updated = manifest.model_copy(update={"bindings": updated_bindings})
        _write_manifest(self.manifest_path, updated)
        return {
            "label": label,
            "relative_path": replacement.relative_path,
            "generation": next_generation,
        }

    def set_tracking_posture(
        self, posture: Literal["local-untracked", "tracked-permitted"]
    ) -> WorkspaceManifest:
        """Change tracking permission without staging or committing content."""

        manifest = self.load_manifest()
        project_root = Path(manifest.project_root)
        if posture == "local-untracked":
            _establish_local_untracked(
                project_root=project_root,
                workspace_root=self.m_root,
                workspace_id=manifest.workspace_id,
            )
        else:
            _remove_owned_exclude(
                project_root=project_root,
                workspace_id=manifest.workspace_id,
            )
        updated = manifest.model_copy(update={"tracking_posture": posture})
        _write_manifest(self.manifest_path, updated)
        return updated

    def project_mindset(
        self,
        *,
        state_store: InstanceStateStore,
        mindset_name: str,
        semantic_label: str,
    ) -> dict[str, Any]:
        """Publish one immutable canonical mindset revision and index it."""

        mindset = state_store.mindset(mindset_name)
        if not bool(mindset["declaration"].get("expose_in_private_workspace", False)):
            raise ValueError(
                f"Mindset `{mindset_name}` is not declared for private-workspace projection."
            )
        directory = self.resolve(semantic_label)
        directory.mkdir(parents=True, exist_ok=True)
        filename = f"{mindset_name}-r{mindset['revision']}.json"
        payload_path = directory / filename
        payload = {
            "schema_version": "houmao-mindset-projection.v1",
            "name": mindset_name,
            "revision": mindset["revision"],
            "record": mindset["record"],
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if payload_path.exists() and payload_path.read_text(encoding="utf-8") != text:
            raise ValueError(f"Immutable mindset projection drifted: {payload_path}")
        payload_path.write_text(text, encoding="utf-8")
        digest = _digest_file(payload_path)
        record_id = f"mindset:{mindset_name}:{mindset['revision']}"
        with sqlite3.connect(self.index_path) as connection:
            existing = connection.execute(
                "SELECT digest FROM workspace_records WHERE record_id = ?", (record_id,)
            ).fetchone()
            if existing is not None and str(existing[0]) != digest:
                raise ValueError(f"Indexed mindset projection drifted: {record_id}")
            connection.execute(
                """
                INSERT INTO workspace_records(
                    record_id, record_kind, semantic_label, relative_path,
                    digest, revision, created_at
                ) VALUES (?, 'mindset_projection', ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO NOTHING
                """,
                (
                    record_id,
                    semantic_label,
                    payload_path.relative_to(self.m_root).as_posix(),
                    digest,
                    int(mindset["revision"]),
                    _utcnow_iso(),
                ),
            )
            connection.commit()
        return {
            "record_id": record_id,
            "path": str(payload_path),
            "digest": digest,
            "canonical_state_preserved": True,
        }

    def cleanup(self, *, confirmed: bool) -> dict[str, Any]:
        """Delete one drift-free owned workspace after explicit confirmation."""

        if not confirmed:
            raise ValueError("Destructive private-workspace cleanup requires confirmation.")
        report = self.validate()
        if not report["valid"]:
            raise ValueError("Private workspace cleanup is blocked by indexed payload drift.")
        manifest = self.load_manifest()
        indexed_paths: set[str] = set()
        with sqlite3.connect(self.index_path) as connection:
            indexed_paths = {
                str(row[0])
                for row in connection.execute(
                    "SELECT relative_path FROM workspace_records"
                ).fetchall()
            }
        allowed_files = {
            WORKSPACE_MANIFEST_FILENAME,
            WORKSPACE_INDEX_FILENAME,
            *indexed_paths,
        }
        unowned = [
            path.relative_to(self.m_root).as_posix()
            for path in self.m_root.rglob("*")
            if path.is_file() and path.relative_to(self.m_root).as_posix() not in allowed_files
        ]
        if unowned:
            raise ValueError(
                "Private workspace cleanup is blocked by unowned content: "
                + ", ".join(sorted(unowned))
            )
        project_root = Path(manifest.project_root)
        relative_root = self.m_root.relative_to(project_root).as_posix()
        tracked = subprocess.run(
            ["git", "-C", str(project_root), "ls-files", "--", relative_root],
            check=False,
            capture_output=True,
            text=True,
        )
        if tracked.returncode == 0 and tracked.stdout.strip():
            raise ValueError(
                "Private workspace cleanup is blocked by tracked repository content: "
                + ", ".join(tracked.stdout.splitlines())
            )
        _remove_owned_exclude(project_root=project_root, workspace_id=manifest.workspace_id)
        shutil.rmtree(self.m_root)
        return {"removed": str(self.m_root), "recoverable": False}


def prepare_private_workspace(
    *,
    project_root: Path,
    agent_id: str,
    deployment_id: str,
    definition_id: str,
    contract: PrivateWorkspaceContract,
    enabled: bool,
    workdir_mode: Literal["project-root", "private-root"],
    state_store: InstanceStateStore,
) -> PreparedPrivateWorkspace | None:
    """Idempotently prepare or reuse one project-contained private workspace."""

    if not enabled:
        if contract.mode == "required":
            raise ValueError("This instance contract requires a private workspace.")
        return None
    if contract.mode == "disabled":
        raise ValueError("This instance contract does not permit a private workspace.")
    if workdir_mode != contract.workdir_mode:
        raise ValueError("Selected private-workspace workdir mode is not definition-valid.")
    resolved_project = project_root.resolve()
    root = resolved_project / PRIVATE_WORKSPACE_ROOT / agent_id
    digest = workspace_contract_digest(contract)
    existing_association = state_store.private_workspace_association()
    if root.exists():
        workspace = PrivateWorkspace(root)
        report = workspace.validate()
        manifest = workspace.load_manifest()
        if (
            manifest.agent_id != agent_id
            or manifest.deployment_id != deployment_id
            or manifest.workspace_contract_digest != digest
            or not report["valid"]
        ):
            raise ValueError("Existing private workspace is incompatible or drifted.")
        if existing_association is None:
            state_store.set_private_workspace_association(
                workspace_id=manifest.workspace_id,
                workspace_root=root,
                workspace_contract_digest=digest,
            )
        execution_workdir = root if workdir_mode == "private-root" else resolved_project
        return PreparedPrivateWorkspace(
            root=root,
            manifest=manifest,
            execution_workdir=execution_workdir,
            reused=True,
        )
    if existing_association is not None:
        raise ValueError("Preserved instance workspace association points to missing content.")
    root.parent.mkdir(parents=True, exist_ok=True)
    workspace_id = str(uuid4())
    bindings = tuple(
        WorkspaceBinding(
            label=item.key,
            relative_path=item.default_path,
            path_kind=item.path_kind,
            required=item.required,
            materialize=item.materialize,
        )
        for item in contract.directories
    )
    manifest = WorkspaceManifest(
        workspace_id=workspace_id,
        agent_id=agent_id,
        project_root=str(resolved_project),
        deployment_id=deployment_id,
        definition_id=definition_id,
        workspace_contract_digest=digest,
        tracking_posture=(
            "tracked-permitted" if contract.tracked_by_default else "local-untracked"
        ),
        workdir_mode=workdir_mode,
        bindings=bindings,
    )
    with tempfile.TemporaryDirectory(prefix=f".{agent_id}.", dir=root.parent) as temporary:
        staged_root = Path(temporary) / agent_id
        staged_root.mkdir()
        _write_manifest(staged_root / WORKSPACE_MANIFEST_FILENAME, manifest)
        _initialize_index(staged_root / WORKSPACE_INDEX_FILENAME, manifest)
        for binding in bindings:
            if binding.required and binding.materialize:
                path = _resolve_binding_path(staged_root, binding.relative_path)
                if binding.path_kind == "directory":
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
        _validate_bindings(staged_root, bindings, require_materialized=True)
        staged_root.rename(root)
    try:
        if manifest.tracking_posture == "local-untracked":
            _establish_local_untracked(
                project_root=resolved_project,
                workspace_root=root,
                workspace_id=workspace_id,
            )
        state_store.set_private_workspace_association(
            workspace_id=workspace_id,
            workspace_root=root,
            workspace_contract_digest=digest,
        )
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        _remove_owned_exclude(project_root=resolved_project, workspace_id=workspace_id)
        raise
    execution_workdir = root if workdir_mode == "private-root" else resolved_project
    return PreparedPrivateWorkspace(
        root=root,
        manifest=manifest,
        execution_workdir=execution_workdir,
        reused=False,
    )


def _write_manifest(path: Path, manifest: WorkspaceManifest) -> None:
    """Atomically write a stable workspace TOML manifest."""

    text = tomli_w.dumps(manifest.model_dump(mode="python"))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _initialize_index(path: Path, manifest: WorkspaceManifest) -> None:
    """Initialize the mutable workspace index."""

    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE workspace_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE workspace_records (
                record_id TEXT PRIMARY KEY,
                record_kind TEXT NOT NULL,
                semantic_label TEXT NOT NULL,
                relative_path TEXT NOT NULL UNIQUE,
                digest TEXT NOT NULL,
                revision INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        metadata = {
            "schema_version": str(WORKSPACE_INDEX_SCHEMA_VERSION),
            "generation": "1",
            "workspace_id": manifest.workspace_id,
            "agent_id": manifest.agent_id,
            "deployment_id": manifest.deployment_id,
            "workspace_contract_digest": manifest.workspace_contract_digest,
        }
        connection.executemany(
            "INSERT INTO workspace_meta(key, value) VALUES (?, ?)", metadata.items()
        )
        connection.commit()


def _resolve_binding_path(root: Path, relative_path: str) -> Path:
    """Resolve one confined binding while rejecting symlink ancestors."""

    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ValueError("Workspace path must remain relative and confined.")
    current = root.resolve()
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Workspace path crosses a symlink: {current}")
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("Workspace path escapes its private root.") from exc
    return resolved


def _validate_bindings(
    root: Path,
    bindings: tuple[WorkspaceBinding, ...],
    *,
    require_materialized: bool,
) -> None:
    """Validate unique confined bindings and path-kind compatibility."""

    relative_paths: set[str] = set()
    for binding in bindings:
        if binding.relative_path in relative_paths:
            raise ValueError(f"Workspace binding collision: {binding.relative_path}")
        relative_paths.add(binding.relative_path)
        path = _resolve_binding_path(root, binding.relative_path)
        if require_materialized and binding.required and not path.exists():
            raise ValueError(f"Required workspace binding was not materialized: {binding.label}")
        if path.exists():
            if binding.path_kind == "directory" and not path.is_dir():
                raise ValueError(f"Workspace binding requires a directory: {binding.label}")
            if binding.path_kind == "file" and not path.is_file():
                raise ValueError(f"Workspace binding requires a file: {binding.label}")


def _git_path(project_root: Path, path_name: str) -> Path | None:
    """Resolve one repository-local Git path or return None outside Git."""

    result = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "--git-path", path_name],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    path = Path(result.stdout.strip())
    return path.resolve() if path.is_absolute() else (project_root / path).resolve()


def _establish_local_untracked(
    *, project_root: Path, workspace_root: Path, workspace_id: str
) -> None:
    """Maintain one owned local exclude entry after proving the root is untracked."""

    exclude_path = _git_path(project_root, "info/exclude")
    if exclude_path is None:
        return
    tracked = subprocess.run(
        ["git", "-C", str(project_root), "ls-files", "--error-unmatch", "--", str(workspace_root)],
        check=False,
        capture_output=True,
        text=True,
    )
    if tracked.returncode == 0:
        raise ValueError("Private workspace local-untracked posture is blocked by indexed content.")
    relative = workspace_root.relative_to(project_root).as_posix()
    begin = f"{_EXCLUDE_BEGIN_PREFIX}{workspace_id}"
    end = f"{_EXCLUDE_END_PREFIX}{workspace_id}"
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.is_file() else ""
    if begin not in existing:
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        separator = "" if not existing or existing.endswith("\n") else "\n"
        exclude_path.write_text(
            f"{existing}{separator}{begin}\n/{relative}/\n{end}\n",
            encoding="utf-8",
        )
    ignored = subprocess.run(
        ["git", "-C", str(project_root), "check-ignore", "-q", "--", str(workspace_root)],
        check=False,
    )
    if ignored.returncode != 0:
        raise ValueError("Git did not recognize the private workspace as locally ignored.")


def _remove_owned_exclude(*, project_root: Path, workspace_id: str) -> None:
    """Remove only one Houmao-owned local Git exclude block."""

    exclude_path = _git_path(project_root, "info/exclude")
    if exclude_path is None or not exclude_path.is_file():
        return
    begin = f"{_EXCLUDE_BEGIN_PREFIX}{workspace_id}"
    end = f"{_EXCLUDE_END_PREFIX}{workspace_id}"
    lines = exclude_path.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    inside = False
    for line in lines:
        if line == begin:
            inside = True
            continue
        if inside and line == end:
            inside = False
            continue
        if not inside:
            kept.append(line)
    exclude_path.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")


__all__ = [
    "PRIVATE_WORKSPACE_ROOT",
    "PreparedPrivateWorkspace",
    "PrivateWorkspace",
    "WorkspaceBinding",
    "WorkspaceManifest",
    "prepare_private_workspace",
]
