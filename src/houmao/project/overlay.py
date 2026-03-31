"""Repo-local Houmao project overlay discovery and bootstrap helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
import os
from pathlib import Path
import tomllib
from typing import Literal, Mapping, cast

from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.project.catalog import PROJECT_CATALOG_FILENAME, PROJECT_CONTENT_DIRNAME, ProjectCatalog

PROJECT_DIRNAME = ".houmao"
PROJECT_CONFIG_FILENAME = "houmao-config.toml"
PROJECT_GITIGNORE_FILENAME = ".gitignore"
PROJECT_EASY_DIRNAME = "easy"
PROJECT_MAILBOX_DIRNAME = "mailbox"
PROJECT_OVERLAY_DIR_ENV_VAR = "HOUMAO_PROJECT_OVERLAY_DIR"
DEFAULT_AGENT_DEF_DIR = Path(".houmao") / "agents"
_STARTER_ASSET_PACKAGE = "houmao.project.assets"
_STARTER_ASSET_ROOT = "starter_agents"

AgentDefDirSource = Literal["cli", "env", "project_config", "project_overlay_env", "default"]
ProjectOverlaySource = Literal["env", "discovered", "default"]


@dataclass(frozen=True)
class HoumaoProjectOverlay:
    """Resolved repo-local Houmao project overlay state."""

    project_root: Path
    overlay_root: Path
    config_path: Path
    schema_version: int
    agent_def_dir: Path

    @property
    def agents_root(self) -> Path:
        """Return the effective project-local agent-definition root."""

        return self.agent_def_dir.resolve()

    @property
    def catalog_path(self) -> Path:
        """Return the project-local SQLite catalog path."""

        return (self.overlay_root / PROJECT_CATALOG_FILENAME).resolve()

    @property
    def content_root(self) -> Path:
        """Return the project-local managed content root."""

        return (self.overlay_root / PROJECT_CONTENT_DIRNAME).resolve()

    @property
    def easy_root(self) -> Path:
        """Return the project-local easy metadata root."""

        return (self.overlay_root / PROJECT_EASY_DIRNAME).resolve()

    @property
    def specialists_root(self) -> Path:
        """Return the project-local specialist metadata root."""

        return (self.easy_root / "specialists").resolve()

    @property
    def mailbox_root(self) -> Path:
        """Return the project-local mailbox root."""

        return (self.overlay_root / PROJECT_MAILBOX_DIRNAME).resolve()


@dataclass(frozen=True)
class AgentDefDirResolution:
    """Resolved effective agent-definition root for project-aware commands."""

    agent_def_dir: Path
    source: AgentDefDirSource
    project_overlay: HoumaoProjectOverlay | None = None


@dataclass(frozen=True)
class ProjectOverlayResolution:
    """Resolved active project-overlay root for project-aware commands."""

    overlay_root: Path
    source: ProjectOverlaySource
    project_overlay: HoumaoProjectOverlay | None = None


@dataclass(frozen=True)
class ProjectInitResult:
    """Filesystem changes performed while bootstrapping one project overlay."""

    project_overlay: HoumaoProjectOverlay
    created_directories: tuple[Path, ...]
    written_files: tuple[Path, ...]
    preserved_files: tuple[Path, ...]


def project_overlay_root(project_root: Path) -> Path:
    """Return the repo-local `.houmao/` root for one project root."""

    return (project_root.resolve() / PROJECT_DIRNAME).resolve()


def project_config_path(project_root: Path) -> Path:
    """Return the repo-local `houmao-config.toml` path for one project root."""

    return overlay_config_path(project_overlay_root(project_root))


def overlay_config_path(overlay_root: Path) -> Path:
    """Return the `houmao-config.toml` path for one overlay root."""

    return (overlay_root.resolve() / PROJECT_CONFIG_FILENAME).resolve()


def render_default_project_config() -> str:
    """Render the default project-local config file."""

    return 'schema_version = 1\n\n[paths]\nagent_def_dir = "agents"\n'


def default_project_gitignore() -> str:
    """Return the local-only ignore policy for one project overlay."""

    return "*\n"


def discover_project_overlay(
    start_directory: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> HoumaoProjectOverlay | None:
    """Return the nearest ancestor repo-local Houmao overlay when present."""

    return resolve_project_overlay(cwd=start_directory, env=env).project_overlay


def require_project_overlay(
    start_directory: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> HoumaoProjectOverlay:
    """Return the nearest discovered project overlay or raise one actionable error."""

    resolution = resolve_project_overlay(cwd=start_directory.resolve(), env=env)
    project_overlay = resolution.project_overlay
    if project_overlay is None:
        if resolution.source == "env":
            raise ValueError(
                "No local Houmao project overlay was discovered at "
                f"`{resolution.overlay_root}`. Run `houmao-mgr project init` first."
            )
        raise ValueError(
            "No local Houmao project overlay was discovered from the current directory. "
            "Run `houmao-mgr project init` first."
        )
    return project_overlay


def load_project_overlay(config_path: Path) -> HoumaoProjectOverlay:
    """Parse one repo-local Houmao overlay config file."""

    resolved_config_path = config_path.expanduser().resolve()
    raw_payload = _load_toml_mapping(resolved_config_path)
    schema_version = raw_payload.get("schema_version")
    if schema_version != 1:
        raise ValueError(
            f"{resolved_config_path}: only schema_version=1 is supported for Houmao project configs."
        )
    raw_paths = _require_mapping(raw_payload, "paths", where=str(resolved_config_path))
    raw_agent_def_dir = _require_string(raw_paths, "agent_def_dir", where=str(resolved_config_path))
    overlay_root = resolved_config_path.parent.resolve()
    return HoumaoProjectOverlay(
        project_root=overlay_root.parent.resolve(),
        overlay_root=overlay_root,
        config_path=resolved_config_path,
        schema_version=1,
        agent_def_dir=_resolve_path(raw_agent_def_dir, base=overlay_root),
    )


def resolve_project_overlay(
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> ProjectOverlayResolution:
    """Resolve the active project-overlay root for project-aware commands."""

    resolved_cwd = cwd.resolve()
    overlay_root_override = _resolve_project_overlay_dir_env_override(env=env)
    if overlay_root_override is not None:
        project_overlay = _load_project_overlay_from_root(overlay_root_override)
        return ProjectOverlayResolution(
            overlay_root=overlay_root_override,
            source="env",
            project_overlay=project_overlay,
        )

    project_overlay = _discover_nearest_project_overlay(resolved_cwd)
    if project_overlay is not None:
        return ProjectOverlayResolution(
            overlay_root=project_overlay.overlay_root,
            source="discovered",
            project_overlay=project_overlay,
        )

    return ProjectOverlayResolution(
        overlay_root=(resolved_cwd / PROJECT_DIRNAME).resolve(),
        source="default",
    )


def resolve_project_init_overlay_root(
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve the overlay root `project init` should bootstrap."""

    overlay_root_override = _resolve_project_overlay_dir_env_override(env=env)
    if overlay_root_override is not None:
        return overlay_root_override
    return (cwd.resolve() / PROJECT_DIRNAME).resolve()


