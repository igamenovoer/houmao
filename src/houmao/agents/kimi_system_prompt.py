"""Native managed-home system-prompt support for Kimi Code 0.34 and later."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib
from typing import Any, Final, Literal, Mapping

import yaml


KIMI_SYSTEM_PROMPT_FILENAME: Final[str] = "SYSTEM.md"
KIMI_V2_ENGINE_ENV_VAR: Final[str] = "KIMI_CODE_LEGACY_FLAG"
KIMI_V2_ENGINE_ENV_VALUE: Final[str] = "0"
_KIMI_TEMPLATE_PREFIX: Final[str] = "${base_prompt}\n\n"
_KIMI_TEMPLATE_PLACEHOLDER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\$\{[A-Za-z_][A-Za-z0-9_]*\}"
)
_KIMI_AGENT_SELECTOR_FLAGS: Final[frozenset[str]] = frozenset({"--agent", "--agent-file"})
_KIMI_AGENT_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_KIMI_AGENT_SCAN_MAX_DEPTH: Final[int] = 8


class KimiSystemPromptError(ValueError):
    """Raised when Houmao cannot guarantee Kimi's native prompt contract."""


@dataclass(frozen=True)
class KimiSystemPromptProjection:
    """Result and provenance for one Kimi ``SYSTEM.md`` projection."""

    state: Literal["projected", "removed"]
    path: Path
    effective_prompt_sha256: str | None
    rendered_template_sha256: str | None
    base_prompt_preserved: bool
    changed: bool

    def to_payload(self) -> dict[str, str | bool | None]:
        """Return a JSON-serializable provenance payload."""

        return {
            "state": self.state,
            "path": str(self.path),
            "effective_prompt_sha256": self.effective_prompt_sha256,
            "rendered_template_sha256": self.rendered_template_sha256,
            "base_prompt_preserved": self.base_prompt_preserved,
            "changed": self.changed,
            "engine_env_var": KIMI_V2_ENGINE_ENV_VAR,
            "engine_env_value": KIMI_V2_ENGINE_ENV_VALUE,
        }


def prompt_sha256(prompt: str) -> str:
    """Return the UTF-8 SHA-256 digest for one effective prompt."""

    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def render_kimi_system_prompt(effective_prompt: str) -> str:
    """Render the canonical Kimi template for one complete Houmao prompt.

    Kimi expands every ``${identifier}`` token after loading ``SYSTEM.md``.
    Houmao therefore rejects all such tokens in the effective prompt rather
    than trying to invent an escaping convention that Kimi does not provide.
    """

    match = _KIMI_TEMPLATE_PLACEHOLDER_PATTERN.search(effective_prompt)
    if match is not None:
        raise KimiSystemPromptError(
            "Kimi native SYSTEM.md cannot safely preserve template placeholder "
            f"{match.group(0)!r} in the effective Houmao prompt. Remove or rewrite every "
            "`${identifier}` token before launching Kimi Code."
        )
    trailing_newline = "" if effective_prompt.endswith("\n") else "\n"
    return f"{_KIMI_TEMPLATE_PREFIX}{effective_prompt}{trailing_newline}"


def ensure_kimi_system_prompt(
    *,
    home_path: Path,
    effective_prompt: str,
) -> KimiSystemPromptProjection:
    """Atomically project or remove Kimi's managed native prompt file."""

    resolved_home = home_path.resolve()
    target = resolved_home / KIMI_SYSTEM_PROMPT_FILENAME
    if not effective_prompt.strip():
        changed = target.exists() or target.is_symlink()
        if changed:
            if target.is_dir() and not target.is_symlink():
                raise KimiSystemPromptError(
                    f"Cannot remove managed Kimi prompt path `{target}` because it is a directory."
                )
            try:
                target.unlink()
            except OSError as exc:
                raise KimiSystemPromptError(
                    f"Cannot remove managed Kimi prompt path `{target}`: {exc}."
                ) from exc
        return KimiSystemPromptProjection(
            state="removed",
            path=target,
            effective_prompt_sha256=None,
            rendered_template_sha256=None,
            base_prompt_preserved=False,
            changed=changed,
        )

    rendered = render_kimi_system_prompt(effective_prompt)
    existing = _read_existing_text(target)
    changed = existing != rendered or not _is_secure_regular_file(target)
    if changed:
        try:
            _atomic_write_text(target, rendered)
        except OSError as exc:
            raise KimiSystemPromptError(
                f"Cannot project managed Kimi prompt to `{target}`: {exc}."
            ) from exc
    rendered_digest = prompt_sha256(rendered)
    _verify_projected_prompt(target=target, expected_text=rendered, expected_digest=rendered_digest)
    return KimiSystemPromptProjection(
        state="projected",
        path=target,
        effective_prompt_sha256=prompt_sha256(effective_prompt),
        rendered_template_sha256=rendered_digest,
        base_prompt_preserved=True,
        changed=changed,
    )


