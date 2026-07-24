"""Canonical per-instance runtime-variable and mindset state."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping
from uuid import uuid4

from houmao.agents.realm_controller.agent_identity import AGENT_MANIFEST_PATH_ENV_VAR
from houmao.agents.realm_controller.registry_storage import (
    is_live_agent_record_fresh,
    load_managed_agent_record_by_agent_id,
)
from houmao.project.agent_definitions import (
    InstanceContract,
    MindsetContract,
    RuntimeVariableContract,
)

INSTANCE_STATE_SCHEMA_VERSION = 1
_LAUNCH_STATES = frozenset({"preparing", "prepared", "starting", "active", "failed"})
_AUTHORITY_FRAGMENTS = (
    "system instruction",
    "ignore previous",
    "grant tool",
    "tool permission",
    "workflow gate",
    "approval evidence",
    "credential",
    "api key",
    "password",
    "secret",
)


def _utcnow_iso() -> str:
    """Return the current UTC timestamp."""

    return datetime.now(tz=UTC).isoformat()


@dataclass(frozen=True)
class VerifiedSelfIdentity:
    """Verified managed-self authority resolved from runtime state."""

    agent_id: str
    agent_name: str
    generation_id: str
    manifest_path: Path
    project_root: Path
    memory_root: Path
    backend: str
    tool: str

    @property
    def state_db(self) -> Path:
        """Return this instance's canonical state database path."""

        return self.memory_root / "state.sqlite"


@dataclass(frozen=True)
class InstancePreparationResult:
    """Result of fresh or preserved instance-state preparation."""

    state_db: Path
    attempt_id: str
    reused: bool
    variable_snapshot: dict[str, Any]
    variable_revisions: dict[str, int]


def resolve_verified_self(
    *,
    env: Mapping[str, str] | None = None,
    registry_env: Mapping[str, str] | None = None,
    current_tmux_session: str | None = None,
) -> VerifiedSelfIdentity:
    """Resolve self from a confined manifest and current registry generation."""

    effective_env = os.environ if env is None else env
    raw_pointer = effective_env.get(AGENT_MANIFEST_PATH_ENV_VAR)
    if raw_pointer is None or not raw_pointer.strip():
        raise ValueError("Managed-self authority requires the runtime manifest pointer.")
    manifest_path = Path(raw_pointer)
    if not manifest_path.is_absolute():
        raise ValueError("The runtime manifest pointer must be absolute.")
    if manifest_path.is_symlink() or manifest_path.name != "manifest.json":
        raise ValueError("The runtime manifest pointer is not a confined runtime manifest.")
    if manifest_path.parent.is_symlink() or not manifest_path.is_file():
        raise ValueError("The runtime manifest pointer is stale or unsafe.")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 4:
        raise ValueError("Unsupported runtime manifest schema.")
    agent_id = _required_manifest_string(payload, "agent_id")
    generation = _required_manifest_string(payload, "registry_generation_id")
    record = load_managed_agent_record_by_agent_id(agent_id, env=registry_env)
    if record is None:
        raise ValueError("No current managed-agent registry record matches the manifest.")
    if record.lifecycle.state != "active" or not is_live_agent_record_fresh(record):
        raise ValueError("Managed-self authority requires one current live registry record.")
    if record.generation_id != generation:
        raise ValueError("The runtime manifest uses a stale registry generation.")
    if Path(record.runtime.manifest_path).resolve() != manifest_path.resolve():
        raise ValueError("The runtime manifest pointer does not match current registry authority.")
    backend = _required_manifest_string(payload, "backend")
    tool = _required_manifest_string(payload, "tool")
    if backend != record.identity.backend or tool != record.identity.tool:
        raise ValueError("Manifest runtime identity does not match the current registry record.")
    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("Runtime manifest does not expose managed memory authority.")
    memory_raw = runtime.get("memory_root")
    if not isinstance(memory_raw, str) or not memory_raw.strip():
        raise ValueError("Runtime manifest does not expose managed memory authority.")
    memory_root = Path(memory_raw)
    if not memory_root.is_absolute() or memory_root.is_symlink():
        raise ValueError("Runtime memory authority must be one absolute non-symlink path.")
    if memory_root.name != agent_id or memory_root.parent.name != "agents":
        raise ValueError("Runtime memory authority does not match the managed-agent id.")
    try:
        overlay_root = memory_root.resolve().parents[2]
    except IndexError as exc:
        raise ValueError("Runtime memory authority is not inside a Houmao project.") from exc
    if overlay_root.name != ".houmao":
        raise ValueError("Runtime memory authority is not inside a Houmao project.")
    project_root = overlay_root.parent
    working_directory = Path(_required_manifest_string(payload, "working_directory")).resolve()
    try:
        working_directory.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError("Runtime manifest targets a foreign project.") from exc
    manifest_tmux = payload.get("tmux_session_name")
    if manifest_tmux is not None:
        if not isinstance(manifest_tmux, str) or not manifest_tmux:
            raise ValueError("Manifest tmux binding is invalid.")
        if record.terminal.current_session_name != manifest_tmux:
            raise ValueError("Manifest tmux binding does not match registry authority.")
        if current_tmux_session is not None and current_tmux_session != manifest_tmux:
            raise ValueError("Current tmux session does not match managed-self authority.")
    return VerifiedSelfIdentity(
        agent_id=agent_id,
        agent_name=record.agent_name,
        generation_id=generation,
        manifest_path=manifest_path.resolve(),
        project_root=project_root.resolve(),
        memory_root=memory_root.resolve(),
        backend=backend,
        tool=tool,
    )