def resolve_project_aware_agent_def_dir(
    *,
    cwd: Path,
    cli_value: str | None = None,
    env: Mapping[str, str] | None = None,
) -> AgentDefDirResolution:
    """Resolve the effective project-aware compatibility-projection root."""

    resolved_cwd = cwd.resolve()
    if cli_value is not None:
        return AgentDefDirResolution(
            agent_def_dir=_resolve_path(cli_value, base=resolved_cwd),
            source="cli",
        )

    env_mapping = dict(os.environ) if env is None else dict(env)
    env_value = env_mapping.get(AGENT_DEF_DIR_ENV_VAR)
    if env_value is not None and env_value.strip():
        return AgentDefDirResolution(
            agent_def_dir=_resolve_path(env_value.strip(), base=resolved_cwd),
            source="env",
        )

    overlay_resolution = resolve_project_overlay(cwd=resolved_cwd, env=env_mapping)
    project_overlay = overlay_resolution.project_overlay
    if project_overlay is not None:
        return AgentDefDirResolution(
            agent_def_dir=project_overlay.agent_def_dir,
            source="project_config",
            project_overlay=project_overlay,
        )
    if overlay_resolution.source == "env":
        return AgentDefDirResolution(
            agent_def_dir=(overlay_resolution.overlay_root / "agents").resolve(),
            source="project_overlay_env",
        )

    return AgentDefDirResolution(
        agent_def_dir=(resolved_cwd / DEFAULT_AGENT_DEF_DIR).resolve(),
        source="default",
    )


