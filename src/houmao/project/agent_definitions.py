"""Author, materialize, plan, and apply reusable Houmao Agent Definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import tempfile
import tomllib
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import tomli_w

from houmao.project.catalog import ProjectCatalog
from houmao.project.overlay import HoumaoProjectOverlay

OVERVIEW_FILENAME = "agent-def-overview.md"
INTERPRETATION_FILENAME = "interpretation.md"
MATERIALIZATION_FILENAME = "materialization.toml"
VALIDATION_FILENAME = "validation.json"
APPROVAL_FILENAME = "approval.toml"
DEFINITION_SCHEMA = "houmao-agent-definition.v1"
DEPLOY_CONTRACT_SCHEMA = "houmao-agent-deploy-contract.v1"
INSTANCE_CONTRACT_SCHEMA = "houmao-agent-instance-contract.v1"
MATERIALIZATION_SCHEMA = "houmao-agent-materialization.v1"
REQUEST_SCHEMA = "houmao-agent-deployment-request.v1"
PLAN_SCHEMA = "houmao-agent-deployment-plan.v1"
_TEXT_MARKER_RE = re.compile(r"\{\{houmao\.deploy\.([a-z][a-z0-9_]*)\}\}")
_INSTANCE_MARKER_RE = re.compile(r"\{\{houmao\.instance\.([a-z][a-z0-9_]*)\}\}")
_ANY_MARKER_RE = re.compile(r"\{\{[^{}]+\}\}")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_SAFE_SOURCE_SUFFIXES = frozenset({".md", ".txt", ".toml", ".json", ".yaml", ".yml"})
_RESERVED_SKILL_PREFIXES = ("houmao-", "openspec-")
_TEXT_BINDING_TARGETS = frozenset({"role_prompt", "memo_seed"})
_FIELD_BINDING_TARGETS = frozenset(
    {"specialist.name", "specialist.tool", "profile.name", "profile.workdir"}
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"""(?im)^\s*["']?(api[_-]?key|password|secret|credential[_-]?secret|auth[_-]?token)["']?\s*[:=]\s*(.+?)\s*$"""
)
_BUILTIN_DEFINITION_PACKAGE = "houmao.project.assets"
_BUILTIN_DEFINITION_ROOT = "agent_definitions"
_BUILTIN_DEFINITION_PREFIX = "builtin:"


def _utcnow_iso() -> str:
    """Return the current UTC timestamp in stable ISO form."""

    return datetime.now(tz=UTC).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    """Return a tagged SHA-256 digest."""

    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _canonical_json(payload: object) -> bytes:
    """Serialize one value to canonical UTF-8 JSON bytes."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _write_text(path: Path, text: str) -> None:
    """Write UTF-8 text after creating its parent directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    """Write stable JSON after creating its parent directory."""

    _write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_toml(path: Path, payload: dict[str, Any]) -> None:
    """Write deterministic TOML after creating its parent directory."""

    _write_text(path, tomli_w.dumps(payload))


def _require_confined_path(root: Path, relative: str, *, kind: Literal["file", "dir"]) -> Path:
    """Resolve one relative path beneath a root and reject unsafe filesystem objects."""

    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Path must remain beneath `{root}`: {relative}")
    lexical = root / candidate
    if lexical.is_symlink():
        raise ValueError(f"Symlinks are not accepted: {lexical}")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path escapes `{root}`: {relative}") from exc
    if kind == "file":
        if not resolved.is_file():
            raise ValueError(f"Referenced file was not found: {resolved}")
        mode = resolved.stat().st_mode
        if not stat.S_ISREG(mode):
            raise ValueError(f"Referenced path is not a regular file: {resolved}")
    elif not resolved.is_dir():
        raise ValueError(f"Referenced directory was not found: {resolved}")
    return resolved


@dataclass(frozen=True)
class AgentDefinitionWorkspace:
    """Typed paths for one Agent Definition authoring workspace."""

    root: Path

    @property
    def source_root(self) -> Path:
        """Return the human-owned intent source root."""

        return self.root.resolve() / "intent" / "src"

    @property
    def overview_path(self) -> Path:
        """Return the only required source path."""

        return self.source_root / OVERVIEW_FILENAME

    @property
    def derived_root(self) -> Path:
        """Return the operator-owned derived-intent root."""

        return self.root.resolve() / "intent" / "derived"

    @property
    def interpretation_path(self) -> Path:
        """Return the readable interpretation path."""

        return self.derived_root / INTERPRETATION_FILENAME

    @property
    def materialization_path(self) -> Path:
        """Return the normalized machine authority path."""

        return self.derived_root / MATERIALIZATION_FILENAME

    @property
    def materials_root(self) -> Path:
        """Return the approved derived-material root."""

        return self.derived_root / "materials"

    @property
    def validation_path(self) -> Path:
        """Return the derivation validation record path."""

        return self.derived_root / VALIDATION_FILENAME

    @property
    def approval_path(self) -> Path:
        """Return the digest-bound human approval path."""

        return self.derived_root / APPROVAL_FILENAME

    @property
    def definition_root(self) -> Path:
        """Return the default materialized revision root."""

        return self.root.resolve() / "agent-definition"


class DeployBinding(BaseModel):
    """One typed deployment-input target binding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target: str = Field(min_length=1)
    mode: Literal["text", "field"]
    marker: str | None = None

    @model_validator(mode="after")
    def validate_marker(self) -> DeployBinding:
        """Validate exact marker use for text targets."""

        if self.mode == "text":
            if self.target not in _TEXT_BINDING_TARGETS:
                raise ValueError(f"Unknown text binding target `{self.target}`.")
            if self.marker is None or _TEXT_MARKER_RE.fullmatch(self.marker) is None:
                raise ValueError(
                    "Text bindings require one exact `{{houmao.deploy.<key>}}` marker."
                )
        else:
            if self.target not in _FIELD_BINDING_TARGETS:
                raise ValueError(f"Unknown structured binding target `{self.target}`.")
            if self.marker is not None:
                raise ValueError("Structured field bindings do not accept text markers.")
        return self


class DeployInput(BaseModel):
    """One declared deployment input and its target bindings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    value_type: Literal["string", "integer", "number", "boolean", "enum"] = "string"
    required: bool = True
    default: str | int | float | bool | None = None
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    bindings: tuple[DeployBinding, ...] = ()

    @model_validator(mode="after")
    def validate_contract(self) -> DeployInput:
        """Validate enum, default, and binding consistency."""

        if not self.bindings:
            raise ValueError(f"Deployment input `{self.key}` must have at least one binding.")
        if self.value_type == "enum" and not self.choices:
            raise ValueError(f"Enum input `{self.key}` requires choices.")
        if self.value_type != "enum" and self.choices:
            raise ValueError(f"Only enum input `{self.key}` may declare choices.")
        for binding in self.bindings:
            if binding.mode == "text" and binding.marker != f"{{{{houmao.deploy.{self.key}}}}}":
                raise ValueError(f"Text binding marker does not match input `{self.key}`.")
        if self.default is not None:
            _validate_input_value(self, self.default)
        return self