def validate_kimi_native_prompt_launch(
    *,
    launch_args: list[str] | tuple[str, ...],
    working_directory: Path,
    home_path: Path,
) -> None:
    """Reject provider inputs that can outrank managed ``SYSTEM.md``."""

    selector = _find_agent_selector(launch_args)
    if selector is not None:
        raise KimiSystemPromptError(
            "Managed Kimi launches reserve the default agent profile for native SYSTEM.md; "
            f"remove higher-priority launch option `{selector}`."
        )

    conflicts = _find_default_agent_overrides(
        working_directory=working_directory,
        home_path=home_path,
    )
    if conflicts:
        rendered = ", ".join(str(path) for path in conflicts)
        raise KimiSystemPromptError(
            "Managed Kimi SYSTEM.md would be outranked by a default `agent` profile with "
            f"`override: true`: {rendered}. Remove the override before launching."
        )


def force_kimi_v2_engine_env(env: Mapping[str, str]) -> dict[str, str]:
    """Return environment records with Kimi's v2 engine enforced."""

    return {**env, KIMI_V2_ENGINE_ENV_VAR: KIMI_V2_ENGINE_ENV_VALUE}


def validate_kimi_v2_engine_env(env: Mapping[str, str]) -> None:
    """Require the final provider environment to select Kimi's v2 engine."""

    value = env.get(KIMI_V2_ENGINE_ENV_VAR)
    if value != KIMI_V2_ENGINE_ENV_VALUE:
        if value is not None and _is_truthy_env_value(value):
            raise KimiSystemPromptError(
                f"{KIMI_V2_ENGINE_ENV_VAR}={value!r} selects Kimi's legacy engine, which "
                "cannot honor Houmao's native SYSTEM.md contract."
            )
        raise KimiSystemPromptError(
            f"Managed Kimi launch requires {KIMI_V2_ENGINE_ENV_VAR}="
            f"{KIMI_V2_ENGINE_ENV_VALUE!r}; got {value!r}."
        )


def _find_agent_selector(launch_args: list[str] | tuple[str, ...]) -> str | None:
    """Return the first explicit Kimi agent selector in an argument vector."""

    for token in launch_args:
        if token in _KIMI_AGENT_SELECTOR_FLAGS:
            return token
        for flag in _KIMI_AGENT_SELECTOR_FLAGS:
            if token.startswith(f"{flag}="):
                return flag
    return None


def _find_default_agent_overrides(
    *,
    working_directory: Path,
    home_path: Path,
) -> tuple[Path, ...]:
    """Return project and configured profiles that override default ``agent``."""

    project_root = _find_project_root(working_directory.resolve())
    source_roots = (
        (project_root / ".kimi-code" / "agents", project_root / ".agents" / "agents"),
        _configured_extra_agent_dirs(home_path=home_path, project_root=project_root),
    )

    conflicts: list[Path] = []
    for roots in source_roots:
        conflict = _default_agent_override_in_roots(roots)
        if conflict is not None:
            conflicts.append(conflict)
    return tuple(conflicts)


def _find_project_root(working_directory: Path) -> Path:
    """Match Kimi's nearest-ancestor ``.git`` project-root rule."""

    current = working_directory
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return working_directory
        current = current.parent


def _configured_extra_agent_dirs(*, home_path: Path, project_root: Path) -> tuple[Path, ...]:
    """Load Kimi ``extra_agent_dirs`` roots from managed-home config."""

    config_path = home_path.resolve() / "config.toml"
    if not config_path.is_file():
        return ()
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise KimiSystemPromptError(
            f"Cannot validate Kimi agent precedence from `{config_path}`: {exc}."
        ) from exc
    raw_dirs = payload.get("extra_agent_dirs", [])
    if raw_dirs is None:
        return ()
    if not isinstance(raw_dirs, list) or not all(isinstance(item, str) for item in raw_dirs):
        raise KimiSystemPromptError(
            f"Kimi config `{config_path}` must define extra_agent_dirs as a list of strings."
        )
    roots: list[Path] = []
    for raw_dir in raw_dirs:
        expanded = Path(raw_dir).expanduser()
        roots.append(expanded if expanded.is_absolute() else project_root / expanded)
    return tuple(roots)


