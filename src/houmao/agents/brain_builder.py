from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.owned_paths import resolve_runtime_root
from houmao.agents.mailbox_runtime_support import (
    parse_declarative_mailbox_config,
    project_runtime_mailbox_system_skills,
    serialize_declarative_mailbox_config,
)
from houmao.agents.mailbox_runtime_models import MailboxDeclarativeConfig
from houmao.agents.realm_controller.agent_identity import (
    derive_agent_id_from_name,
    normalize_agent_identity_name,
)

_AGENT_DEF_DIR_ENV_VAR = "AGENTSYS_AGENT_DEF_DIR"
_DEFAULT_AGENT_DEF_DIR = Path(".agentsys") / "agents"


class BuildError(RuntimeError):
    """Raised when brain construction cannot proceed."""


@dataclass(frozen=True)
class CredentialFileMapping:
    source: str
    destination: str
    mode: str
    required: bool = True


@dataclass(frozen=True)
class ToolAdapter:
    tool: str
    home_selector_env_var: str
    launch_executable: str
    launch_args: list[str]
    env_injection_mode: str
    env_file_in_home: str | None
    config_destination: str
    skills_destination: str
    skills_mode: str
    credential_files_dir: str
    credential_file_mappings: list[CredentialFileMapping]
    credential_env_source: str
    credential_env_allowlist: list[str]


@dataclass(frozen=True)
class BrainRecipe:
    name: str
    tool: str
    skills: list[str]
    config_profile: str
    credential_profile: str
    default_agent_name: str | None = None
    mailbox: MailboxDeclarativeConfig | None = None


@dataclass(frozen=True)
class BuildRequest:
    agent_def_dir: Path
    tool: str
    skills: list[str]
    config_profile: str
    credential_profile: str
    runtime_root: Path | None = None
    mailbox: MailboxDeclarativeConfig | None = None
    agent_name: str | None = None
    agent_id: str | None = None
    home_id: str | None = None
    reuse_home: bool = False


@dataclass(frozen=True)
class BuildResult:
    home_id: str
    home_path: Path
    manifest_path: Path
    launch_helper_path: Path
    launch_preview: str
    manifest: dict[str, Any]


def _load_mapping_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise BuildError(f"Missing file: {path}")

    text = path.read_text(encoding="utf-8")

    try:
        import yaml

        loaded = yaml.safe_load(text)
    except Exception:
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Could not parse {path} as YAML/JSON: {exc}") from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise BuildError(f"Expected top-level mapping in {path}")
    return loaded


def _write_mapping_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml

        content = yaml.safe_dump(payload, sort_keys=False)
    except Exception:
        content = json.dumps(payload, indent=2, sort_keys=False)
    path.write_text(content, encoding="utf-8")