class DefinitionDocument(BaseModel):
    """Portable definition identity and component references."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-definition.v1"] = "houmao-agent-definition.v1"
    definition_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    revision_id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    purpose: str = Field(min_length=1)
    revision_digest: str = ""
    role_prompt: str = "assets/prompts/system.md"
    memo_seed: str = "assets/memo/houmao-memo.md"
    skills: tuple[str, ...] = ()


class DeployContract(BaseModel):
    """Typed deploy-time input contract for one revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-deploy-contract.v1"] = "houmao-agent-deploy-contract.v1"
    inputs: tuple[DeployInput, ...] = ()

    @field_validator("inputs")
    @classmethod
    def unique_inputs(cls, value: tuple[DeployInput, ...]) -> tuple[DeployInput, ...]:
        """Reject duplicate input keys."""

        keys = [item.key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("Deployment input keys must be unique.")
        return value


class RuntimeVariableContract(BaseModel):
    """One per-instance runtime-variable declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    value_type: Literal["string", "integer", "number", "boolean", "enum"] = "string"
    required: bool = False
    default: str | int | float | bool | None = None
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    consumers: tuple[str, ...] = ()
    mutable: bool = True
    secret: bool = False

    @model_validator(mode="after")
    def validate_variable(self) -> RuntimeVariableContract:
        """Reject secret state and validate defaults and consumers."""

        if self.secret:
            raise ValueError(
                f"Runtime variable `{self.key}` cannot store secrets; use Houmao credentials."
            )
        if self.value_type == "enum" and not self.choices:
            raise ValueError(f"Enum runtime variable `{self.key}` requires choices.")
        if self.value_type != "enum" and self.choices:
            raise ValueError(f"Only enum runtime variable `{self.key}` may declare choices.")
        if self.default is not None:
            valid = {
                "string": isinstance(self.default, str),
                "enum": isinstance(self.default, str),
                "integer": isinstance(self.default, int) and not isinstance(self.default, bool),
                "number": isinstance(self.default, (int, float))
                and not isinstance(self.default, bool),
                "boolean": isinstance(self.default, bool),
            }[self.value_type]
            if not valid:
                raise ValueError(
                    f"Runtime variable `{self.key}` default requires `{self.value_type}`."
                )
            if self.value_type == "enum" and self.default not in self.choices:
                raise ValueError(
                    f"Runtime variable `{self.key}` default must be one of {list(self.choices)}."
                )
            if isinstance(self.default, (int, float)) and not isinstance(self.default, bool):
                if self.minimum is not None and self.default < self.minimum:
                    raise ValueError(f"Runtime variable `{self.key}` default is below its minimum.")
                if self.maximum is not None and self.default > self.maximum:
                    raise ValueError(f"Runtime variable `{self.key}` default is above its maximum.")
        if len(self.consumers) != len(set(self.consumers)):
            raise ValueError(f"Runtime variable `{self.key}` has duplicate consumers.")
        for consumer in self.consumers:
            if consumer in {"prompt", "memo"}:
                continue
            kind, separator, target = consumer.partition(":")
            if kind != "skill" or not separator or not target:
                raise ValueError(
                    f"Runtime variable `{self.key}` has unknown consumer `{consumer}`."
                )
        return self


class MindsetQuestionContract(BaseModel):
    """One stable question in a named mindset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    text: str = Field(min_length=1)
    max_question_length: int = Field(default=4000, ge=1, le=100_000)
    max_answer_length: int = Field(default=4000, ge=1, le=100_000)
    max_note_length: int = Field(default=4000, ge=1, le=100_000)


class MindsetContract(BaseModel):
    """One named mindset questionnaire declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    questions: tuple[MindsetQuestionContract, ...] = ()
    required_skills: tuple[str, ...] = ()
    user_editable: bool = True
    expose_in_private_workspace: bool = False

    @model_validator(mode="after")
    def validate_mindset(self) -> MindsetContract:
        """Reject duplicate questions and authority-bearing declaration text."""

        ids = [question.question_id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Mindset `{self.name}` has duplicate question ids.")
        for question in self.questions:
            if len(question.text) > question.max_question_length:
                raise ValueError(
                    f"Mindset `{self.name}` question `{question.question_id}` exceeds "
                    "its declared question-text bound."
                )
            _reject_authority_bearing_mindset_text(question.text)
        return self


class WorkspaceDirectoryContract(BaseModel):
    """One semantic directory in an optional private workspace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=r"^workspace\.[a-z][a-z0-9_.-]*$")
    default_path: str = Field(min_length=1)
    description: str = ""
    path_kind: Literal["directory", "file"] = "directory"
    required: bool = True
    materialize: bool = True


class PrivateWorkspaceContract(BaseModel):
    """Optional private-workspace policy for one definition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["disabled", "optional", "required"] = "disabled"
    default_enabled: bool = False
    workdir_mode: Literal["project-root", "private-root"] = "project-root"
    tracked_by_default: bool = False
    directories: tuple[WorkspaceDirectoryContract, ...] = ()

    @model_validator(mode="after")
    def validate_workspace_contract(self) -> PrivateWorkspaceContract:
        """Validate activation defaults and safe relative semantic bindings."""

        if self.mode == "disabled" and (self.default_enabled or self.directories):
            raise ValueError("Disabled private workspaces cannot select or declare paths.")
        if self.mode == "required" and not self.default_enabled:
            raise ValueError("Required private workspaces must be enabled by default.")
        if self.workdir_mode == "private-root" and self.mode == "disabled":
            raise ValueError("Private-root workdir requires an enabled workspace contract.")
        keys = [item.key for item in self.directories]
        if len(keys) != len(set(keys)):
            raise ValueError("Private-workspace semantic labels must be unique.")
        paths: set[str] = set()
        for item in self.directories:
            candidate = Path(item.default_path)
            if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
                raise ValueError(
                    f"Workspace binding `{item.key}` must use one confined relative path."
                )
            normalized = candidate.as_posix()
            if normalized in paths:
                raise ValueError(f"Workspace path collision: {normalized}")
            paths.add(normalized)
        return self


class InstanceContract(BaseModel):
    """Per-instance extension boundary for one definition revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-instance-contract.v1"] = (
        "houmao-agent-instance-contract.v1"
    )
    contract_digest: str = ""
    runtime_variables: tuple[RuntimeVariableContract, ...] = ()
    mindsets: tuple[MindsetContract, ...] = ()
    private_workspace: PrivateWorkspaceContract = Field(default_factory=PrivateWorkspaceContract)

    @model_validator(mode="after")
    def validate_instance_contract(self) -> InstanceContract:
        """Reject duplicate state keys and unknown mindset skill bindings."""

        variable_keys = [item.key for item in self.runtime_variables]
        if len(variable_keys) != len(set(variable_keys)):
            raise ValueError("Runtime-variable keys must be unique.")
        mindset_names = [item.name for item in self.mindsets]
        if len(mindset_names) != len(set(mindset_names)):
            raise ValueError("Mindset names must be unique.")
        return self


class MaterializationSpec(BaseModel):
    """Normalized machine input for materializing one revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-materialization.v1"] = "houmao-agent-materialization.v1"
    definition_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    revision_id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    purpose: str = Field(min_length=1)
    role_prompt_source: str
    memo_seed_source: str
    role_prompt: str
    memo_seed: str
    skills: tuple[str, ...] = ()
    deploy_inputs: tuple[DeployInput, ...] = ()
    instance: InstanceContract = Field(default_factory=InstanceContract)


class DeploymentRequest(BaseModel):
    """Operator-authored, non-secret request for one Agent Deployment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-deployment-request.v1"] = (
        "houmao-agent-deployment-request.v1"
    )
    definition_path: str
    definition_id: str
    revision_id: str
    revision_digest: str
    target_project: str
    deployment_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    specialist_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    profile_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    tool: str
    credential: str
    workdir: str
    provider: str = "default"
    setup: str = "default"
    values: dict[str, str | int | float | bool] = Field(default_factory=dict)
    posture: dict[str, Any] = Field(default_factory=dict)
    private_workspace_enabled: bool | None = None
    workspace_workdir_mode: Literal["project-root", "private-root"] | None = None
    update_existing: bool = False


class RenderedArtifact(BaseModel):
    """One rendered file recorded by a Deployment Plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    digest: str


class DeploymentPlan(BaseModel):
    """Deterministic, integrity-protected plan for applying one deployment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["houmao-agent-deployment-plan.v1"] = "houmao-agent-deployment-plan.v1"
    plan_id: str
    plan_digest: str = ""
    request_digest: str
    definition_id: str
    revision_id: str
    revision_digest: str
    instance_contract_digest: str
    target_project: str
    project_precondition_digest: str
    deployment_name: str
    specialist_name: str
    profile_name: str
    tool: str
    credential: str
    provider: str
    setup: str
    workdir: str
    values: dict[str, str | int | float | bool]
    posture: dict[str, Any]
    private_workspace_enabled: bool
    workspace_workdir_mode: Literal["project-root", "private-root"]
    workspace_contract_digest: str | None = None
    update_existing: bool = False
    skill_names: tuple[str, ...]
    rendered_artifacts: tuple[RenderedArtifact, ...]
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class RevisionValidation:
    """Loaded and validated Agent Definition Revision."""

    root: Path
    definition: DefinitionDocument
    deploy_contract: DeployContract
    instance_contract: InstanceContract
    revision_digest: str
    instance_contract_digest: str


def init_intent(workspace_root: Path, *, overview_text: str = "") -> AgentDefinitionWorkspace:
    """Initialize one workspace with only its required source entrypoint."""

    workspace = AgentDefinitionWorkspace(workspace_root.resolve())
    if workspace.overview_path.exists():
        raise FileExistsError(f"Overview already exists: {workspace.overview_path}")
    workspace.source_root.mkdir(parents=True, exist_ok=True)
    _write_text(workspace.overview_path, overview_text)
    return workspace


def source_set(workspace: AgentDefinitionWorkspace) -> tuple[Path, ...]:
    """Resolve the overview and only its confined Markdown-linked supporting files."""

    overview = _require_confined_path(workspace.source_root, OVERVIEW_FILENAME, kind="file")
    paths = [overview]
    for raw_reference in _MARKDOWN_LINK_RE.findall(overview.read_text(encoding="utf-8")):
        reference = raw_reference.split("#", 1)[0].strip()
        if not reference or "://" in reference:
            continue
        candidate = _require_confined_path(workspace.source_root, reference, kind="file")
        if candidate.suffix.lower() not in _SAFE_SOURCE_SUFFIXES:
            raise ValueError(f"Unsupported supporting-file kind: {candidate}")
        paths.append(candidate)
    return tuple(dict.fromkeys(paths))


def digest_paths(paths: tuple[Path, ...], *, root: Path) -> str:
    """Digest a stable ordered set of confined regular files."""

    records = [
        {
            "path": path.resolve().relative_to(root.resolve()).as_posix(),
            "digest": _sha256_bytes(path.read_bytes()),
        }
        for path in sorted(paths)
    ]
    return _sha256_bytes(_canonical_json(records))