def _default_agent_override_in_roots(roots: tuple[Path, ...]) -> Path | None:
    """Return the selected default-agent override for one Kimi source lane."""

    seen_roots: set[Path] = set()
    for root in roots:
        resolved_root = root.expanduser().resolve()
        if resolved_root in seen_roots or not resolved_root.is_dir():
            continue
        seen_roots.add(resolved_root)
        for path in _iter_agent_markdown_files(resolved_root):
            parsed = _parse_agent_file_identity(path)
            if parsed is None:
                continue
            name, override = parsed
            if name == "agent":
                return path.resolve() if override else None
    return None


def _iter_agent_markdown_files(root: Path) -> tuple[Path, ...]:
    """Return Kimi-discoverable Markdown files in deterministic scan order."""

    paths: list[Path] = []

    def _walk(directory: Path, depth: int) -> None:
        """Walk one agent directory with Kimi's depth and skip rules."""

        if depth > _KIMI_AGENT_SCAN_MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name == "node_modules":
                continue
            try:
                if entry.is_dir():
                    _walk(entry, depth + 1)
                elif entry.name.endswith(".md") and entry.is_file():
                    paths.append(entry)
            except OSError:
                continue

    _walk(root, 0)
    return tuple(paths)


def _parse_agent_file_identity(path: Path) -> tuple[str, bool] | None:
    """Parse the Kimi fields that determine one discovered agent's identity."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    parsed = _load_frontmatter(text)
    if parsed is None:
        return None
    frontmatter, body = parsed
    raw_name = frontmatter.get("name")
    if raw_name is not None and not isinstance(raw_name, str):
        return None
    name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else path.stem
    if not _KIMI_AGENT_NAME_PATTERN.fullmatch(name):
        return None
    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip() or not body.strip():
        return None
    override = frontmatter.get("override")
    if override is not None and not isinstance(override, bool):
        return None
    for field in ("tools", "disallowedTools", "subagents"):
        if not _is_valid_agent_string_list(frontmatter.get(field)):
            return None
    model_preference = frontmatter.get("model_preference")
    if model_preference is not None and model_preference not in ("primary", "secondary"):
        return None
    return name, override is True


def _load_frontmatter(text: str) -> tuple[dict[str, Any], str] | None:
    """Load one valid YAML frontmatter mapping and its Markdown body."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        return None
    try:
        payload = yaml.safe_load("\n".join(lines[1:closing_index]))
    except yaml.YAMLError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload, "\n".join(lines[closing_index + 1 :])


def _is_valid_agent_string_list(value: object) -> bool:
    """Return whether one Kimi agent list field has accepted syntax."""

    if value is None or isinstance(value, str):
        return True
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _read_existing_text(path: Path) -> str | None:
    """Read one existing projection, returning ``None`` when absent."""

    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _is_secure_regular_file(path: Path) -> bool:
    """Return whether one projection is a non-symlink regular file with mode 0600."""

    try:
        metadata = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) == 0o600


def _verify_projected_prompt(*, target: Path, expected_text: str, expected_digest: str) -> None:
    """Verify final projection bytes, digest, file type, and permissions."""

    try:
        observed_bytes = target.read_bytes()
    except OSError as exc:
        raise KimiSystemPromptError(
            f"Cannot verify managed Kimi prompt at `{target}`: {exc}."
        ) from exc
    observed_digest = hashlib.sha256(observed_bytes).hexdigest()
    if observed_bytes != expected_text.encode("utf-8") or observed_digest != expected_digest:
        raise KimiSystemPromptError(
            f"Managed Kimi prompt verification failed for `{target}`: projected digest mismatch."
        )
    if not _is_secure_regular_file(target):
        raise KimiSystemPromptError(
            f"Managed Kimi prompt verification failed for `{target}`: expected a regular "
            "file with permissions 0600."
        )


def _atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8 text through same-directory atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        temp_path.chmod(0o600)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _is_truthy_env_value(value: str) -> bool:
    """Return whether one environment value conventionally means true."""

    return value.strip().lower() in {"1", "true", "yes", "on"}
