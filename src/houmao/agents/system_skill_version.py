"""Strict version metadata parsing for public Houmao system-skill roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Literal

from packaging.version import InvalidVersion, Version
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode

from houmao.agents.system_skill_manifest import (
    EXPECTED_STANDALONE_SKILL_NAMES,
    SystemSkillManifest,
    standalone_system_skill_source_path,
)


FrontmatterErrorCode = Literal[
    "missing-file",
    "malformed-delimiters",
    "malformed-yaml",
    "duplicate-key",
    "missing-name",
    "invalid-name",
    "name-mismatch",
    "missing-version",
    "non-string-version",
    "invalid-version",
]


class SystemSkillFrontmatterError(RuntimeError):
    """Raised when one public top-level skill has invalid version metadata."""

    def __init__(self, *, code: FrontmatterErrorCode, path: Path, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """PyYAML safe loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    """Construct one YAML mapping while rejecting duplicate keys."""

    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)  # type: ignore[no-untyped-call]
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(  # type: ignore[no-untyped-call]
            value_node,
            deep=deep,
        )
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class TopLevelSystemSkillFrontmatter:
    """Validated name and release metadata from one public ``SKILL.md`` root."""

    path: Path
    name: str
    houmao_version: str
    raw_frontmatter: str


@dataclass(frozen=True)
class SystemSkillVersionSourceIssue:
    """One source root that does not match the project release version."""

    skill_name: str
    path: Path
    expected_version: str
    observed_version: str | None
    problem: str


@dataclass(frozen=True)
class SystemSkillVersionSourceCheck:
    """Read-only result of checking all six public source roots."""

    project_version: str
    checked_skill_names: tuple[str, ...]
    issues: tuple[SystemSkillVersionSourceIssue, ...]

    @property
    def healthy(self) -> bool:
        """Return whether every source root exactly matches the project release."""

        return not self.issues


def parse_top_level_system_skill_frontmatter(
    path: Path,
    *,
    expected_name: str,
) -> TopLevelSystemSkillFrontmatter:
    """Parse strict release metadata from one top-level public skill entrypoint."""

    resolved_path = path.expanduser().resolve(strict=False)
    try:
        text = resolved_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemSkillFrontmatterError(
            code="missing-file",
            path=resolved_path,
            message=f"Cannot read top-level skill entrypoint `{resolved_path}`: {exc}",
        ) from exc
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise SystemSkillFrontmatterError(
            code="malformed-delimiters",
            path=resolved_path,
            message=f"Top-level skill `{resolved_path}` must begin with `---` frontmatter.",
        )
    try:
        closing_index = lines.index("---", 1)
    except ValueError as exc:
        raise SystemSkillFrontmatterError(
            code="malformed-delimiters",
            path=resolved_path,
            message=f"Top-level skill `{resolved_path}` has no closing `---` delimiter.",
        ) from exc
    raw_frontmatter = "\n".join(lines[1:closing_index])
    try:
        payload = yaml.load(raw_frontmatter, Loader=_UniqueKeySafeLoader)
    except ConstructorError as exc:
        code: FrontmatterErrorCode = (
            "duplicate-key" if "duplicate key" in str(exc) else "malformed-yaml"
        )
        raise SystemSkillFrontmatterError(
            code=code,
            path=resolved_path,
            message=f"Invalid YAML frontmatter in `{resolved_path}`: {exc}",
        ) from exc
    except yaml.YAMLError as exc:
        raise SystemSkillFrontmatterError(
            code="malformed-yaml",
            path=resolved_path,
            message=f"Invalid YAML frontmatter in `{resolved_path}`: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise SystemSkillFrontmatterError(
            code="malformed-yaml",
            path=resolved_path,
            message=f"Frontmatter in `{resolved_path}` must be a YAML mapping.",
        )
    name = payload.get("name")
    if name is None:
        raise SystemSkillFrontmatterError(
            code="missing-name",
            path=resolved_path,
            message=f"Frontmatter in `{resolved_path}` is missing `name`.",
        )
    if not isinstance(name, str) or not name:
        raise SystemSkillFrontmatterError(
            code="invalid-name",
            path=resolved_path,
            message=f"Frontmatter `name` in `{resolved_path}` must be a non-empty string.",
        )
    if name != expected_name:
        raise SystemSkillFrontmatterError(
            code="name-mismatch",
            path=resolved_path,
            message=(
                f"Frontmatter name `{name}` in `{resolved_path}` does not match "
                f"expected skill `{expected_name}`."
            ),
        )
    if "houmao_version" not in payload:
        raise SystemSkillFrontmatterError(
            code="missing-version",
            path=resolved_path,
            message=f"Frontmatter in `{resolved_path}` is missing `houmao_version`.",
        )
    houmao_version = payload["houmao_version"]
    if not isinstance(houmao_version, str):
        raise SystemSkillFrontmatterError(
            code="non-string-version",
            path=resolved_path,
            message=f"Frontmatter `houmao_version` in `{resolved_path}` must be a string.",
        )
    try:
        Version(houmao_version)
    except InvalidVersion as exc:
        raise SystemSkillFrontmatterError(
            code="invalid-version",
            path=resolved_path,
            message=(
                f"Frontmatter `houmao_version` value `{houmao_version}` in `{resolved_path}` "
                "is not a valid release string."
            ),
        ) from exc
    return TopLevelSystemSkillFrontmatter(
        path=resolved_path,
        name=name,
        houmao_version=houmao_version,
        raw_frontmatter=raw_frontmatter,
    )