def derive_intent(
    workspace: AgentDefinitionWorkspace,
    *,
    interpretation_text: str,
    materialization: MaterializationSpec,
    source_skill_roots: tuple[Path, ...] = (),
) -> dict[str, Any]:
    """Write minimal derived intent and copy complete source Agent Skills."""

    sources = source_set(workspace)
    source_paths = {path.resolve() for path in sources}
    if workspace.derived_root.exists():
        shutil.rmtree(workspace.derived_root)
    workspace.materials_root.mkdir(parents=True)
    _write_text(workspace.interpretation_path, interpretation_text)
    for source_relative, target_relative in (
        (materialization.role_prompt_source, materialization.role_prompt),
        (materialization.memo_seed_source, materialization.memo_seed),
    ):
        source_path = _require_confined_path(workspace.source_root, source_relative, kind="file")
        if source_path not in source_paths:
            raise ValueError(
                f"Materialization source must be referenced by {OVERVIEW_FILENAME}: "
                f"{source_relative}"
            )
        target_path = Path(target_relative)
        if (
            target_path.is_absolute()
            or ".." in target_path.parts
            or not target_path.parts
            or target_path.parts[0] != "materials"
        ):
            raise ValueError(f"Derived asset target must stay beneath `materials/`: {target_path}")
        destination = workspace.derived_root / target_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
    copied_skills: list[str] = []
    for source in source_skill_roots:
        skill_source = source.resolve()
        if skill_source.is_symlink() or not skill_source.is_dir():
            raise ValueError(f"Agent Skill source must be a real directory: {source}")
        skill_file = skill_source / "SKILL.md"
        if not skill_file.is_file():
            raise ValueError(f"Agent Skill is missing SKILL.md: {source}")
        if skill_source.name.startswith(_RESERVED_SKILL_PREFIXES):
            raise ValueError(f"Reserved system-skill name is not allowed: {skill_source.name}")
        destination = workspace.materials_root / "skills" / skill_source.name
        shutil.copytree(skill_source, destination, symlinks=False)
        _validate_regular_tree(destination)
        copied_skills.append(f"materials/skills/{skill_source.name}")
    if tuple(copied_skills) != materialization.skills:
        raise ValueError(
            "Materialization skill paths must exactly match the selected Agent Skills."
        )
    _write_toml(
        workspace.materialization_path,
        materialization.model_dump(mode="python", exclude_none=True),
    )
    source_digest = digest_paths(sources, root=workspace.source_root)
    derived_digest = _derived_digest(workspace)
    validation = {
        "schema_version": "houmao-agent-derivation-validation.v1",
        "valid": True,
        "source_digest": source_digest,
        "source_files": [path.relative_to(workspace.source_root).as_posix() for path in sources],
        "derived_digest": derived_digest,
        "copied_skills": copied_skills,
        "findings": [],
    }
    _write_json(workspace.validation_path, validation)
    return validation


def approve_derivation(
    workspace: AgentDefinitionWorkspace,
    *,
    approved_by: str,
) -> dict[str, Any]:
    """Approve the exact current source and derived digests."""

    validation = _load_validation(workspace)
    _require_fresh_derivation(workspace, validation)
    approval = {
        "schema_version": "houmao-agent-derivation-approval.v1",
        "approved": True,
        "approved_by": approved_by,
        "approved_at": _utcnow_iso(),
        "source_digest": validation["source_digest"],
        "derived_digest": validation["derived_digest"],
    }
    _write_toml(workspace.approval_path, approval)
    return approval


def materialize_revision(
    workspace: AgentDefinitionWorkspace,
    *,
    output_root: Path | None = None,
    write: bool = True,
) -> RevisionValidation:
    """Preview or write one immutable portable Agent Definition Revision."""

    validation = _load_validation(workspace)
    _require_fresh_derivation(workspace, validation)
    approval = _load_toml(workspace.approval_path)
    if not approval.get("approved"):
        raise ValueError("The current derivation has not been approved.")
    if approval.get("source_digest") != validation["source_digest"]:
        raise ValueError("Approval is stale for the current source set.")
    if approval.get("derived_digest") != validation["derived_digest"]:
        raise ValueError("Approval is stale for the current derived material.")
    spec = MaterializationSpec.model_validate(_load_toml(workspace.materialization_path))
    if write:
        destination = (output_root or workspace.definition_root).resolve()
        if destination.exists():
            raise FileExistsError(
                f"Immutable Agent Definition Revision already exists: {destination}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".houmao-definition-", dir=destination.parent
        ) as temporary:
            staged = Path(temporary) / destination.name
            _build_revision(
                workspace=workspace, spec=spec, destination=staged, validation=validation
            )
            staged.rename(destination)
        return validate_revision(destination)
    with tempfile.TemporaryDirectory(prefix="houmao-definition-preview-") as temporary:
        destination = Path(temporary) / "agent-definition"
        _build_revision(
            workspace=workspace, spec=spec, destination=destination, validation=validation
        )
        return validate_revision(destination)


def validate_revision(root: Path) -> RevisionValidation:
    """Validate schemas, paths, markers, skills, and whole-revision identity."""

    revision_root = resolve_revision_reference(root)
    _validate_regular_tree(revision_root)
    _reject_secret_assignments(revision_root)
    definition = DefinitionDocument.model_validate(_load_toml(revision_root / "definition.toml"))
    deploy_contract = DeployContract.model_validate(
        _load_toml(revision_root / "deploy-contract.toml")
    )
    instance_contract = InstanceContract.model_validate(
        _load_toml(revision_root / "instance-contract.toml")
    )
    prompt = _require_confined_path(revision_root, definition.role_prompt, kind="file")
    memo = _require_confined_path(revision_root, definition.memo_seed, kind="file")
    skill_names: set[str] = set()
    for relative in definition.skills:
        skill_dir = _require_confined_path(revision_root, relative, kind="dir")
        if skill_dir.name in skill_names:
            raise ValueError(f"Duplicate Agent Skill name: {skill_dir.name}")
        if skill_dir.name.startswith(_RESERVED_SKILL_PREFIXES):
            raise ValueError(f"Reserved system-skill name is not allowed: {skill_dir.name}")
        skill_names.add(skill_dir.name)
        _validate_regular_tree(skill_dir)
        if not (skill_dir / "SKILL.md").is_file():
            raise ValueError(f"Agent Skill is missing SKILL.md: {skill_dir}")
    skills_by_name = {
        Path(relative).name: revision_root / relative for relative in definition.skills
    }
    for variable in instance_contract.runtime_variables:
        for consumer in variable.consumers:
            kind, separator, target = consumer.partition(":")
            if kind == "skill":
                if not separator or target not in skills_by_name:
                    raise ValueError(
                        f"Runtime variable `{variable.key}` references unknown skill `{target}`."
                    )
                skill_text = (skills_by_name[target] / "SKILL.md").read_text(encoding="utf-8")
                command_fragment = (
                    f"houmao-mgr agents self instance-state variables get {variable.key}"
                )
                if command_fragment not in skill_text:
                    raise ValueError(
                        f"Skill `{target}` omits the verified-self runtime-variable lookup phase."
                    )
    for mindset in instance_contract.mindsets:
        for skill_name in mindset.required_skills:
            if skill_name not in skills_by_name:
                raise ValueError(
                    f"Mindset `{mindset.name}` references unknown skill `{skill_name}`."
                )
            skill_text = (skills_by_name[skill_name] / "SKILL.md").read_text(encoding="utf-8")
            command_fragment = (
                f"houmao-mgr agents self instance-state mindsets snapshot --skill {skill_name}"
            )
            if command_fragment not in skill_text or "stop" not in skill_text.lower():
                raise ValueError(
                    f"Skill `{skill_name}` omits the fail-closed mindset snapshot phase."
                )
    declared_text_markers: dict[str, set[str]] = {
        "role_prompt": set(),
        "memo_seed": set(),
    }
    for item in deploy_contract.inputs:
        for binding in item.bindings:
            if binding.mode == "text":
                assert binding.marker is not None
                declared_text_markers[binding.target].add(binding.marker)
    prompt_text = prompt.read_text(encoding="utf-8")
    memo_text = memo.read_text(encoding="utf-8")
    for target, text in (("role_prompt", prompt_text), ("memo_seed", memo_text)):
        found_deploy_markers = {
            f"{{{{houmao.deploy.{key}}}}}" for key in _TEXT_MARKER_RE.findall(text)
        }
        if found_deploy_markers != declared_text_markers[target]:
            raise ValueError(
                f"Text marker declarations do not match `{target}`: "
                f"declared={sorted(declared_text_markers[target])}, "
                f"found={sorted(found_deploy_markers)}"
            )
    declared_instance_markers: dict[str, set[str]] = {"prompt": set(), "memo": set()}
    for variable in instance_contract.runtime_variables:
        marker = f"{{{{houmao.instance.{variable.key}}}}}"
        for target in ("prompt", "memo"):
            if target in variable.consumers:
                declared_instance_markers[target].add(marker)
    for target, text in (("prompt", prompt_text), ("memo", memo_text)):
        found_instance_marker_text = {
            f"{{{{houmao.instance.{key}}}}}" for key in _INSTANCE_MARKER_RE.findall(text)
        }
        if found_instance_marker_text != declared_instance_markers[target]:
            raise ValueError(
                f"Instance markers do not match `{target}` consumers: "
                f"declared={sorted(declared_instance_markers[target])}, "
                f"found={sorted(found_instance_marker_text)}"
            )
    revision_digest = _revision_digest(revision_root)
    if definition.revision_digest != revision_digest:
        raise ValueError(
            f"Revision digest mismatch: expected {definition.revision_digest}, got {revision_digest}"
        )
    instance_digest = _instance_contract_digest(instance_contract)
    if instance_contract.contract_digest != instance_digest:
        raise ValueError(
            "Instance-contract digest mismatch: "
            f"expected {instance_contract.contract_digest}, got {instance_digest}"
        )
    return RevisionValidation(
        root=revision_root,
        definition=definition,
        deploy_contract=deploy_contract,
        instance_contract=instance_contract,
        revision_digest=revision_digest,
        instance_contract_digest=instance_digest,
    )