def resolve_materialized_project_aware_agent_def_dir(
    *,
    cwd: Path,
    cli_value: str | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Resolve one filesystem agent-definition root for file-tree consumers."""

    resolution = resolve_project_aware_agent_def_dir(
        cwd=cwd,
        cli_value=cli_value,
        env=env,
    )
    if resolution.project_overlay is not None:
        return materialize_project_agent_catalog_projection(resolution.project_overlay)
    return resolution.agent_def_dir


def bootstrap_project_overlay(
    project_root: Path,
    *,
    include_compatibility_profiles: bool = False,
) -> ProjectInitResult:
    """Create or validate one repo-local Houmao project overlay from a project root."""

    return bootstrap_project_overlay_at_root(
        project_overlay_root(project_root),
        include_compatibility_profiles=include_compatibility_profiles,
    )


def bootstrap_project_overlay_at_root(
    overlay_root: Path,
    *,
    include_compatibility_profiles: bool = False,
) -> ProjectInitResult:
    """Create or validate one repo-local Houmao project overlay."""

    resolved_overlay_root = overlay_root.resolve()
    config_path = overlay_config_path(resolved_overlay_root)
    catalog_path = (resolved_overlay_root / PROJECT_CATALOG_FILENAME).resolve()
    content_root = (resolved_overlay_root / PROJECT_CONTENT_DIRNAME).resolve()
    created_directories: list[Path] = []
    written_files: list[Path] = []
    preserved_files: list[Path] = []

    bootstrap_directories = [
        resolved_overlay_root,
        content_root,
        content_root / "prompts",
        content_root / "auth",
        content_root / "skills",
        content_root / "setups",
    ]

    for directory in bootstrap_directories:
        _ensure_directory(directory, created_directories=created_directories)

    gitignore_path = (resolved_overlay_root / PROJECT_GITIGNORE_FILENAME).resolve()
    _ensure_default_gitignore(
        gitignore_path,
        written_files=written_files,
        preserved_files=preserved_files,
    )

    if config_path.exists():
        existing_overlay = load_project_overlay(config_path)
        _validate_agent_def_dir_root(existing_overlay.agent_def_dir)
        preserved_files.append(config_path)
    else:
        config_path.write_text(render_default_project_config(), encoding="utf-8")
        written_files.append(config_path)

    overlay = load_project_overlay(config_path)
    catalog_was_present = catalog_path.exists()
    ProjectCatalog.from_overlay(overlay).initialize()
    if catalog_was_present:
        preserved_files.append(catalog_path)
    else:
        written_files.append(catalog_path)

    if include_compatibility_profiles:
        ensure_project_agent_compatibility_tree(
            overlay,
            include_compatibility_profiles=True,
            created_directories=created_directories,
            written_files=written_files,
            preserved_files=preserved_files,
        )

    return ProjectInitResult(
        project_overlay=overlay,
        created_directories=tuple(dict.fromkeys(created_directories)),
        written_files=tuple(dict.fromkeys(written_files)),
        preserved_files=tuple(dict.fromkeys(preserved_files)),
    )


def _discover_nearest_project_overlay(start_directory: Path) -> HoumaoProjectOverlay | None:
    """Return the nearest ancestor repo-local Houmao overlay when present."""

    resolved_start = start_directory.resolve()
    for candidate_root in (resolved_start, *resolved_start.parents):
        candidate_config = overlay_config_path(candidate_root / PROJECT_DIRNAME)
        if candidate_config.is_file():
            return load_project_overlay(candidate_config)
    return None


def _load_project_overlay_from_root(overlay_root: Path) -> HoumaoProjectOverlay | None:
    """Load one project overlay from its root when the config is present."""

    config_path = overlay_config_path(overlay_root)
    if not config_path.is_file():
        return None
    return load_project_overlay(config_path)


def _resolve_project_overlay_dir_env_override(
    *,
    env: Mapping[str, str] | None,
) -> Path | None:
    """Resolve one optional absolute project-overlay override from the environment."""

    env_mapping = dict(os.environ) if env is None else dict(env)
    env_value = env_mapping.get(PROJECT_OVERLAY_DIR_ENV_VAR)
    if env_value is None or not env_value.strip():
        return None

    candidate = Path(env_value.strip()).expanduser()
    if not candidate.is_absolute():
        raise ValueError(f"`{PROJECT_OVERLAY_DIR_ENV_VAR}` must be an absolute path.")
    return candidate.resolve()


def ensure_project_agent_compatibility_tree(
    overlay: HoumaoProjectOverlay,
    *,
    include_compatibility_profiles: bool = False,
    created_directories: list[Path] | None = None,
    written_files: list[Path] | None = None,
    preserved_files: list[Path] | None = None,
) -> Path:
    """Ensure the non-authoritative compatibility projection tree exists."""

    created = [] if created_directories is None else created_directories
    written = [] if written_files is None else written_files
    preserved = [] if preserved_files is None else preserved_files
    projection_root = overlay.agents_root
    for directory in (
        projection_root,
        projection_root / "skills",
        projection_root / "roles",
        projection_root / "tools",
    ):
        _ensure_directory(directory, created_directories=created)
    if include_compatibility_profiles:
        _ensure_directory(
            projection_root / "compatibility-profiles",
            created_directories=created,
        )
    _copy_starter_assets(
        destination_root=projection_root,
        written_files=written,
        preserved_files=preserved,
        created_directories=created,
    )
    _ensure_tool_auth_roots(
        agent_def_dir=projection_root,
        created_directories=created,
    )
    return projection_root


def materialize_project_agent_catalog_projection(overlay: HoumaoProjectOverlay) -> Path:
    """Materialize the project-local compatibility tree from the catalog."""

    ensure_project_agent_compatibility_tree(overlay)
    return ProjectCatalog.from_overlay(overlay).materialize_projection()


def _ensure_default_gitignore(
    path: Path,
    *,
    written_files: list[Path],
    preserved_files: list[Path],
) -> None:
    """Ensure the local overlay `.gitignore` keeps the subtree untracked."""

    if not path.exists():
        path.write_text(default_project_gitignore(), encoding="utf-8")
        written_files.append(path)
        return
    if path.is_dir():
        raise ValueError(f"Expected `{path}` to be a file.")
    non_comment_lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if "*" not in non_comment_lines:
        raise ValueError(
            f"{path}: existing local ignore policy is incompatible; expected a `*` rule."
        )
    preserved_files.append(path)


def _copy_starter_assets(
    *,
    destination_root: Path,
    written_files: list[Path],
    preserved_files: list[Path],
    created_directories: list[Path],
) -> None:
    """Copy packaged starter assets into the local agent-definition tree."""

    starter_root = resources.files(_STARTER_ASSET_PACKAGE) / _STARTER_ASSET_ROOT
    if not starter_root.is_dir():
        raise ValueError("Packaged Houmao project starter assets are missing.")
    _copy_traversable_tree(
        source=starter_root,
        destination=destination_root,
        written_files=written_files,
        preserved_files=preserved_files,
        created_directories=created_directories,
    )


def _copy_traversable_tree(
    *,
    source: Traversable,
    destination: Path,
    written_files: list[Path],
    preserved_files: list[Path],
    created_directories: list[Path],
) -> None:
    """Recursively copy one packaged resource tree without overwriting files."""

    if source.is_dir():
        _ensure_directory(destination, created_directories=created_directories)
        for child in sorted(source.iterdir(), key=lambda item: item.name):
            _copy_traversable_tree(
                source=child,
                destination=destination / child.name,
                written_files=written_files,
                preserved_files=preserved_files,
                created_directories=created_directories,
            )
        return

    if destination.exists():
        if destination.is_dir():
            raise ValueError(f"Expected `{destination}` to be a file.")
        preserved_files.append(destination)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    written_files.append(destination)


def _ensure_tool_auth_roots(
    *,
    agent_def_dir: Path,
    created_directories: list[Path],
) -> None:
    """Create empty auth roots for packaged tool starter content."""

    tools_root = (agent_def_dir / "tools").resolve()
    if not tools_root.is_dir():
        return
    for tool_dir in sorted(path for path in tools_root.iterdir() if path.is_dir()):
        _ensure_directory(tool_dir / "auth", created_directories=created_directories)


def _ensure_directory(path: Path, *, created_directories: list[Path]) -> None:
    """Ensure one directory exists and record newly created paths."""

    if path.exists():
        if not path.is_dir():
            raise ValueError(f"Expected `{path}` to be a directory.")
        return
    path.mkdir(parents=True, exist_ok=True)
    created_directories.append(path)


def _validate_agent_def_dir_root(path: Path) -> None:
    """Validate one configured compatibility-projection root when present."""

    if path.exists() and not path.is_dir():
        raise ValueError(
            "Configured Houmao compatibility-projection root must be a directory when it exists: "
            f"`{path}`."
        )


def _load_toml_mapping(path: Path) -> dict[str, object]:
    """Load one TOML mapping from disk."""

    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ValueError(f"Missing Houmao project config: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Malformed Houmao project config `{path}`: {exc}.") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a top-level TOML table.")
    return cast(dict[str, object], raw)


def _require_mapping(
    payload: Mapping[str, object], key: str, *, where: str
) -> Mapping[str, object]:
    """Require one mapping value from a parsed config payload."""

    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{where}: missing table `{key}`.")
    return cast(Mapping[str, object], value)


def _require_string(payload: Mapping[str, object], key: str, *, where: str) -> str:
    """Require one non-empty string value from a parsed config payload."""

    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: missing string `{key}`.")
    return value.strip()


def _resolve_path(value: str, *, base: Path) -> Path:
    """Resolve one possibly relative path from the provided base directory."""

    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base.resolve() / candidate).resolve()