def _require_mapping(payload: dict[str, Any], key: str, *, where: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise BuildError(f"{where}: missing mapping `{key}`")
    return value


def _require_str(payload: dict[str, Any], key: str, *, where: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BuildError(f"{where}: missing string `{key}`")
    return value


def _require_str_list(payload: dict[str, Any], key: str, *, where: str) -> list[str]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise BuildError(f"{where}: expected list of strings for `{key}`")
    return value


def _load_tool_adapter(path: Path) -> ToolAdapter:
    payload = _load_mapping_file(path)

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise BuildError(f"{path}: only schema_version=1 is supported")

    home_selector = _require_mapping(payload, "home_selector", where=str(path))
    launch = _require_mapping(payload, "launch", where=str(path))
    config_projection = _require_mapping(payload, "config_projection", where=str(path))
    skills_projection = _require_mapping(payload, "skills_projection", where=str(path))
    credential_projection = _require_mapping(payload, "credential_projection", where=str(path))
    credential_env = _require_mapping(credential_projection, "env", where=str(path))

    env_injection = _require_mapping(launch, "env_injection", where=str(path))
    env_injection_mode = _require_str(env_injection, "mode", where=str(path))
    if env_injection_mode not in {"home_dotenv", "export_from_env_file"}:
        raise BuildError(
            f"{path}: launch.env_injection.mode must be home_dotenv or export_from_env_file"
        )

    env_file_in_home: str | None = env_injection.get("env_file_in_home")
    if env_file_in_home is not None and not isinstance(env_file_in_home, str):
        raise BuildError(f"{path}: launch.env_injection.env_file_in_home must be a string")

    file_mappings: list[CredentialFileMapping] = []
    for idx, raw_mapping in enumerate(credential_projection.get("file_mappings", [])):
        if not isinstance(raw_mapping, dict):
            raise BuildError(f"{path}: file_mappings[{idx}] must be a mapping")
        required = raw_mapping.get("required", True)
        if not isinstance(required, bool):
            raise BuildError(f"{path}: file_mappings[{idx}].required must be a boolean")
        mapping = CredentialFileMapping(
            required=required,
            source=_require_str(raw_mapping, "source", where=f"{path}:file_mappings[{idx}]"),
            destination=_require_str(
                raw_mapping,
                "destination",
                where=f"{path}:file_mappings[{idx}]",
            ),
            mode=_require_str(raw_mapping, "mode", where=f"{path}:file_mappings[{idx}]"),
        )
        if mapping.mode not in {"symlink", "copy"}:
            raise BuildError(
                f"{path}: file_mappings[{idx}].mode must be `symlink` or `copy`, "
                f"got {mapping.mode!r}"
            )
        file_mappings.append(mapping)

    skills_mode = _require_str(skills_projection, "mode", where=str(path))
    if skills_mode not in {"symlink", "copy"}:
        raise BuildError(f"{path}: skills_projection.mode must be `symlink` or `copy`")

    adapter = ToolAdapter(
        tool=_require_str(payload, "tool", where=str(path)),
        home_selector_env_var=_require_str(home_selector, "env_var", where=str(path)),
        launch_executable=_require_str(launch, "executable", where=str(path)),
        launch_args=_require_str_list(launch, "args", where=str(path)),
        env_injection_mode=env_injection_mode,
        env_file_in_home=env_file_in_home,
        config_destination=_require_str(config_projection, "destination", where=str(path)),
        skills_destination=_require_str(skills_projection, "destination", where=str(path)),
        skills_mode=skills_mode,
        credential_files_dir=_require_str(credential_projection, "files_dir", where=str(path)),
        credential_file_mappings=file_mappings,
        credential_env_source=_require_str(credential_env, "source", where=str(path)),
        credential_env_allowlist=_require_str_list(credential_env, "allowlist", where=str(path)),
    )
    return adapter


def load_brain_recipe(path: Path) -> BrainRecipe:
    payload = _load_mapping_file(path)
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise BuildError(f"{path}: only schema_version=1 recipes are supported")

    skills = _require_str_list(payload, "skills", where=str(path))
    default_agent_name = payload.get("default_agent_name")
    if default_agent_name is not None:
        if not isinstance(default_agent_name, str) or not default_agent_name.strip():
            raise BuildError(f"{path}: default_agent_name must be a non-empty string when set")
    try:
        mailbox = parse_declarative_mailbox_config(
            payload.get("mailbox"),
            source=str(path),
        )
    except ValueError as exc:
        raise BuildError(str(exc)) from exc
    recipe = BrainRecipe(
        name=_require_str(payload, "name", where=str(path)),
        tool=_require_str(payload, "tool", where=str(path)),
        skills=skills,
        config_profile=_require_str(payload, "config_profile", where=str(path)),
        credential_profile=_require_str(payload, "credential_profile", where=str(path)),
        default_agent_name=default_agent_name.strip()
        if isinstance(default_agent_name, str)
        else None,
        mailbox=mailbox,
    )
    return recipe


def _parse_env_file(path: Path) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    if not path.exists():
        raise BuildError(f"Missing credential env file: {path}")

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        env_vars[key] = value
    return env_vars


def _ensure_clean_target(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def _project_path(source: Path, target: Path, *, mode: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _ensure_clean_target(target)

    if mode == "symlink":
        relative_target = os.path.relpath(source, target.parent)
        target.symlink_to(relative_target)
        return
    if mode != "copy":
        raise BuildError(f"Unsupported projection mode: {mode}")

    if source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


def _copy_directory_contents(source_dir: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for child in sorted(source_dir.iterdir()):
        _project_path(child, destination_dir / child.name, mode="copy")


def _validate_skill_names(skills_root: Path, selected_skills: list[str]) -> None:
    for skill in selected_skills:
        skill_dir = skills_root / skill
        skill_markdown = skill_dir / "SKILL.md"
        if not skill_dir.is_dir() or not skill_markdown.is_file():
            raise BuildError(f"Unknown skill `{skill}` (expected {skill_markdown} to exist)")


def _generate_home_id(tool: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
    short_uuid = uuid.uuid4().hex[:6]
    return f"{tool}-brain-{timestamp}-{short_uuid}"


def _validate_relative_path(value: str, *, field: str) -> None:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise BuildError(f"{field} must be a relative path, got {value!r}")


def _build_launch_helper(
    *,
    home_path: Path,
    helper_path: Path,
    adapter: ToolAdapter,
    env_file: Path,
) -> str:
    allowlist = adapter.credential_env_allowlist
    args = " ".join(shlex.quote(arg) for arg in adapter.launch_args)
    executable = shlex.quote(adapter.launch_executable)
    command_suffix = f" {args}" if args else ""
    project_root = Path(__file__).resolve().parents[3]
    pixi_manifest = project_root / "pixi.toml"
    if not pixi_manifest.is_file():
        pixi_manifest = project_root / "pyproject.toml"
    src_root = Path(__file__).resolve().parents[2]

    script_lines: list[str] = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"export {adapter.home_selector_env_var}={shlex.quote(str(home_path))}",
    ]

    if allowlist:
        script_lines.extend(
            [
                f"ENV_FILE={shlex.quote(str(env_file))}",
                'if [[ -f "${ENV_FILE}" ]]; then',
                '  while IFS= read -r line || [[ -n "${line}" ]]; do',
                '    [[ -z "${line}" ]] && continue',
                '    [[ "${line:0:1}" == "#" ]] && continue',
                '    key="${line%%=*}"',
                '    value="${line#*=}"',
                '    case "${key}" in',
            ]
        )
        for key in allowlist:
            script_lines.append(f'      {key}) export "${{key}}=${{value}}" ;;')
        script_lines.extend(
            [
                "      *) ;;",
                "    esac",
                '  done < "${ENV_FILE}"',
                "fi",
            ]
        )

    if adapter.tool in {"claude", "codex"}:
        script_lines.extend(
            [
                "BOOTSTRAP_PYTHON=()",
                f"if command -v pixi >/dev/null 2>&1 && [[ -f {shlex.quote(str(pixi_manifest))} ]]; then",
                f"  BOOTSTRAP_PYTHON=(pixi run --manifest-path {shlex.quote(str(pixi_manifest))} python)",
                "else",
                '  PYTHON_BIN="$(command -v python3 || command -v python || true)"',
                '  if [[ -z "${PYTHON_BIN}" ]]; then',
                '    echo "launch helper requires `pixi`, `python3`, or `python` on PATH." >&2',
                "    exit 127",
                "  fi",
                f"  export PYTHONPATH={shlex.quote(str(src_root))}${{PYTHONPATH:+:${{PYTHONPATH}}}}",
                '  BOOTSTRAP_PYTHON=("${PYTHON_BIN}")',
                "fi",
            ]
        )

    if adapter.tool == "claude":
        script_lines.extend(
            [
                "\"${BOOTSTRAP_PYTHON[@]}\" - <<'PY'",
                "from pathlib import Path",
                "import os",
                "",
                "from houmao.agents.realm_controller.backends.claude_bootstrap import (",
                "    ensure_claude_home_bootstrap,",
                ")",
                "",
                "ensure_claude_home_bootstrap(",
                "    home_path=Path(os.environ['CLAUDE_CONFIG_DIR']),",
                "    env=dict(os.environ),",
                ")",
                "PY",
            ]
        )
    if adapter.tool == "codex":
        script_lines.extend(
            [
                "\"${BOOTSTRAP_PYTHON[@]}\" - <<'PY'",
                "from pathlib import Path",
                "import os",
                "",
                "from houmao.agents.realm_controller.backends.codex_bootstrap import (",
                "    ensure_codex_home_bootstrap,",
                ")",
                "",
                "ensure_codex_home_bootstrap(",
                "    home_path=Path(os.environ['CODEX_HOME']),",
                "    env=dict(os.environ),",
                "    working_directory=Path.cwd(),",
                ")",
                "PY",
            ]
        )

    script_lines.append(f'exec {executable}{command_suffix} "$@"')

    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    helper_path.chmod(0o755)
    return shlex.quote(str(helper_path))


def build_brain_home(request: BuildRequest) -> BuildResult:
    agent_def_dir = request.agent_def_dir.resolve()
    runtime_root = resolve_runtime_root(explicit_root=request.runtime_root)

    adapter_path = agent_def_dir / "brains" / "tool-adapters" / f"{request.tool}.yaml"
    if not adapter_path.is_file():
        raise BuildError(f"Missing adapter for tool `{request.tool}`: {adapter_path}")

    adapter = _load_tool_adapter(adapter_path)
    if adapter.tool != request.tool:
        raise BuildError(
            f"Adapter tool mismatch: requested `{request.tool}`, adapter says `{adapter.tool}`"
        )

    skills_root = agent_def_dir / "brains" / "skills"
    config_profile_dir = (
        agent_def_dir / "brains" / "cli-configs" / request.tool / request.config_profile
    )
    credential_profile_dir = (
        agent_def_dir / "brains" / "api-creds" / request.tool / request.credential_profile
    )

    if not skills_root.is_dir():
        raise BuildError(f"Missing skills repository: {skills_root}")
    _validate_skill_names(skills_root=skills_root, selected_skills=request.skills)

    if not config_profile_dir.is_dir():
        raise BuildError(f"Missing config profile: {config_profile_dir}")
    if not credential_profile_dir.is_dir():
        raise BuildError(f"Missing credential profile: {credential_profile_dir}")

    home_id = request.home_id or _generate_home_id(request.tool)
    if "/" in home_id or "\\" in home_id:
        raise BuildError(f"home_id must not contain path separators: {home_id!r}")

    homes_dir = runtime_root / "homes"
    manifests_dir = runtime_root / "manifests"
    home_path = homes_dir / home_id

    if home_path.exists() and not request.reuse_home:
        raise BuildError(
            f"Refusing to reuse existing home (fresh-by-default): {home_path}. "
            "Use --reuse-home to allow reuse."
        )

    home_path.mkdir(parents=True, exist_ok=request.reuse_home)

    _validate_relative_path(adapter.config_destination, field="config_projection.destination")
    config_destination = home_path / adapter.config_destination
    _copy_directory_contents(config_profile_dir, config_destination)

    _validate_relative_path(adapter.skills_destination, field="skills_projection.destination")
    skill_destination_dir = home_path / adapter.skills_destination
    skill_destination_dir.mkdir(parents=True, exist_ok=True)
    for skill_name in request.skills:
        source = skills_root / skill_name
        destination = skill_destination_dir / skill_name
        _project_path(source, destination, mode=adapter.skills_mode)
    project_runtime_mailbox_system_skills(skill_destination_dir)

    _validate_relative_path(adapter.credential_files_dir, field="credential_projection.files_dir")
    credential_files_dir = credential_profile_dir / adapter.credential_files_dir
    projected_credentials: list[dict[str, Any]] = []
    for mapping in adapter.credential_file_mappings:
        _validate_relative_path(
            mapping.source,
            field=f"credential_projection.file_mappings[{mapping.source}].source",
        )
        _validate_relative_path(
            mapping.destination,
            field=f"credential_projection.file_mappings[{mapping.source}].destination",
        )
        source = credential_files_dir / mapping.source
        if not source.exists():
            if mapping.required:
                raise BuildError(
                    f"Missing credential file for mapping `{mapping.source}` in profile "
                    f"{credential_profile_dir}"
                )
            continue
        destination = home_path / mapping.destination
        _project_path(source, destination, mode=mapping.mode)
        projected_credentials.append(
            {
                "source": str(source),
                "destination": str(destination),
                "mode": mapping.mode,
                "required": mapping.required,
            }
        )

    _validate_relative_path(adapter.credential_env_source, field="credential_projection.env.source")
    credential_env_file = credential_profile_dir / adapter.credential_env_source
    env_values = _parse_env_file(credential_env_file)
    selected_env_names = [key for key in adapter.credential_env_allowlist if key in env_values]

    if adapter.env_injection_mode == "home_dotenv":
        env_file_in_home = adapter.env_file_in_home or ".env"
        _validate_relative_path(env_file_in_home, field="launch.env_injection.env_file_in_home")
        _project_path(credential_env_file, home_path / env_file_in_home, mode="symlink")

    launch_helper_path = home_path / "launch.sh"
    launch_preview = _build_launch_helper(
        home_path=home_path,
        helper_path=launch_helper_path,
        adapter=adapter,
        env_file=credential_env_file,
    )

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "built_at_utc": datetime.now(UTC).isoformat(),
        "inputs": {
            "tool": request.tool,
            "skills": request.skills,
            "config_profile": request.config_profile,
            "credential_profile": request.credential_profile,
            "adapter_path": str(adapter_path),
        },
        "runtime": {
            "runtime_root": str(runtime_root),
            "home_id": home_id,
            "home_path": str(home_path),
            "launch_helper": str(launch_helper_path),
            "launch_home_selector": {
                "env_var": adapter.home_selector_env_var,
                "value": str(home_path),
            },
            "launch_executable": adapter.launch_executable,
            "launch_args": adapter.launch_args,
        },
        "credentials": {
            "profile_path": str(credential_profile_dir),
            "projected_files": projected_credentials,
            "env_contract": {
                "source_file": str(credential_env_file),
                "allowlisted_env_vars": adapter.credential_env_allowlist,
                "selected_env_vars": selected_env_names,
                "injection_mode": adapter.env_injection_mode,
            },
        },
    }
    if request.mailbox is not None:
        manifest["mailbox"] = serialize_declarative_mailbox_config(request.mailbox)
    if request.agent_name is not None or request.agent_id is not None:
        canonical_agent_name = (
            normalize_agent_identity_name(request.agent_name).canonical_name
            if request.agent_name is not None
            else None
        )
        manifest["identity"] = {
            "canonical_agent_name": canonical_agent_name,
            "agent_id": request.agent_id
            or (
                derive_agent_id_from_name(canonical_agent_name)
                if canonical_agent_name is not None
                else None
            ),
        }

    manifest_path = manifests_dir / f"{home_id}.yaml"
    _write_mapping_file(manifest_path, manifest)

    return BuildResult(
        home_id=home_id,
        home_path=home_path,
        manifest_path=manifest_path,
        launch_helper_path=launch_helper_path,
        launch_preview=launch_preview,
        manifest=manifest,
    )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fresh runtime CLI home from reusable brain components."
    )
    parser.add_argument("--recipe", help="Path to brain recipe YAML/JSON")
    parser.add_argument(
        "--agent-def-dir",
        default=None,
        help=(
            "Agent definition directory root (contains brains/, roles/, blueprints/). "
            "Precedence: CLI > AGENTSYS_AGENT_DEF_DIR > <pwd>/.agentsys/agents."
        ),
    )
    parser.add_argument(
        "--runtime-root",
        default=None,
        help="Runtime root for generated homes/manifests",
    )
    parser.add_argument("--tool", help="Tool name (codex/claude/gemini)")
    parser.add_argument(
        "--skill",
        dest="skills",
        action="append",
        default=[],
        help="Skill name to install (repeatable)",
    )
    parser.add_argument("--config-profile", help="Tool config profile name")
    parser.add_argument("--cred-profile", help="Credential profile name")
    parser.add_argument("--home-id", help="Optional fixed home id")
    parser.add_argument(
        "--reuse-home",
        action="store_true",
        help="Allow building into an existing home id (fresh-by-default is off)",
    )
    return parser.parse_args(argv)


def _normalize_path(value: str, *, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def main(argv: list[str] | None = None) -> int:
    namespace = _parse_args(argv or sys.argv[1:])
    cwd = Path.cwd().resolve()
    agent_def_dir = _resolve_agent_def_dir(namespace.agent_def_dir, cwd=cwd)
    runtime_root = _normalize_path(namespace.runtime_root, base=cwd) if namespace.runtime_root else None

    recipe: BrainRecipe | None = None
    if namespace.recipe:
        recipe_path = _normalize_path(namespace.recipe, base=agent_def_dir)
        recipe = load_brain_recipe(recipe_path)

    tool_raw = namespace.tool or (recipe.tool if recipe else None)
    skills_raw = namespace.skills or (recipe.skills if recipe else [])
    config_profile_raw = namespace.config_profile or (recipe.config_profile if recipe else None)
    credential_profile_raw = namespace.cred_profile or (
        recipe.credential_profile if recipe else None
    )

    missing: list[str] = []
    if not tool_raw:
        missing.append("--tool (or recipe.tool)")
    if not config_profile_raw:
        missing.append("--config-profile (or recipe.config_profile)")
    if not credential_profile_raw:
        missing.append("--cred-profile (or recipe.credential_profile)")
    if not skills_raw:
        missing.append("at least one --skill (or recipe.skills)")
    if missing:
        raise BuildError(f"Missing required inputs: {', '.join(missing)}")

    assert tool_raw is not None
    assert config_profile_raw is not None
    assert credential_profile_raw is not None
    skills = [str(skill) for skill in skills_raw]

    request = BuildRequest(
        agent_def_dir=agent_def_dir,
        runtime_root=runtime_root,
        tool=tool_raw,
        skills=skills,
        config_profile=config_profile_raw,
        credential_profile=credential_profile_raw,
        mailbox=recipe.mailbox if recipe else None,
        agent_name=recipe.default_agent_name if recipe else None,
        home_id=namespace.home_id,
        reuse_home=namespace.reuse_home,
    )

    result = build_brain_home(request)

    print(f"Built brain home: {result.home_path}")
    print(f"Resolved manifest: {result.manifest_path}")
    print(f"Launch helper: {result.launch_helper_path}")
    print(f"Launch command: {result.launch_preview}")
    return 0


def _resolve_agent_def_dir(cli_value: str | None, *, cwd: Path) -> Path:
    if cli_value is not None:
        return _normalize_path(cli_value, base=cwd)

    env_value = os.environ.get(_AGENT_DEF_DIR_ENV_VAR)
    if env_value:
        return _normalize_path(env_value, base=cwd)

    return (cwd / _DEFAULT_AGENT_DEF_DIR).resolve()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