def resolve_revision_reference(reference: Path) -> Path:
    """Resolve a local path or packaged ``builtin:<name>`` revision reference."""

    raw_reference = str(reference)
    if not raw_reference.startswith(_BUILTIN_DEFINITION_PREFIX):
        return reference.resolve()
    name = raw_reference.removeprefix(_BUILTIN_DEFINITION_PREFIX)
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) is None:
        raise ValueError(f"Invalid built-in Agent Definition name: {name}")
    resource = files(_BUILTIN_DEFINITION_PACKAGE).joinpath(
        _BUILTIN_DEFINITION_ROOT,
        name,
    )
    path = Path(str(resource))
    if not path.is_dir():
        raise ValueError(f"Unknown built-in Agent Definition: {name}")
    return path.resolve()


def load_instance_contract(path: Path, *, expected_digest: str | None = None) -> InstanceContract:
    """Load one immutable instance contract and optionally verify its digest."""

    contract = InstanceContract.model_validate(_load_toml(path))
    actual_digest = _instance_contract_digest(contract)
    if contract.contract_digest != actual_digest:
        raise ValueError(
            f"Instance-contract digest mismatch: expected {contract.contract_digest}, "
            f"got {actual_digest}"
        )
    if expected_digest is not None and actual_digest != expected_digest:
        raise ValueError(f"Instance contract does not match deployment digest `{expected_digest}`.")
    return contract


def create_deployment_request(
    *,
    revision_root: Path,
    overlay: HoumaoProjectOverlay,
    deployment_name: str,
    specialist_name: str,
    profile_name: str,
    tool: str,
    credential: str,
    workdir: str,
    values: dict[str, str | int | float | bool],
    provider: str = "default",
    setup: str = "default",
    posture: dict[str, Any] | None = None,
    private_workspace_enabled: bool | None = None,
    workspace_workdir_mode: Literal["project-root", "private-root"] | None = None,
    update_existing: bool = False,
) -> DeploymentRequest:
    """Validate values and create one non-secret Deployment Request."""

    revision = validate_revision(revision_root)
    resolved_values = _resolve_input_values(revision.deploy_contract, values)
    workspace_contract = revision.instance_contract.private_workspace
    selected_workspace = (
        workspace_contract.default_enabled
        if private_workspace_enabled is None
        else private_workspace_enabled
    )
    if workspace_contract.mode == "disabled" and selected_workspace:
        raise ValueError("This Agent Definition does not declare a private workspace.")
    if workspace_contract.mode == "required" and not selected_workspace:
        raise ValueError("This Agent Definition requires a private workspace.")
    selected_workdir_mode = workspace_workdir_mode or workspace_contract.workdir_mode
    if selected_workdir_mode == "private-root" and not selected_workspace:
        raise ValueError("Private-root workdir requires private workspace activation.")
    if selected_workdir_mode != workspace_contract.workdir_mode:
        raise ValueError("Deployment cannot select an undeclared workspace workdir mode.")
    return DeploymentRequest(
        definition_path=str(revision.root),
        definition_id=revision.definition.definition_id,
        revision_id=revision.definition.revision_id,
        revision_digest=revision.revision_digest,
        target_project=str(overlay.project_root.resolve()),
        deployment_name=deployment_name,
        specialist_name=specialist_name,
        profile_name=profile_name,
        tool=tool,
        credential=credential,
        workdir=workdir,
        provider=provider,
        setup=setup,
        values=resolved_values,
        posture=posture or {},
        private_workspace_enabled=selected_workspace,
        workspace_workdir_mode=selected_workdir_mode,
        update_existing=update_existing,
    )


def plan_deployment(
    request: DeploymentRequest,
    *,
    overlay: HoumaoProjectOverlay,
) -> tuple[DeploymentPlan, Path]:
    """Render and persist an integrity-protected Deployment Plan."""

    if Path(request.target_project).resolve() != overlay.project_root.resolve():
        raise ValueError("Deployment Request targets a different project.")
    revision = validate_revision(Path(request.definition_path))
    if (
        revision.definition.definition_id != request.definition_id
        or revision.definition.revision_id != request.revision_id
        or revision.revision_digest != request.revision_digest
    ):
        raise ValueError("Deployment Request is stale for the selected definition revision.")
    catalog = ProjectCatalog.from_overlay(overlay)
    catalog.initialize()
    blockers: list[str] = []
    try:
        catalog.load_auth_profile(tool=request.tool, name=request.credential)
    except FileNotFoundError:
        blockers.append(
            f"Credential `{request.tool}/{request.credential}` is not an existing "
            "compatible project reference."
        )
    existing_deployment: dict[str, Any] | None = None
    try:
        existing_deployment = inspect_agent_deployment(overlay, request.deployment_name)
    except FileNotFoundError:
        pass
    if request.update_existing:
        if existing_deployment is None:
            blockers.append(f"Agent Deployment `{request.deployment_name}` does not exist.")
        elif existing_deployment["definition_id"] != request.definition_id:
            blockers.append("An Agent Deployment update cannot change definition identity.")
        elif _deployment_health_findings(overlay, existing_deployment):
            blockers.append(
                "Existing Agent Deployment has source or output drift; run doctor before update."
            )
    elif existing_deployment is not None:
        blockers.append(f"Agent Deployment `{request.deployment_name}` already exists.")
    if catalog.specialist_exists(request.specialist_name):
        if (
            not request.update_existing
            or existing_deployment is None
            or request.specialist_name != existing_deployment["specialist_name"]
        ):
            blockers.append(f"Specialist `{request.specialist_name}` already exists.")
    try:
        catalog.load_launch_profile(request.profile_name)
    except FileNotFoundError:
        pass
    else:
        if (
            not request.update_existing
            or existing_deployment is None
            or request.profile_name != existing_deployment["profile_name"]
        ):
            blockers.append(f"Launch profile `{request.profile_name}` already exists.")
    _resolve_input_values(revision.deploy_contract, request.values)
    request_payload = request.model_dump(mode="json")
    request_digest = _sha256_bytes(_canonical_json(request_payload))
    precondition = _project_precondition_digest(overlay)
    seed = {
        "request_digest": request_digest,
        "revision_digest": revision.revision_digest,
        "project_precondition_digest": precondition,
    }
    plan_id = hashlib.sha256(_canonical_json(seed)).hexdigest()[:24]
    plan_root = overlay.jobs_root / "agent-definition-deployments" / plan_id
    if plan_root.exists():
        existing = load_deployment_plan(plan_root)
        return existing, plan_root
    rendered_root = plan_root / "rendered"
    role_prompt = _render_text_asset(
        (revision.root / revision.definition.role_prompt).read_text(encoding="utf-8"),
        revision.deploy_contract,
        request.values,
        target="role_prompt",
    )
    memo_seed = _render_text_asset(
        (revision.root / revision.definition.memo_seed).read_text(encoding="utf-8"),
        revision.deploy_contract,
        request.values,
        target="memo_seed",
    )
    resolved_fields = _resolve_structured_bindings(revision.deploy_contract, request.values)
    specialist_name = str(resolved_fields.get("specialist.name", request.specialist_name))
    profile_name = str(resolved_fields.get("profile.name", request.profile_name))
    workdir = str(resolved_fields.get("profile.workdir", request.workdir))
    tool = str(resolved_fields.get("specialist.tool", request.tool))
    if specialist_name != request.specialist_name or profile_name != request.profile_name:
        raise ValueError("V1 plans do not allow bindings to change requested catalog identities.")
    _write_text(rendered_root / "prompts" / "system.md", role_prompt)
    _write_text(rendered_root / "memo" / "houmao-memo.md", memo_seed)
    contract_target = rendered_root / "contracts" / "instance-contract.toml"
    contract_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(revision.root / "instance-contract.toml", contract_target)
    skill_names: list[str] = []
    for relative in revision.definition.skills:
        source = revision.root / relative
        destination = rendered_root / "skills" / source.name
        shutil.copytree(source, destination)
        skill_names.append(source.name)
    artifacts = tuple(
        RenderedArtifact(
            relative_path=path.relative_to(plan_root).as_posix(),
            digest=_sha256_bytes(path.read_bytes()),
        )
        for path in sorted(rendered_root.rglob("*"))
        if path.is_file()
    )
    plan = DeploymentPlan(
        plan_id=plan_id,
        request_digest=request_digest,
        definition_id=request.definition_id,
        revision_id=request.revision_id,
        revision_digest=request.revision_digest,
        instance_contract_digest=revision.instance_contract_digest,
        target_project=request.target_project,
        project_precondition_digest=precondition,
        deployment_name=request.deployment_name,
        specialist_name=specialist_name,
        profile_name=profile_name,
        tool=tool,
        credential=request.credential,
        provider=request.provider,
        setup=request.setup,
        workdir=workdir,
        values=request.values,
        posture=request.posture,
        private_workspace_enabled=bool(request.private_workspace_enabled),
        workspace_workdir_mode=request.workspace_workdir_mode or "project-root",
        workspace_contract_digest=(
            _workspace_contract_digest(revision.instance_contract.private_workspace)
            if request.private_workspace_enabled
            else None
        ),
        update_existing=request.update_existing,
        skill_names=tuple(skill_names),
        rendered_artifacts=artifacts,
        blockers=tuple(blockers),
    )
    plan = plan.model_copy(update={"plan_digest": _plan_digest(plan)})
    _write_json(plan_root / "request.json", request_payload)
    _write_json(plan_root / "plan.json", plan.model_dump(mode="json"))
    _write_json(
        plan_root / "journal.json",
        {"schema_version": "houmao-agent-deployment-journal.v1", "state": "planned"},
    )
    return plan, plan_root