def check_system_skill_source_versions(
    *,
    project_root: Path,
    manifest: SystemSkillManifest | None = None,
) -> SystemSkillVersionSourceCheck:
    """Check exact quoted release synchronization for the six public source roots."""

    resolved_root = project_root.expanduser().resolve()
    project_version = _load_project_version(resolved_root / "pyproject.toml")
    source_entries = (
        _manifest_source_entries(manifest)
        if manifest is not None
        else _project_source_entries(resolved_root)
    )
    skill_names = tuple(name for name, _ in source_entries)
    if skill_names != EXPECTED_STANDALONE_SKILL_NAMES:
        raise RuntimeError(
            "The v4 manifest must enumerate exactly the six versioned public skill roots."
        )
    issues: list[SystemSkillVersionSourceIssue] = []
    for skill_name, path in source_entries:
        try:
            metadata = parse_top_level_system_skill_frontmatter(path, expected_name=skill_name)
        except SystemSkillFrontmatterError as exc:
            issues.append(
                SystemSkillVersionSourceIssue(
                    skill_name=skill_name,
                    path=path,
                    expected_version=project_version,
                    observed_version=None,
                    problem=f"{exc.code}: {exc}",
                )
            )
            continue
        observed = metadata.houmao_version
        exact_line = f'houmao_version: "{project_version}"'
        if observed != project_version:
            issues.append(
                SystemSkillVersionSourceIssue(
                    skill_name=skill_name,
                    path=path,
                    expected_version=project_version,
                    observed_version=observed,
                    problem="version mismatch",
                )
            )
        elif exact_line not in metadata.raw_frontmatter.splitlines():
            issues.append(
                SystemSkillVersionSourceIssue(
                    skill_name=skill_name,
                    path=path,
                    expected_version=project_version,
                    observed_version=observed,
                    problem=f"metadata must contain exact quoted line `{exact_line}`",
                )
            )
    return SystemSkillVersionSourceCheck(
        project_version=project_version,
        checked_skill_names=skill_names,
        issues=tuple(issues),
    )


def _manifest_source_entries(manifest: SystemSkillManifest) -> tuple[tuple[str, Path], ...]:
    """Return versioned roots from one already loaded manifest fixture."""

    return tuple(
        (
            skill_name,
            standalone_system_skill_source_path(manifest, record) / "SKILL.md",
        )
        for skill_name, record in manifest.standalone_skills.items()
    )


def _project_source_entries(project_root: Path) -> tuple[tuple[str, Path], ...]:
    """Read exact standalone roots from source TOML without validating skill content."""

    assets_root = project_root / "src/houmao/agents/assets/system_skills"
    manifest_path = assets_root / "manifest.toml"
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        raw_records = payload["standalone_skills"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(f"Cannot read standalone roots from `{manifest_path}`: {exc}") from exc
    if not isinstance(raw_records, list):
        raise RuntimeError(f"Standalone records in `{manifest_path}` must be an array of tables.")
    entries: list[tuple[str, Path]] = []
    resolved_assets_root = assets_root.resolve()
    for raw_record in raw_records:
        if not isinstance(raw_record, dict):
            raise RuntimeError(f"Standalone records in `{manifest_path}` must be TOML tables.")
        name = raw_record.get("name")
        source_path = raw_record.get("source_path")
        if not isinstance(name, str) or not isinstance(source_path, str):
            raise RuntimeError(
                f"Standalone records in `{manifest_path}` require string name and source_path."
            )
        entrypoint = (assets_root / source_path / "SKILL.md").resolve(strict=False)
        if not entrypoint.is_relative_to(resolved_assets_root):
            raise RuntimeError(
                f"Standalone source `{source_path}` escapes system-skill assets in "
                f"`{manifest_path}`."
            )
        entries.append((name, entrypoint))
    return tuple(entries)


def _load_project_version(path: Path) -> str:
    """Load and validate ``[project].version`` from one project file."""

    try:
        payload: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
        project = payload["project"]
        value = project["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(f"Cannot read [project].version from `{path}`: {exc}") from exc
    if not isinstance(value, str):
        raise RuntimeError(f"[project].version in `{path}` must be a string.")
    try:
        Version(value)
    except InvalidVersion as exc:
        raise RuntimeError(f"[project].version `{value}` is not a valid release string.") from exc
    return value


__all__ = (
    "FrontmatterErrorCode",
    "SystemSkillFrontmatterError",
    "SystemSkillVersionSourceCheck",
    "SystemSkillVersionSourceIssue",
    "TopLevelSystemSkillFrontmatter",
    "check_system_skill_source_versions",
    "parse_top_level_system_skill_frontmatter",
)