class InstanceStateStore:
    """Versioned SQLite store for one managed-agent instance."""

    def __init__(self, path: Path) -> None:
        """Bind the store to one state database path."""

        self.m_path = path.resolve()

    @property
    def path(self) -> Path:
        """Return the state database path."""

        return self.m_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open one foreign-key-enabled state connection."""

        connection = sqlite3.connect(self.m_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(
        self,
        *,
        agent_id: str,
        deployment_id: str,
        instance_contract_digest: str,
        contract: InstanceContract,
        launch_values: Mapping[str, Any],
        attempt_id: str,
    ) -> None:
        """Create a fresh state store and initialize all declarations at revision one."""

        if self.m_path.exists():
            raise FileExistsError(f"Instance state already exists: {self.m_path}")
        self.m_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_schema_sql())
            timestamp = _utcnow_iso()
            metadata = {
                "schema_version": str(INSTANCE_STATE_SCHEMA_VERSION),
                "agent_id": agent_id,
                "deployment_id": deployment_id,
                "instance_contract_digest": instance_contract_digest,
                "created_at": timestamp,
            }
            connection.executemany(
                "INSERT INTO store_meta(key, value) VALUES (?, ?)", metadata.items()
            )
            connection.execute(
                """
                INSERT INTO launch_attempts(attempt_id, state, created_at, updated_at, error)
                VALUES (?, 'preparing', ?, ?, NULL)
                """,
                (attempt_id, timestamp, timestamp),
            )
            values = _resolve_runtime_values(contract.runtime_variables, launch_values)
            for runtime_declaration in contract.runtime_variables:
                connection.execute(
                    "INSERT INTO runtime_variable_declarations(key, declaration_payload) VALUES (?, ?)",
                    (
                        runtime_declaration.key,
                        json.dumps(runtime_declaration.model_dump(mode="json"), sort_keys=True),
                    ),
                )
                value = values[runtime_declaration.key]
                connection.execute(
                    """
                    INSERT INTO runtime_variable_revisions(
                        key, revision, value_payload, actor, created_at
                    ) VALUES (?, 1, ?, 'launch', ?)
                    """,
                    (runtime_declaration.key, json.dumps(value, sort_keys=True), timestamp),
                )
                connection.execute(
                    "INSERT INTO runtime_variable_current(key, revision) VALUES (?, 1)",
                    (runtime_declaration.key,),
                )
            for mindset_declaration in contract.mindsets:
                connection.execute(
                    "INSERT INTO mindset_declarations(name, declaration_payload) VALUES (?, ?)",
                    (
                        mindset_declaration.name,
                        json.dumps(mindset_declaration.model_dump(mode="json"), sort_keys=True),
                    ),
                )
                record = _initial_mindset_record(mindset_declaration)
                connection.execute(
                    """
                    INSERT INTO mindset_revisions(
                        name, revision, record_payload, actor, created_at
                    ) VALUES (?, 1, ?, 'launch', ?)
                    """,
                    (mindset_declaration.name, json.dumps(record, sort_keys=True), timestamp),
                )
                connection.execute(
                    "INSERT INTO mindset_current(name, revision) VALUES (?, 1)",
                    (mindset_declaration.name,),
                )
            connection.execute(
                "UPDATE launch_attempts SET state = 'prepared', updated_at = ? WHERE attempt_id = ?",
                (timestamp, attempt_id),
            )

    def verify_compatible(
        self,
        *,
        agent_id: str,
        deployment_id: str,
        instance_contract_digest: str,
    ) -> None:
        """Verify store schema, integrity, identity, deployment, and contract digest."""

        with self._connect() as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]) != "ok":
                raise ValueError(f"Instance state integrity check failed: {self.m_path}")
            metadata = {
                str(row["key"]): str(row["value"])
                for row in connection.execute("SELECT key, value FROM store_meta").fetchall()
            }
        version = int(metadata.get("schema_version", "0"))
        if version != INSTANCE_STATE_SCHEMA_VERSION:
            raise ValueError(
                "Instance state requires an explicit migration: "
                f"schema {version} -> {INSTANCE_STATE_SCHEMA_VERSION}"
            )
        expected = {
            "agent_id": agent_id,
            "deployment_id": deployment_id,
            "instance_contract_digest": instance_contract_digest,
        }
        mismatches = [key for key, value in expected.items() if metadata.get(key) != value]
        if mismatches:
            raise ValueError("Preserved instance state is incompatible: " + ", ".join(mismatches))

    def begin_relaunch_attempt(self) -> str:
        """Create one new preserved-instance launch preparation attempt."""

        attempt_id = str(uuid4())
        timestamp = _utcnow_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO launch_attempts(attempt_id, state, created_at, updated_at, error)
                VALUES (?, 'preparing', ?, ?, NULL)
                """,
                (attempt_id, timestamp, timestamp),
            )
            connection.execute(
                "UPDATE launch_attempts SET state = 'prepared', updated_at = ? WHERE attempt_id = ?",
                (timestamp, attempt_id),
            )
        return attempt_id

    def set_launch_state(self, attempt_id: str, state: str, *, error: str | None = None) -> None:
        """Advance or fail one launch attempt."""

        if state not in _LAUNCH_STATES:
            raise ValueError(f"Unsupported launch-attempt state: {state}")
        with self._connect() as connection:
            current = connection.execute(
                "SELECT state FROM launch_attempts WHERE attempt_id = ?", (attempt_id,)
            ).fetchone()
            if current is None:
                raise FileNotFoundError(f"Launch attempt was not found: {attempt_id}")
            allowed = {
                "preparing": {"prepared", "failed"},
                "prepared": {"starting", "failed"},
                "starting": {"active", "failed"},
                "active": set(),
                "failed": set(),
            }[str(current["state"])]
            if state != current["state"] and state not in allowed:
                raise ValueError(
                    f"Invalid launch-attempt transition: {current['state']} -> {state}"
                )
            connection.execute(
                """
                UPDATE launch_attempts SET state = ?, updated_at = ?, error = ?
                WHERE attempt_id = ?
                """,
                (state, _utcnow_iso(), error, attempt_id),
            )

    def runtime_variables(self) -> list[dict[str, Any]]:
        """Return current variable values, declarations, and revisions."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT d.key, d.declaration_payload, c.revision, r.value_payload, r.created_at
                FROM runtime_variable_declarations AS d
                INNER JOIN runtime_variable_current AS c ON c.key = d.key
                INNER JOIN runtime_variable_revisions AS r
                    ON r.key = c.key AND r.revision = c.revision
                ORDER BY d.key
                """
            ).fetchall()
        return [
            {
                "key": str(row["key"]),
                "revision": int(row["revision"]),
                "value": json.loads(str(row["value_payload"])),
                "declaration": json.loads(str(row["declaration_payload"])),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def runtime_variable(self, key: str) -> dict[str, Any]:
        """Return one current runtime variable."""

        for item in self.runtime_variables():
            if item["key"] == key:
                return item
        raise FileNotFoundError(f"Runtime variable `{key}` was not found.")

    def runtime_variable_snapshot(self) -> tuple[dict[str, Any], dict[str, int]]:
        """Read one transactionally consistent variable value snapshot."""

        with self._connect() as connection:
            connection.execute("BEGIN")
            rows = connection.execute(
                """
                SELECT c.key, c.revision, r.value_payload
                FROM runtime_variable_current AS c
                INNER JOIN runtime_variable_revisions AS r
                    ON r.key = c.key AND r.revision = c.revision
                ORDER BY c.key
                """
            ).fetchall()
        return (
            {str(row["key"]): json.loads(str(row["value_payload"])) for row in rows},
            {str(row["key"]): int(row["revision"]) for row in rows},
        )

    def mutate_runtime_variable(
        self,
        *,
        key: str,
        value: Any,
        expected_revision: int,
        actor: str,
    ) -> dict[str, Any]:
        """Compare-and-set one explicit instance variable."""

        with self._connect() as connection:
            declaration_row = connection.execute(
                "SELECT declaration_payload FROM runtime_variable_declarations WHERE key = ?",
                (key,),
            ).fetchone()
            current_row = connection.execute(
                "SELECT revision FROM runtime_variable_current WHERE key = ?", (key,)
            ).fetchone()
            if declaration_row is None or current_row is None:
                raise FileNotFoundError(f"Runtime variable `{key}` was not found.")
            declaration = RuntimeVariableContract.model_validate(
                json.loads(str(declaration_row["declaration_payload"]))
            )
            if not declaration.mutable:
                raise ValueError(f"Runtime variable `{key}` is immutable.")
            current_revision = int(current_row["revision"])
            if current_revision != expected_revision:
                raise ValueError(
                    f"Stale runtime-variable revision: expected {expected_revision}, "
                    f"current {current_revision}."
                )
            _validate_runtime_value(declaration, value)
            new_revision = current_revision + 1
            timestamp = _utcnow_iso()
            connection.execute(
                """
                INSERT INTO runtime_variable_revisions(
                    key, revision, value_payload, actor, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (key, new_revision, json.dumps(value, sort_keys=True), actor, timestamp),
            )
            connection.execute(
                "UPDATE runtime_variable_current SET revision = ? WHERE key = ?",
                (new_revision, key),
            )
        return {"key": key, "revision": new_revision, "value": value}

    def mindset(self, name: str) -> dict[str, Any]:
        """Return one current mindset declaration and record revision."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT d.declaration_payload, c.revision, r.record_payload, r.created_at
                FROM mindset_declarations AS d
                INNER JOIN mindset_current AS c ON c.name = d.name
                INNER JOIN mindset_revisions AS r
                    ON r.name = c.name AND r.revision = c.revision
                WHERE d.name = ?
                """,
                (name,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"Mindset `{name}` was not found.")
        return {
            "name": name,
            "revision": int(row["revision"]),
            "declaration": json.loads(str(row["declaration_payload"])),
            "record": json.loads(str(row["record_payload"])),
            "created_at": str(row["created_at"]),
        }

    def mutate_mindset(
        self,
        *,
        name: str,
        record: dict[str, Any],
        expected_revision: int,
        actor: str,
    ) -> dict[str, Any]:
        """Compare-and-set one explicit named mindset and return its semantic diff."""

        with self._connect() as connection:
            declaration_row = connection.execute(
                "SELECT declaration_payload FROM mindset_declarations WHERE name = ?",
                (name,),
            ).fetchone()
            current_row = connection.execute(
                """
                SELECT c.revision, r.record_payload
                FROM mindset_current AS c
                INNER JOIN mindset_revisions AS r
                    ON r.name = c.name AND r.revision = c.revision
                WHERE c.name = ?
                """,
                (name,),
            ).fetchone()
            if declaration_row is None or current_row is None:
                raise FileNotFoundError(f"Mindset `{name}` was not found.")
            declaration = MindsetContract.model_validate(
                json.loads(str(declaration_row["declaration_payload"]))
            )
            current_revision = int(current_row["revision"])
            if current_revision != expected_revision:
                raise ValueError(
                    f"Stale mindset revision: expected {expected_revision}, "
                    f"current {current_revision}."
                )
            normalized = _validate_mindset_record(declaration, record)
            previous = json.loads(str(current_row["record_payload"]))
            new_revision = current_revision + 1
            connection.execute(
                """
                INSERT INTO mindset_revisions(name, revision, record_payload, actor, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    new_revision,
                    json.dumps(normalized, sort_keys=True),
                    actor,
                    _utcnow_iso(),
                ),
            )
            connection.execute(
                "UPDATE mindset_current SET revision = ? WHERE name = ?",
                (new_revision, name),
            )
        return {
            "name": name,
            "revision": new_revision,
            "record": normalized,
            "diff": _semantic_record_diff(previous, normalized),
        }

    def mindset_snapshot_for_skill(self, skill_name: str) -> dict[str, Any]:
        """Return immutable current revisions for every mindset required by one skill."""

        with self._connect() as connection:
            connection.execute("BEGIN")
            rows = connection.execute(
                """
                SELECT d.name, d.declaration_payload, c.revision, r.record_payload
                FROM mindset_declarations AS d
                INNER JOIN mindset_current AS c ON c.name = d.name
                INNER JOIN mindset_revisions AS r
                    ON r.name = c.name AND r.revision = c.revision
                ORDER BY d.name
                """
            ).fetchall()
        snapshots: list[dict[str, Any]] = []
        for row in rows:
            declaration = json.loads(str(row["declaration_payload"]))
            if skill_name not in declaration.get("required_skills", []):
                continue
            snapshots.append(
                {
                    "name": str(row["name"]),
                    "revision": int(row["revision"]),
                    "record": json.loads(str(row["record_payload"])),
                }
            )
        if not snapshots:
            raise FileNotFoundError(
                f"No declared mindset snapshot is bound to skill `{skill_name}`."
            )
        return {"skill_name": skill_name, "mindsets": snapshots}

    def set_private_workspace_association(
        self,
        *,
        workspace_id: str,
        workspace_root: Path,
        workspace_contract_digest: str,
    ) -> None:
        """Persist the compatible private-workspace association before process start."""

        with self._connect() as connection:
            existing = connection.execute(
                "SELECT workspace_id, workspace_root, workspace_contract_digest "
                "FROM private_workspace_association WHERE singleton = 1"
            ).fetchone()
            if existing is not None:
                expected = (
                    workspace_id,
                    str(workspace_root.resolve()),
                    workspace_contract_digest,
                )
                actual = (
                    str(existing["workspace_id"]),
                    str(existing["workspace_root"]),
                    str(existing["workspace_contract_digest"]),
                )
                if actual != expected:
                    raise ValueError("Preserved instance has an incompatible private workspace.")
                return
            connection.execute(
                """
                INSERT INTO private_workspace_association(
                    singleton, workspace_id, workspace_root, workspace_contract_digest, created_at
                ) VALUES (1, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    str(workspace_root.resolve()),
                    workspace_contract_digest,
                    _utcnow_iso(),
                ),
            )

    def private_workspace_association(self) -> dict[str, str] | None:
        """Return the persisted private-workspace association when present."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT workspace_id, workspace_root, workspace_contract_digest, created_at "
                "FROM private_workspace_association WHERE singleton = 1"
            ).fetchone()
        if row is None:
            return None
        return {
            "workspace_id": str(row["workspace_id"]),
            "workspace_root": str(row["workspace_root"]),
            "workspace_contract_digest": str(row["workspace_contract_digest"]),
            "created_at": str(row["created_at"]),
        }

    def clear_private_workspace_association(self, *, expected_workspace_id: str) -> None:
        """Remove one exact association after confirmed workspace cleanup."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT workspace_id FROM private_workspace_association WHERE singleton = 1"
            ).fetchone()
            if row is None:
                raise FileNotFoundError("This instance has no private-workspace association.")
            if str(row["workspace_id"]) != expected_workspace_id:
                raise ValueError("Private-workspace association changed before cleanup completed.")
            connection.execute("DELETE FROM private_workspace_association WHERE singleton = 1")


def prepare_instance_state(
    *,
    state_db: Path,
    agent_id: str,
    deployment_id: str,
    instance_contract_digest: str,
    contract: InstanceContract,
    launch_values: Mapping[str, Any],
) -> InstancePreparationResult:
    """Create fresh state or revalidate and reuse a compatible preserved instance."""

    store = InstanceStateStore(state_db)
    reused = state_db.exists()
    if reused:
        store.verify_compatible(
            agent_id=agent_id,
            deployment_id=deployment_id,
            instance_contract_digest=instance_contract_digest,
        )
        if launch_values:
            raise ValueError(
                "Preserved instances retain current runtime values; launch overrides are fresh-only."
            )
        attempt_id = store.begin_relaunch_attempt()
    else:
        attempt_id = str(uuid4())
        temporary = state_db.with_name(f".{state_db.name}.{attempt_id}.preparing")
        temporary_store = InstanceStateStore(temporary)
        try:
            temporary_store.initialize(
                agent_id=agent_id,
                deployment_id=deployment_id,
                instance_contract_digest=instance_contract_digest,
                contract=contract,
                launch_values=launch_values,
                attempt_id=attempt_id,
            )
            temporary.replace(state_db)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        store = InstanceStateStore(state_db)
    values, revisions = store.runtime_variable_snapshot()
    return InstancePreparationResult(
        state_db=state_db.resolve(),
        attempt_id=attempt_id,
        reused=reused,
        variable_snapshot=values,
        variable_revisions=revisions,
    )


def render_instance_snapshot(text: str, snapshot: Mapping[str, Any]) -> str:
    """Render prompt or memo instance markers from one launch snapshot."""

    rendered = text
    for key, value in snapshot.items():
        rendered = rendered.replace(f"{{{{houmao.instance.{key}}}}}", str(value))
    if "{{houmao.instance." in rendered:
        raise ValueError("Prompt or memo contains an unresolved instance-state marker.")
    return rendered


def migrate_instance_state(path: Path) -> dict[str, Any]:
    """Validate current state or report that no automatic historical migration exists."""

    if not path.is_file():
        raise FileNotFoundError(f"Instance state was not found: {path}")
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT value FROM store_meta WHERE key = 'schema_version'"
        ).fetchone()
    version = int(row[0]) if row is not None else 0
    if version != INSTANCE_STATE_SCHEMA_VERSION:
        raise ValueError(
            f"No automatic instance-state migration is available for schema {version}."
        )
    return {"path": str(path.resolve()), "schema_version": version, "migrated": False}


def _schema_sql() -> str:
    """Return the version-one instance-state schema."""

    return """
    CREATE TABLE store_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE TABLE launch_attempts (
        attempt_id TEXT PRIMARY KEY,
        state TEXT NOT NULL CHECK(state IN ('preparing','prepared','starting','active','failed')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        error TEXT
    );
    CREATE TABLE runtime_variable_declarations (
        key TEXT PRIMARY KEY,
        declaration_payload TEXT NOT NULL
    );
    CREATE TABLE runtime_variable_revisions (
        key TEXT NOT NULL REFERENCES runtime_variable_declarations(key) ON DELETE RESTRICT,
        revision INTEGER NOT NULL CHECK(revision > 0),
        value_payload TEXT NOT NULL,
        actor TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(key, revision)
    );
    CREATE TABLE runtime_variable_current (
        key TEXT PRIMARY KEY REFERENCES runtime_variable_declarations(key) ON DELETE RESTRICT,
        revision INTEGER NOT NULL
    );
    CREATE TABLE mindset_declarations (
        name TEXT PRIMARY KEY,
        declaration_payload TEXT NOT NULL
    );
    CREATE TABLE mindset_revisions (
        name TEXT NOT NULL REFERENCES mindset_declarations(name) ON DELETE RESTRICT,
        revision INTEGER NOT NULL CHECK(revision > 0),
        record_payload TEXT NOT NULL,
        actor TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(name, revision)
    );
    CREATE TABLE mindset_current (
        name TEXT PRIMARY KEY REFERENCES mindset_declarations(name) ON DELETE RESTRICT,
        revision INTEGER NOT NULL
    );
    CREATE TABLE private_workspace_association (
        singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
        workspace_id TEXT NOT NULL,
        workspace_root TEXT NOT NULL,
        workspace_contract_digest TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """


def _required_manifest_string(payload: dict[str, Any], key: str) -> str:
    """Read one required non-empty manifest string."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Runtime manifest is missing `{key}` authority.")
    return value


def _resolve_runtime_values(
    declarations: tuple[RuntimeVariableContract, ...],
    supplied: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve fresh launch values and declaration defaults."""

    by_key = {item.key: item for item in declarations}
    unknown = sorted(set(supplied) - set(by_key))
    if unknown:
        raise ValueError(f"Unknown runtime variable(s): {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for key, declaration in by_key.items():
        if key in supplied:
            value = supplied[key]
        elif declaration.default is not None:
            value = declaration.default
        elif declaration.required:
            raise ValueError(f"Required runtime variable `{key}` was not supplied.")
        else:
            value = None
        _validate_runtime_value(declaration, value)
        values[key] = value
    return values


def _validate_runtime_value(declaration: RuntimeVariableContract, value: Any) -> None:
    """Validate one runtime value without accepting credential-like records."""

    if isinstance(value, str) and any(
        fragment in value.casefold() for fragment in _AUTHORITY_FRAGMENTS
    ):
        raise ValueError("Runtime variables are non-secret behavior data.")
    if value is None and not declaration.required:
        return
    valid = {
        "string": isinstance(value, str),
        "enum": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }[declaration.value_type]
    if not valid:
        raise ValueError(
            f"Runtime variable `{declaration.key}` requires `{declaration.value_type}`."
        )
    if declaration.value_type == "enum" and value not in declaration.choices:
        raise ValueError(
            f"Runtime variable `{declaration.key}` must be one of {list(declaration.choices)}."
        )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if declaration.minimum is not None and value < declaration.minimum:
            raise ValueError(f"Runtime variable `{declaration.key}` is below its minimum.")
        if declaration.maximum is not None and value > declaration.maximum:
            raise ValueError(f"Runtime variable `{declaration.key}` is above its maximum.")


def _initial_mindset_record(declaration: MindsetContract) -> dict[str, Any]:
    """Build the revision-one record from one immutable declaration."""

    return {
        "questions": [
            {
                "question_id": question.question_id,
                "question": question.text,
                "answer": "",
                "note": "",
            }
            for question in declaration.questions
        ]
    }


def _validate_mindset_record(
    declaration: MindsetContract, record: dict[str, Any]
) -> dict[str, Any]:
    """Validate one low-authority record against stable question bounds."""

    raw_questions = record.get("questions")
    if not isinstance(raw_questions, list):
        raise ValueError("Mindset record requires a `questions` list.")
    by_id = {question.question_id: question for question in declaration.questions}
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in raw_questions:
        if not isinstance(raw, dict):
            raise ValueError("Mindset question records must be mappings.")
        question_id = raw.get("question_id")
        question_text = raw.get("question")
        answer = raw.get("answer", "")
        note = raw.get("note", "")
        if not isinstance(question_id, str) or question_id not in by_id:
            raise ValueError(f"Unknown mindset question id: {question_id!r}")
        if question_id in seen:
            raise ValueError(f"Duplicate mindset question id: {question_id}")
        if (
            not isinstance(question_text, str)
            or not isinstance(answer, str)
            or not isinstance(note, str)
        ):
            raise ValueError("Mindset questions, answers, and notes must be strings.")
        question = by_id[question_id]
        if (
            not question_text
            or len(question_text) > question.max_question_length
            or len(answer) > question.max_answer_length
            or len(note) > question.max_note_length
        ):
            raise ValueError(f"Mindset content exceeds bounds for `{question_id}`.")
        if any(
            fragment in f"{question_text}\n{answer}\n{note}".casefold()
            for fragment in _AUTHORITY_FRAGMENTS
        ):
            raise ValueError(
                "Mindsets cannot carry instruction, tool, gate, or credential authority."
            )
        normalized.append(
            {
                "question_id": question_id,
                "question": question_text,
                "answer": answer,
                "note": note,
            }
        )
        seen.add(question_id)
    if seen != set(by_id):
        raise ValueError("Mindset record must preserve every declared question id.")
    return {"questions": normalized}


def _semantic_record_diff(
    previous: dict[str, Any], current: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return changed answer and note fields by stable question id."""

    previous_by_id = {item["question_id"]: item for item in previous.get("questions", [])}
    changes: list[dict[str, Any]] = []
    for item in current.get("questions", []):
        old = previous_by_id.get(item["question_id"], {})
        for field in ("question", "answer", "note"):
            if old.get(field) != item.get(field):
                changes.append(
                    {
                        "question_id": item["question_id"],
                        "field": field,
                        "before": old.get(field),
                        "after": item.get(field),
                    }
                )
    return changes


__all__ = [
    "INSTANCE_STATE_SCHEMA_VERSION",
    "InstancePreparationResult",
    "InstanceStateStore",
    "VerifiedSelfIdentity",
    "migrate_instance_state",
    "prepare_instance_state",
    "render_instance_snapshot",
    "resolve_verified_self",
]