def load_deployment_plan(plan_root: Path) -> DeploymentPlan:
    """Load one plan and reject edited plan or rendered artifacts."""

    plan = DeploymentPlan.model_validate(
        json.loads((plan_root / "plan.json").read_text(encoding="utf-8"))
    )
    if _plan_digest(plan) != plan.plan_digest:
        raise ValueError(f"Deployment Plan was edited: {plan_root}")
    for artifact in plan.rendered_artifacts:
        path = _require_confined_path(plan_root, artifact.relative_path, kind="file")
        if _sha256_bytes(path.read_bytes()) != artifact.digest:
            raise ValueError(f"Rendered plan artifact was edited: {path}")
    return plan


def apply_deployment(
    plan_root: Path,
    *,
    overlay: HoumaoProjectOverlay,
    defer_registration: bool = False,
    skip_project_precondition: bool = False,
    batch_operation_id: str | None = None,
    batch_member_ordinal: int | None = None,
) -> dict[str, Any]:
    """Apply one intact plan and make its Agent Deployment visible last."""

    plan = load_deployment_plan(plan_root)
    if plan.blockers:
        raise ValueError("Deployment Plan has blockers: " + "; ".join(plan.blockers))
    if Path(plan.target_project).resolve() != overlay.project_root.resolve():
        raise ValueError("Deployment Plan targets a different project.")
    if (
        not skip_project_precondition
        and _project_precondition_digest(overlay) != plan.project_precondition_digest
    ):
        raise ValueError("Project catalog changed after planning; create a new Deployment Plan.")
    journal_path = plan_root / "journal.json"
    catalog = ProjectCatalog.from_overlay(overlay)
    created_skills: list[str] = []
    specialist_created = False
    profile_created = False
    catalog_committed = False
    deployment_id = str(uuid4())
    replaced_deployment: dict[str, Any] | None = None
    try:
        if plan.update_existing:
            replaced_deployment = inspect_agent_deployment(overlay, plan.deployment_name)
            deployment_id = str(replaced_deployment["deployment_id"])
            if replaced_deployment[
                "instance_contract_digest"
            ] != plan.instance_contract_digest and deployment_instance_references(
                overlay,
                str(replaced_deployment["deployment_id"]),
            ):
                raise ValueError(
                    "Instance-contract update is blocked by live or preserved managed-agent state."
                )
            if plan.specialist_name == replaced_deployment["specialist_name"]:
                raise ValueError(
                    "Update requires a fresh specialist name so publication remains recoverable."
                )
            if plan.profile_name == replaced_deployment["profile_name"]:
                raise ValueError(
                    "Update requires a fresh profile name so publication remains recoverable."
                )
        _write_json(journal_path, {"state": "preparing", "plan_id": plan.plan_id})
        rendered_root = plan_root / "rendered"
        for skill_name in plan.skill_names:
            rendered_skill = rendered_root / "skills" / skill_name
            cached_skill = _ensure_registered_skill_cache(
                overlay=overlay,
                source=rendered_skill,
            )
            if catalog.project_skill_exists(skill_name):
                existing = catalog.load_project_skill(skill_name)
                existing_digest = _tree_digest(existing.resolved_canonical_path(overlay))
                candidate_digest = _tree_digest(cached_skill)
                if existing_digest != candidate_digest:
                    raise ValueError(
                        f"Project skill collision for `{skill_name}` with different content."
                    )
                continue
            catalog.create_project_skill_from_source(
                name=skill_name,
                source_path=cached_skill,
                mode="symlink",
            )
            created_skills.append(skill_name)
            _write_json(
                journal_path,
                {
                    "state": "preparing",
                    "plan_id": plan.plan_id,
                    "created_skills": created_skills,
                },
            )
        auth_profile = catalog.load_auth_profile(tool=plan.tool, name=plan.credential)
        _write_json(
            journal_path,
            {
                "state": "prepared",
                "plan_id": plan.plan_id,
                "created_skills": created_skills,
            },
        )
        catalog.store_specialist(
            name=plan.specialist_name,
            preset_name=f"{plan.specialist_name}-preset",
            tool=plan.tool,
            provider=plan.provider,
            auth_profile=auth_profile,
            role_name=f"{plan.specialist_name}-role",
            setup_name=plan.setup,
            prompt_path=rendered_root / "prompts" / "system.md",
            skill_names=plan.skill_names,
            launch_mapping={},
            mailbox_mapping=None,
            extra_mapping={},
        )
        specialist_created = True
        _write_json(
            journal_path,
            {
                "state": "prepared",
                "plan_id": plan.plan_id,
                "created_skills": created_skills,
                "specialist_created": True,
            },
        )
        deployment_posture = dict(plan.posture)
        deployment_posture["houmao_agent_definition"] = {
            "deployment_id": deployment_id,
            "deployment_name": plan.deployment_name,
            "definition_id": plan.definition_id,
            "revision_id": plan.revision_id,
            "revision_digest": plan.revision_digest,
            "instance_contract_digest": plan.instance_contract_digest,
            "instance_contract_path": str(
                (plan_root / "rendered" / "contracts" / "instance-contract.toml").resolve()
            ),
            "private_workspace_enabled": plan.private_workspace_enabled,
            "workspace_workdir_mode": plan.workspace_workdir_mode,
            "workspace_contract_digest": plan.workspace_contract_digest,
        }
        catalog.store_launch_profile(
            name=plan.profile_name,
            profile_lane="easy_profile",
            source_kind="specialist",
            source_name=plan.specialist_name,
            managed_agent_name=None,
            managed_agent_id=None,
            workdir=plan.workdir,
            auth_tool=plan.tool,
            auth_name=plan.credential,
            operator_prompt_mode=None,
            env_mapping={},
            mailbox_mapping=None,
            posture_mapping=deployment_posture,
            system_skills_mapping=None,
            prompt_overlay_mode=None,
            prompt_overlay_text=None,
            memo_seed_source_kind="memo",
            memo_seed_text=(rendered_root / "memo" / "houmao-memo.md").read_text(encoding="utf-8"),
            registered_skill_names=plan.skill_names,
        )
        profile_created = True
        if defer_registration:
            _write_json(
                journal_path,
                {
                    "state": "prepared",
                    "plan_id": plan.plan_id,
                    "deployment_id": deployment_id,
                    "batch_operation_id": batch_operation_id,
                    "batch_member_ordinal": batch_member_ordinal,
                    "created_skills": created_skills,
                    "specialist_created": True,
                    "profile_created": True,
                },
            )
        else:
            replaced_resources = (
                {
                    "replaced_specialist_name": str(replaced_deployment["specialist_name"]),
                    "replaced_profile_name": str(replaced_deployment["profile_name"]),
                }
                if replaced_deployment is not None
                else {}
            )
            _write_json(
                journal_path,
                {
                    "state": "committing",
                    "plan_id": plan.plan_id,
                    "deployment_id": deployment_id,
                    "created_skills": created_skills,
                    "specialist_created": True,
                    "profile_created": True,
                    **replaced_resources,
                },
            )
            if replaced_deployment is None:
                deployment_id = _register_agent_deployment(
                    overlay=overlay,
                    plan=plan,
                    plan_root=plan_root,
                    deployment_id=deployment_id,
                    batch_operation_id=batch_operation_id,
                    batch_member_ordinal=batch_member_ordinal,
                )
            else:
                with sqlite3.connect(overlay.catalog_path) as connection:
                    connection.execute("PRAGMA foreign_keys = ON")
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        "DELETE FROM agent_deployments WHERE deployment_id = ?",
                        (replaced_deployment["deployment_id"],),
                    )
                    deployment_id = _register_agent_deployment(
                        overlay=overlay,
                        plan=plan,
                        plan_root=plan_root,
                        deployment_id=deployment_id,
                        batch_operation_id=batch_operation_id,
                        batch_member_ordinal=batch_member_ordinal,
                        connection=connection,
                    )
                    connection.commit()
            catalog_committed = True
            catalog.materialize_projection()
            if replaced_deployment is not None:
                _cleanup_replaced_deployment_resources(
                    catalog,
                    profile_name=str(replaced_deployment["profile_name"]),
                    specialist_name=str(replaced_deployment["specialist_name"]),
                )
                catalog.materialize_projection()
            _write_json(
                journal_path,
                {"state": "applied", "plan_id": plan.plan_id, "deployment_id": deployment_id},
            )
    except Exception as exc:
        try:
            visible = inspect_agent_deployment(overlay, plan.deployment_name)
        except FileNotFoundError:
            visible = None
        catalog_committed = catalog_committed or (
            visible is not None and visible["plan_digest"] == plan.plan_digest
        )
        if catalog_committed:
            _write_json(
                journal_path,
                {
                    "state": "committing",
                    "plan_id": plan.plan_id,
                    "deployment_id": deployment_id,
                    "created_skills": created_skills,
                    "specialist_created": specialist_created,
                    "profile_created": profile_created,
                    "replaced_specialist_name": (
                        None
                        if replaced_deployment is None
                        else str(replaced_deployment["specialist_name"])
                    ),
                    "replaced_profile_name": (
                        None
                        if replaced_deployment is None
                        else str(replaced_deployment["profile_name"])
                    ),
                    "catalog_committed": True,
                    "error": str(exc),
                },
            )
        else:
            if profile_created:
                catalog.remove_launch_profile(plan.profile_name)
            if specialist_created:
                catalog.remove_specialist(plan.specialist_name)
            for skill_name in reversed(created_skills):
                try:
                    catalog.remove_project_skill(skill_name)
                except (FileNotFoundError, ValueError):
                    pass
            _write_json(
                journal_path,
                {"state": "failed", "plan_id": plan.plan_id, "error": str(exc)},
            )
        raise
    launch_command = (
        f"houmao-mgr --project-dir {json.dumps(str(overlay.project_root))} "
        f"project agents launch --profile {plan.profile_name} --name <agent-name>"
    )
    return {
        "deployment_id": deployment_id,
        "deployment_name": plan.deployment_name,
        "profile_name": plan.profile_name,
        "launch_command": launch_command,
        "launched": False,
        "prepared_only": defer_registration,
    }


def _cleanup_replaced_deployment_resources(
    catalog: ProjectCatalog,
    *,
    profile_name: str,
    specialist_name: str,
) -> None:
    """Remove superseded update resources after the new catalog row commits."""

    try:
        catalog.remove_launch_profile(profile_name)
    except (FileNotFoundError, ValueError):
        pass
    try:
        catalog.remove_specialist(specialist_name)
    except (FileNotFoundError, ValueError):
        pass


def _ensure_registered_skill_cache(
    *,
    overlay: HoumaoProjectOverlay,
    source: Path,
) -> Path:
    """Return one immutable project skill-cache tree keyed by content digest."""

    digest = _tree_digest(source)
    digest_name = digest.removeprefix("sha256:")
    cache_root = overlay.content_root / "agent-definition-skill-cache"
    destination = cache_root / digest_name
    if destination.exists():
        if not destination.is_dir() or _tree_digest(destination) != digest:
            raise ValueError(f"Registered-skill cache entry is invalid: {destination}")
        return destination
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".skill-cache-", dir=cache_root) as temporary:
        staged = Path(temporary) / digest_name
        shutil.copytree(source, staged)
        _validate_regular_tree(staged)
        if _tree_digest(staged) != digest:
            raise ValueError("Registered-skill cache staging changed during copy.")
        try:
            staged.rename(destination)
        except FileExistsError:
            if not destination.is_dir() or _tree_digest(destination) != digest:
                raise ValueError(
                    f"Registered-skill cache entry is invalid: {destination}"
                ) from None
    return destination


def rollback_prepared_deployment(
    plan_root: Path,
    *,
    overlay: HoumaoProjectOverlay,
) -> None:
    """Remove ordinary catalog artifacts prepared for an uncommitted batch member."""

    plan = load_deployment_plan(plan_root)
    journal_path = plan_root / "journal.json"
    journal = json.loads(journal_path.read_text(encoding="utf-8")) if journal_path.is_file() else {}
    catalog = ProjectCatalog.from_overlay(overlay)
    try:
        catalog.remove_launch_profile(plan.profile_name)
    except FileNotFoundError:
        pass
    try:
        catalog.remove_specialist(plan.specialist_name)
    except FileNotFoundError:
        pass
    created_skills = journal.get("created_skills", [])
    if not isinstance(created_skills, list):
        created_skills = []
    for skill_name in created_skills:
        if not isinstance(skill_name, str):
            continue
        try:
            catalog.remove_project_skill(skill_name)
        except (FileNotFoundError, ValueError):
            pass


def list_agent_deployments(overlay: HoumaoProjectOverlay) -> list[dict[str, Any]]:
    """List catalog-visible Agent Deployments."""

    ProjectCatalog.from_overlay(overlay).initialize()
    with sqlite3.connect(overlay.catalog_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM agent_deployments ORDER BY deployment_name"
        ).fetchall()
    return [dict(row) for row in rows]


def inspect_agent_deployment(overlay: HoumaoProjectOverlay, deployment_name: str) -> dict[str, Any]:
    """Inspect one catalog-visible Agent Deployment."""

    for row in list_agent_deployments(overlay):
        if row["deployment_name"] == deployment_name:
            row["skill_names"] = json.loads(str(row["skill_names_payload"]))
            return row
    raise FileNotFoundError(f"Agent Deployment `{deployment_name}` was not found.")


def _deployment_health_findings(
    overlay: HoumaoProjectOverlay,
    deployment: dict[str, Any],
) -> list[dict[str, str]]:
    """Verify one deployment's source, plan, catalog, and managed content."""

    findings: list[dict[str, str]] = []
    deployment_name = str(deployment["deployment_name"])
    plan_path = Path(str(deployment["plan_path"]))
    try:
        plan = load_deployment_plan(plan_path)
    except (OSError, ValueError) as exc:
        detail = str(exc)
        code = "output-drift" if "artifact" in detail.casefold() else "plan-drift"
        return [
            {
                "severity": "error",
                "path": str(plan_path),
                "deployment_name": deployment_name,
                "code": code,
                "detail": detail,
            }
        ]
    if plan.plan_digest != deployment["plan_digest"]:
        findings.append(
            {
                "severity": "error",
                "path": str(plan_path),
                "deployment_name": deployment_name,
                "code": "catalog-plan-digest-drift",
            }
        )
    request_path = Path(str(deployment["request_path"]))
    try:
        request_payload = json.loads(request_path.read_text(encoding="utf-8"))
        request = DeploymentRequest.model_validate(request_payload)
        request_digest = _sha256_bytes(_canonical_json(request.model_dump(mode="json")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        findings.append(
            {
                "severity": "error",
                "path": str(request_path),
                "deployment_name": deployment_name,
                "code": "request-drift",
                "detail": str(exc),
            }
        )
        request = None
        request_digest = ""
    if request is not None:
        if request_digest != plan.request_digest or request_digest != str(
            deployment["request_digest"]
        ):
            findings.append(
                {
                    "severity": "error",
                    "path": str(request_path),
                    "deployment_name": deployment_name,
                    "code": "request-digest-drift",
                }
            )
        try:
            revision = validate_revision(Path(request.definition_path))
            if (
                revision.revision_digest != plan.revision_digest
                or revision.revision_digest != deployment["revision_digest"]
            ):
                raise ValueError("Revision digest no longer matches deployment provenance.")
        except (OSError, ValueError) as exc:
            findings.append(
                {
                    "severity": "error",
                    "path": request.definition_path,
                    "deployment_name": deployment_name,
                    "code": "source-drift",
                    "detail": str(exc),
                }
            )
    catalog = ProjectCatalog.from_overlay(overlay)
    try:
        specialist = catalog.load_specialist(str(deployment["specialist_name"]))
        if (
            specialist.tool != plan.tool
            or specialist.credential_name != plan.credential
            or tuple(specialist.skills) != plan.skill_names
        ):
            raise ValueError("Specialist semantics no longer match the Deployment Plan.")
        prompt_path = specialist.prompt_ref.resolve(overlay)
        if prompt_path.read_bytes() != (plan_path / "rendered/prompts/system.md").read_bytes():
            raise ValueError("Managed specialist prompt differs from rendered plan output.")
    except (OSError, ValueError) as exc:
        findings.append(
            {
                "severity": "error",
                "path": str(deployment["specialist_name"]),
                "deployment_name": deployment_name,
                "code": "managed-specialist-drift",
                "detail": str(exc),
            }
        )
    try:
        profile = catalog.load_launch_profile(str(deployment["profile_name"]))
        if (
            profile.source_name != plan.specialist_name
            or profile.registered_skill_names != plan.skill_names
            or profile.memo_seed is None
        ):
            raise ValueError("Launch-profile semantics no longer match the Deployment Plan.")
        memo_path = profile.memo_seed.content_ref.resolve(overlay)
        if memo_path.read_bytes() != (plan_path / "rendered/memo/houmao-memo.md").read_bytes():
            raise ValueError("Managed memo seed differs from rendered plan output.")
    except (OSError, ValueError) as exc:
        findings.append(
            {
                "severity": "error",
                "path": str(deployment["profile_name"]),
                "deployment_name": deployment_name,
                "code": "managed-profile-drift",
                "detail": str(exc),
            }
        )
    for skill_name in plan.skill_names:
        try:
            skill = catalog.load_project_skill(skill_name)
            managed_digest = _tree_digest(skill.resolved_canonical_path(overlay))
            planned_digest = _tree_digest(plan_path / "rendered" / "skills" / skill_name)
            if managed_digest != planned_digest:
                raise ValueError("Registered skill differs from rendered plan output.")
        except (OSError, ValueError) as exc:
            findings.append(
                {
                    "severity": "error",
                    "path": skill_name,
                    "deployment_name": deployment_name,
                    "code": "registered-skill-drift",
                    "detail": str(exc),
                }
            )
    return findings


def doctor_agent_deployments(overlay: HoumaoProjectOverlay) -> dict[str, Any]:
    """Recover interrupted apply publication and verify deployment-owned plans."""

    findings: list[dict[str, str]] = []
    catalog = ProjectCatalog.from_overlay(overlay)
    jobs_root = overlay.jobs_root / "agent-definition-deployments"
    if jobs_root.is_dir():
        for job in sorted(path for path in jobs_root.iterdir() if path.is_dir()):
            journal_path = job / "journal.json"
            if not journal_path.is_file():
                findings.append({"severity": "error", "path": str(job), "code": "missing-journal"})
                continue
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            state = str(journal.get("state"))
            if state in {"preparing", "prepared", "committing"}:
                try:
                    plan = load_deployment_plan(job)
                except (OSError, ValueError) as exc:
                    findings.append(
                        {
                            "severity": "error",
                            "path": str(job),
                            "code": "invalid-interrupted-plan",
                            "detail": str(exc),
                        }
                    )
                    continue
                try:
                    visible = inspect_agent_deployment(overlay, plan.deployment_name)
                except FileNotFoundError:
                    visible = None
                if (
                    state == "committing"
                    and visible is not None
                    and visible["plan_digest"] == plan.plan_digest
                ):
                    catalog.materialize_projection()
                    replaced_profile_name = journal.get("replaced_profile_name")
                    replaced_specialist_name = journal.get("replaced_specialist_name")
                    if isinstance(replaced_profile_name, str) and isinstance(
                        replaced_specialist_name, str
                    ):
                        _cleanup_replaced_deployment_resources(
                            catalog,
                            profile_name=replaced_profile_name,
                            specialist_name=replaced_specialist_name,
                        )
                        catalog.materialize_projection()
                    _write_json(
                        journal_path,
                        {
                            "state": "applied",
                            "plan_id": plan.plan_id,
                            "deployment_id": visible["deployment_id"],
                            "recovered_by_doctor": True,
                        },
                    )
                    findings.append(
                        {
                            "severity": "info",
                            "path": str(job),
                            "code": "recovered-publication",
                        }
                    )
                elif visible is None:
                    rollback_prepared_deployment(job, overlay=overlay)
                    _write_json(
                        journal_path,
                        {
                            "state": "failed",
                            "plan_id": plan.plan_id,
                            "recovered_by_doctor": True,
                        },
                    )
                    findings.append(
                        {
                            "severity": "info",
                            "path": str(job),
                            "code": f"rolled-back-{state}",
                        }
                    )
                else:
                    findings.append(
                        {
                            "severity": "error",
                            "path": str(job),
                            "code": "interrupted-publication-conflict",
                        }
                    )
    for deployment in list_agent_deployments(overlay):
        findings.extend(_deployment_health_findings(overlay, deployment))
    return {
        "healthy": not any(item["severity"] == "error" for item in findings),
        "findings": findings,
    }


def remove_agent_deployment(
    overlay: HoumaoProjectOverlay,
    deployment_name: str,
    *,
    has_instance_references: bool = False,
) -> dict[str, Any]:
    """Remove one deployment and only its owned catalog relationships."""

    deployment = inspect_agent_deployment(overlay, deployment_name)
    drift = _deployment_health_findings(overlay, deployment)
    if drift:
        codes = ", ".join(sorted({item["code"] for item in drift}))
        raise ValueError(f"Deployment has source or output drift; run doctor first: {codes}")
    references = deployment_instance_references(overlay, str(deployment["deployment_id"]))
    if has_instance_references or references:
        detail = ", ".join(str(path) for path in references)
        suffix = f": {detail}" if detail else ""
        raise ValueError(
            "Deployment is referenced by live or preserved managed-agent instances" + suffix
        )
    catalog = ProjectCatalog.from_overlay(overlay)
    with sqlite3.connect(overlay.catalog_path) as connection:
        connection.execute(
            "DELETE FROM agent_deployments WHERE deployment_name = ?", (deployment_name,)
        )
        connection.commit()
    catalog.remove_launch_profile(str(deployment["profile_name"]))
    catalog.remove_specialist(str(deployment["specialist_name"]))
    for skill_name in deployment["skill_names"]:
        try:
            catalog.remove_project_skill(str(skill_name))
        except ValueError:
            pass
    return {"removed": deployment_name, "credentials_preserved": True}


def deployment_instance_references(
    overlay: HoumaoProjectOverlay,
    deployment_id: str,
) -> tuple[Path, ...]:
    """Return preserved instance-state stores bound to one deployment id."""

    agents_root = overlay.memory_root / "agents"
    if not agents_root.is_dir():
        return ()
    references: list[Path] = []
    for state_db in sorted(agents_root.glob("*/state.sqlite")):
        if state_db.is_symlink() or not state_db.is_file():
            continue
        try:
            with sqlite3.connect(state_db) as connection:
                row = connection.execute(
                    "SELECT value FROM store_meta WHERE key = 'deployment_id'"
                ).fetchone()
        except sqlite3.DatabaseError:
            continue
        if row is not None and str(row[0]) == deployment_id:
            references.append(state_db.resolve())
    return tuple(references)


def _load_toml(path: Path) -> dict[str, Any]:
    """Load one TOML mapping."""

    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a TOML mapping: {path}")
    return payload


def _load_validation(workspace: AgentDefinitionWorkspace) -> dict[str, Any]:
    """Load one derivation validation mapping."""

    payload = json.loads(workspace.validation_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a validation mapping: {workspace.validation_path}")
    return payload


def _derived_digest(workspace: AgentDefinitionWorkspace) -> str:
    """Digest the machine authority and approved material files."""

    paths = [workspace.interpretation_path, workspace.materialization_path]
    if workspace.materials_root.is_dir():
        paths.extend(path for path in workspace.materials_root.rglob("*") if path.is_file())
    return digest_paths(tuple(paths), root=workspace.derived_root)


def _require_fresh_derivation(
    workspace: AgentDefinitionWorkspace, validation: dict[str, Any]
) -> None:
    """Reject stale source or derived content."""

    source_digest = digest_paths(source_set(workspace), root=workspace.source_root)
    if source_digest != validation.get("source_digest"):
        raise ValueError("Derived intent is stale because the source set changed.")
    derived_digest = _derived_digest(workspace)
    if derived_digest != validation.get("derived_digest"):
        raise ValueError("Derived intent is stale because derived material changed.")


def _validate_regular_tree(root: Path) -> None:
    """Reject symlinks and special files anywhere in a copied tree."""

    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not accepted in Agent Skills: {path}")
        mode = path.stat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError(f"Special files are not accepted: {path}")


def _reject_secret_assignments(root: Path) -> None:
    """Reject embedded credential-secret assignments in portable text assets."""

    inspected_suffixes = {".toml", ".json", ".yaml", ".yml", ".env", ".md", ".txt", ".ini", ".cfg"}
    safe_literals = {"", "false", "null", "none", '""', "''", "[]", "{}"}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.suffix.casefold() not in inspected_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        for match in _SECRET_ASSIGNMENT_RE.finditer(text):
            value = match.group(2).strip().casefold().rstrip(",")
            if value in safe_literals or value.startswith(("<", "${")):
                continue
            raise ValueError(
                "Agent Definition contains a credential-secret field: "
                f"{path.relative_to(root)}:{match.group(1)}"
            )


def _build_revision(
    *,
    workspace: AgentDefinitionWorkspace,
    spec: MaterializationSpec,
    destination: Path,
    validation: dict[str, Any],
) -> None:
    """Build a revision in one empty staging directory."""

    destination.mkdir(parents=True)
    prompt_source = _require_confined_path(workspace.derived_root, spec.role_prompt, kind="file")
    memo_source = _require_confined_path(workspace.derived_root, spec.memo_seed, kind="file")
    prompt_destination = destination / "assets" / "prompts" / "system.md"
    memo_destination = destination / "assets" / "memo" / "houmao-memo.md"
    prompt_destination.parent.mkdir(parents=True)
    memo_destination.parent.mkdir(parents=True)
    shutil.copy2(prompt_source, prompt_destination)
    shutil.copy2(memo_source, memo_destination)
    skill_paths: list[str] = []
    for relative in spec.skills:
        skill_source = _require_confined_path(workspace.derived_root, relative, kind="dir")
        skill_destination = destination / "assets" / "skills" / skill_source.name
        shutil.copytree(skill_source, skill_destination)
        _validate_regular_tree(skill_destination)
        skill_paths.append(skill_destination.relative_to(destination).as_posix())
    instance = spec.instance.model_copy(update={"contract_digest": ""})
    instance = instance.model_copy(update={"contract_digest": _instance_contract_digest(instance)})
    _write_toml(
        destination / "deploy-contract.toml",
        DeployContract(inputs=spec.deploy_inputs).model_dump(mode="python", exclude_none=True),
    )
    _write_toml(
        destination / "instance-contract.toml",
        instance.model_dump(mode="python", exclude_none=True),
    )
    definition = DefinitionDocument(
        definition_id=spec.definition_id,
        revision_id=spec.revision_id,
        purpose=spec.purpose,
        skills=tuple(skill_paths),
    )
    _write_toml(
        destination / "definition.toml",
        definition.model_dump(mode="python", exclude_none=True),
    )
    _write_json(
        destination / "provenance" / "materialization.json",
        {
            "schema_version": "houmao-agent-materialization-provenance.v1",
            "source_digest": validation["source_digest"],
            "derived_digest": validation["derived_digest"],
            "materialized_at": _utcnow_iso(),
        },
    )
    definition = definition.model_copy(update={"revision_digest": _revision_digest(destination)})
    _write_toml(
        destination / "definition.toml",
        definition.model_dump(mode="python", exclude_none=True),
    )


def _instance_contract_digest(contract: InstanceContract) -> str:
    """Compute the canonical digest with its self-field cleared."""

    payload = contract.model_dump(mode="json")
    payload["contract_digest"] = ""
    return _sha256_bytes(_canonical_json(payload))


def workspace_contract_digest(contract: PrivateWorkspaceContract) -> str:
    """Return the immutable digest of one private-workspace contract."""

    return _sha256_bytes(_canonical_json(contract.model_dump(mode="json")))


def _workspace_contract_digest(contract: PrivateWorkspaceContract) -> str:
    """Compatibility-local wrapper for workspace contract digesting."""

    return workspace_contract_digest(contract)


def _revision_digest(root: Path) -> str:
    """Compute a whole-revision digest with the self-field cleared."""

    records: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == "definition.toml":
            payload = _load_toml(path)
            payload["revision_digest"] = ""
            content = tomli_w.dumps(payload).encode()
        elif relative == "provenance/materialization.json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload.pop("materialized_at", None)
            content = _canonical_json(payload)
        else:
            content = path.read_bytes()
        records.append({"path": relative, "digest": _sha256_bytes(content)})
    return _sha256_bytes(_canonical_json(records))


def _tree_digest(root: Path) -> str:
    """Digest all regular files in one directory tree."""

    return digest_paths(tuple(path for path in root.rglob("*") if path.is_file()), root=root)


def _validate_input_value(item: DeployInput, value: object) -> None:
    """Validate one scalar value against its input declaration."""

    valid = {
        "string": isinstance(value, str),
        "enum": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }[item.value_type]
    if not valid:
        raise ValueError(f"Input `{item.key}` requires type `{item.value_type}`.")
    if item.value_type == "enum" and value not in item.choices:
        raise ValueError(f"Input `{item.key}` must be one of {list(item.choices)}.")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if item.minimum is not None and value < item.minimum:
            raise ValueError(f"Input `{item.key}` is below its minimum.")
        if item.maximum is not None and value > item.maximum:
            raise ValueError(f"Input `{item.key}` is above its maximum.")


def _resolve_input_values(
    contract: DeployContract,
    supplied: dict[str, str | int | float | bool],
) -> dict[str, str | int | float | bool]:
    """Resolve defaults and reject missing or unknown deployment inputs."""

    by_key = {item.key: item for item in contract.inputs}
    unknown = sorted(set(supplied) - set(by_key))
    if unknown:
        raise ValueError(f"Unknown deployment input(s): {', '.join(unknown)}")
    resolved: dict[str, str | int | float | bool] = {}
    for key, item in by_key.items():
        if key in supplied:
            value = supplied[key]
        elif item.default is not None:
            value = item.default
        elif item.required:
            raise ValueError(f"Required deployment input `{key}` was not supplied.")
        else:
            continue
        _validate_input_value(item, value)
        resolved[key] = value
    return resolved


def _render_text_asset(
    text: str,
    contract: DeployContract,
    values: dict[str, str | int | float | bool],
    *,
    target: str,
) -> str:
    """Render exact text markers for one declared target."""

    rendered = text
    allowed: set[str] = set()
    for item in contract.inputs:
        for binding in item.bindings:
            if binding.mode != "text" or binding.target != target:
                continue
            assert binding.marker is not None
            allowed.add(binding.marker)
            if item.key in values:
                rendered = rendered.replace(binding.marker, str(values[item.key]))
    remaining = {
        marker
        for marker in _ANY_MARKER_RE.findall(rendered)
        if _INSTANCE_MARKER_RE.fullmatch(marker) is None
    }
    if remaining:
        raise ValueError(f"Unresolved or unknown deployment marker(s): {sorted(remaining)}")
    original = set(_ANY_MARKER_RE.findall(text))
    undeclared = original - allowed
    if undeclared:
        raise ValueError(f"Undeclared content edits are not allowed: {sorted(undeclared)}")
    return rendered


def _reject_authority_bearing_mindset_text(text: str) -> None:
    """Reject mindset content that claims instruction, tool, gate, or credential authority."""

    normalized = text.casefold()
    forbidden = (
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
    if any(fragment in normalized for fragment in forbidden):
        raise ValueError("Mindsets are low-authority reflection data, not instructions or secrets.")


def _resolve_structured_bindings(
    contract: DeployContract,
    values: dict[str, str | int | float | bool],
) -> dict[str, str | int | float | bool]:
    """Resolve declared structured field assignments."""

    fields: dict[str, str | int | float | bool] = {}
    for item in contract.inputs:
        if item.key not in values:
            continue
        for binding in item.bindings:
            if binding.mode != "field":
                continue
            if binding.target in fields:
                raise ValueError(f"Multiple inputs bind structured target `{binding.target}`.")
            fields[binding.target] = values[item.key]
    return fields


def _project_precondition_digest(overlay: HoumaoProjectOverlay) -> str:
    """Digest logical catalog rows as a stable apply precondition."""

    if not overlay.catalog_path.exists():
        return _sha256_bytes(b"missing")
    tables = (
        "catalog_meta",
        "auth_profiles",
        "skill_packages",
        "specialists",
        "launch_profiles",
        "agent_deployments",
    )
    payload: dict[str, list[list[Any]]] = {}
    with sqlite3.connect(overlay.catalog_path) as connection:
        for table in tables:
            columns = [
                str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            if not columns:
                payload[table] = []
                continue
            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            order = ", ".join(f'"{column}"' for column in columns)
            rows = connection.execute(
                f'SELECT {quoted_columns} FROM "{table}" ORDER BY {order}'
            ).fetchall()
            payload[table] = [list(row) for row in rows]
    return _sha256_bytes(_canonical_json(payload))


def _plan_digest(plan: DeploymentPlan) -> str:
    """Compute a plan digest with its self-field cleared."""

    payload = plan.model_dump(mode="json")
    payload["plan_digest"] = ""
    return _sha256_bytes(_canonical_json(payload))


def _register_agent_deployment(
    *,
    overlay: HoumaoProjectOverlay,
    plan: DeploymentPlan,
    plan_root: Path,
    deployment_id: str,
    batch_operation_id: str | None = None,
    batch_member_ordinal: int | None = None,
    connection: sqlite3.Connection | None = None,
) -> str:
    """Insert one deployment row after all ordinary catalog artifacts are ready."""

    timestamp = _utcnow_iso()

    def insert(target: sqlite3.Connection) -> None:
        """Insert the deployment row on one caller-owned connection."""

        target.execute(
            """
            INSERT INTO agent_deployments (
                deployment_id, deployment_name, definition_id, revision_id,
                revision_digest, instance_contract_digest, private_workspace_enabled,
                workspace_workdir_mode, workspace_contract_digest, batch_operation_id,
                batch_member_ordinal, request_path, request_digest,
                plan_path, plan_digest, specialist_name, profile_name, skill_names_payload,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                deployment_id,
                plan.deployment_name,
                plan.definition_id,
                plan.revision_id,
                plan.revision_digest,
                plan.instance_contract_digest,
                int(plan.private_workspace_enabled),
                plan.workspace_workdir_mode,
                plan.workspace_contract_digest,
                batch_operation_id,
                batch_member_ordinal,
                str(plan_root / "request.json"),
                plan.request_digest,
                str(plan_root),
                plan.plan_digest,
                plan.specialist_name,
                plan.profile_name,
                json.dumps(plan.skill_names),
                timestamp,
                timestamp,
            ),
        )

    if connection is not None:
        insert(connection)
    else:
        with sqlite3.connect(overlay.catalog_path) as owned_connection:
            owned_connection.execute("PRAGMA foreign_keys = ON")
            insert(owned_connection)
            owned_connection.commit()
    return deployment_id


__all__ = [
    "AgentDefinitionWorkspace",
    "DefinitionDocument",
    "DeployBinding",
    "DeployContract",
    "DeployInput",
    "DeploymentPlan",
    "DeploymentRequest",
    "InstanceContract",
    "MaterializationSpec",
    "MindsetContract",
    "PrivateWorkspaceContract",
    "RevisionValidation",
    "RuntimeVariableContract",
    "WorkspaceDirectoryContract",
    "apply_deployment",
    "approve_derivation",
    "create_deployment_request",
    "derive_intent",
    "deployment_instance_references",
    "doctor_agent_deployments",
    "init_intent",
    "inspect_agent_deployment",
    "load_instance_contract",
    "list_agent_deployments",
    "load_deployment_plan",
    "materialize_revision",
    "plan_deployment",
    "remove_agent_deployment",
    "resolve_revision_reference",
    "rollback_prepared_deployment",
    "source_set",
    "validate_revision",
    "workspace_contract_digest",
]
