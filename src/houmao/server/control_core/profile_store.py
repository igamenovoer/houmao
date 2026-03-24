"""Houmao-owned compatibility profile storage and install helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
import threading
from pathlib import Path
from urllib import error, request

import yaml

from houmao.server.config import HoumaoServerConfig

from .models import (
    CompatibilityAgentProfile,
    CompatibilityProfileIndexRecord,
    CompatibilityProfileIndexSnapshot,
)

_FRONTMATTER_DELIMITER = "---"


class CompatibilityProfileInstallError(RuntimeError):
    """Raised when compatibility profile install or load fails."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        """Initialize one explicit install failure."""

        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class PreparedCompatibilityProfile:
    """Resolved compatibility profile ready for provider launch."""

    profile: CompatibilityAgentProfile
    resolved_provider: str
    markdown_path: Path
    context_path: Path
    provider_artifact_paths: dict[str, Path]


class CompatibilityProfileStore:
    """Server-owned compatibility profile store plus install behavior."""

    def __init__(self, *, config: HoumaoServerConfig) -> None:
        """Initialize the profile store."""

        self.m_config = config
        self.m_lock = threading.RLock()

    def ensure_directories(self) -> None:
        """Create the compatibility-profile directories."""

        for path in (
            self.m_config.compatibility_home_dir,
            self.m_config.compatibility_cao_home_dir,
            self.m_config.compatibility_agent_store_dir,
            self.m_config.compatibility_agent_context_dir,
            self.m_config.compatibility_q_agents_dir,
            self.m_config.compatibility_kiro_agents_dir,
            self.m_config.compatibility_state_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def install_profile(
        self,
        *,
        agent_source: str,
        provider: str,
        working_directory: Path | None = None,
    ) -> CompatibilityProfileIndexRecord:
        """Install one compatibility profile into the server-owned store."""

        self.ensure_directories()
        resolved_source = agent_source.strip()
        if not resolved_source:
            raise CompatibilityProfileInstallError(
                status_code=422,
                detail="Compatibility install requires a non-empty `agent_source`.",
            )
        resolved_provider = provider.strip()
        if not resolved_provider:
            raise CompatibilityProfileInstallError(
                status_code=422,
                detail="Compatibility install requires a non-empty `provider`.",
            )

        markdown_text = self._load_source_markdown(
            agent_source=resolved_source,
            working_directory=working_directory,
        )
        profile = _parse_profile_markdown(markdown_text=markdown_text)
        prepared = self._store_profile_markdown(
            profile=profile,
            requested_provider=resolved_provider,
            markdown_text=markdown_text,
        )
        return self._write_profile_index_record(
            prepared=prepared, requested_provider=resolved_provider
        )

    def load_profile(
        self,
        *,
        profile_name: str,
        requested_provider: str,
    ) -> PreparedCompatibilityProfile:
        """Load and materialize one compatibility profile for launch."""

        self.ensure_directories()
        resolved_name = profile_name.strip()
        if not resolved_name:
            raise CompatibilityProfileInstallError(
                status_code=404,
                detail="Compatibility profile name must not be empty.",
            )

        markdown_path = self.m_config.compatibility_agent_store_dir / f"{resolved_name}.md"
        if not markdown_path.is_file():
            raise CompatibilityProfileInstallError(
                status_code=404,
                detail=f"Compatibility profile `{resolved_name}` was not found in the Houmao-managed store.",
            )

        markdown_text = markdown_path.read_text(encoding="utf-8")
        profile = _parse_profile_markdown(markdown_text=markdown_text)
        context_path = self._write_context_file(profile=profile, markdown_text=markdown_text)
        resolved_provider = self._resolve_launch_provider(
            profile=profile,
            requested_provider=requested_provider,
        )
        provider_artifact_paths = self._materialize_provider_artifacts(
            profile_name=resolved_name,
            profile=profile,
            context_path=context_path,
            resolved_provider=resolved_provider,
        )
        self._write_profile_index_record(
            prepared=PreparedCompatibilityProfile(
                profile=profile,
                resolved_provider=resolved_provider,
                markdown_path=markdown_path,
                context_path=context_path,
                provider_artifact_paths=provider_artifact_paths,
            ),
            requested_provider=requested_provider,
        )
        return PreparedCompatibilityProfile(
            profile=profile,
            resolved_provider=resolved_provider,
            markdown_path=markdown_path,
            context_path=context_path,
            provider_artifact_paths=provider_artifact_paths,
        )

    def _load_source_markdown(
        self,
        *,
        agent_source: str,
        working_directory: Path | None,
    ) -> str:
        """Resolve one install source to markdown text."""

        if agent_source.startswith("http://") or agent_source.startswith("https://"):
            return self._download_markdown(agent_source=agent_source)

        resolved_working_directory = (
            working_directory.resolve() if working_directory is not None else None
        )
        explicit_path = Path(agent_source).expanduser()
        if not explicit_path.is_absolute() and resolved_working_directory is not None:
            explicit_path = (resolved_working_directory / explicit_path).resolve()
        elif explicit_path.is_absolute():
            explicit_path = explicit_path.resolve()

        if explicit_path.is_file():
            if explicit_path.suffix != ".md":
                raise CompatibilityProfileInstallError(
                    status_code=422,
                    detail=f"Compatibility install only accepts Markdown profile sources, got `{explicit_path}`.",
                )
            return explicit_path.read_text(encoding="utf-8")

        built_in_match = self._find_named_profile_source(
            agent_name=agent_source, working_directory=resolved_working_directory
        )
        if built_in_match is None:
            raise CompatibilityProfileInstallError(
                status_code=404,
                detail=f"Compatibility profile source `{agent_source}` could not be resolved.",
            )
        return built_in_match.read_text(encoding="utf-8")

    def _find_named_profile_source(
        self,
        *,
        agent_name: str,
        working_directory: Path | None,
    ) -> Path | None:
        """Resolve one named install source from local or built-in stores."""

        candidates: list[Path] = []
        direct_store = self.m_config.compatibility_agent_store_dir / f"{agent_name}.md"
        if direct_store.is_file():
            candidates.append(direct_store)

        built_in_store = self._built_in_profile_store_dir()
        if built_in_store is not None:
            built_in_candidate = built_in_store / f"{agent_name}.md"
            if built_in_candidate.is_file():
                candidates.append(built_in_candidate)

        if working_directory is not None:
            recursive_matches = list(working_directory.rglob(f"{agent_name}.md"))
            candidates.extend(path.resolve() for path in recursive_matches if path.is_file())
        if not candidates:
            repo_root = Path(__file__).resolve().parents[4]
            recursive_matches = list(repo_root.rglob(f"{agent_name}.md"))
            candidates.extend(path.resolve() for path in recursive_matches if path.is_file())

        deduped: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            deduped.append(resolved)
        if not deduped:
            return None
        if len(deduped) > 1:
            rendered = ", ".join(str(path) for path in deduped[:5])
            raise CompatibilityProfileInstallError(
                status_code=409,
                detail=(
                    f"Compatibility profile source `{agent_name}` is ambiguous. "
                    f"Matching Markdown files: {rendered}"
                ),
            )
        return deduped[0]

    def _download_markdown(self, *, agent_source: str) -> str:
        """Download one remote Markdown install source."""

        try:
            with request.urlopen(agent_source, timeout=15.0) as response:
                payload = response.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            raise CompatibilityProfileInstallError(
                status_code=502,
                detail=f"Failed to download compatibility profile `{agent_source}`: HTTP {exc.code}.",
            ) from exc
        except (error.URLError, TimeoutError, OSError) as exc:
            raise CompatibilityProfileInstallError(
                status_code=502,
                detail=f"Failed to download compatibility profile `{agent_source}`: {exc}.",
            ) from exc

        if not agent_source.endswith(".md"):
            raise CompatibilityProfileInstallError(
                status_code=422,
                detail=f"Compatibility profile URL must point to a `.md` file, got `{agent_source}`.",
            )
        return payload

    def _store_profile_markdown(
        self,
        *,
        profile: CompatibilityAgentProfile,
        requested_provider: str,
        markdown_text: str,
    ) -> PreparedCompatibilityProfile:
        """Store one parsed profile markdown into the managed compatibility store."""

        markdown_path = self.m_config.compatibility_agent_store_dir / f"{profile.name}.md"
        markdown_path.write_text(
            markdown_text if markdown_text.endswith("\n") else f"{markdown_text}\n",
            encoding="utf-8",
        )
        context_path = self._write_context_file(profile=profile, markdown_text=markdown_text)
        resolved_provider = self._resolve_launch_provider(
            profile=profile,
            requested_provider=requested_provider,
        )
        provider_artifact_paths = self._materialize_provider_artifacts(
            profile_name=profile.name,
            profile=profile,
            context_path=context_path,
            resolved_provider=resolved_provider,
        )
        return PreparedCompatibilityProfile(
            profile=profile,
            resolved_provider=resolved_provider,
            markdown_path=markdown_path,
            context_path=context_path,
            provider_artifact_paths=provider_artifact_paths,
        )

    def _write_context_file(
        self,
        *,
        profile: CompatibilityAgentProfile,
        markdown_text: str,
    ) -> Path:
        """Write the CAO-compatible agent-context copy for one profile."""

        context_path = self.m_config.compatibility_agent_context_dir / f"{profile.name}.md"
        context_path.write_text(
            markdown_text if markdown_text.endswith("\n") else f"{markdown_text}\n",
            encoding="utf-8",
        )
        return context_path

    def _resolve_launch_provider(
        self,
        *,
        profile: CompatibilityAgentProfile,
        requested_provider: str,
    ) -> str:
        """Resolve the launch provider using the profile override when valid."""

        if profile.provider is not None and profile.provider.strip():
            return profile.provider.strip()
        return requested_provider

    def _materialize_provider_artifacts(
        self,
        *,
        profile_name: str,
        profile: CompatibilityAgentProfile,
        context_path: Path,
        resolved_provider: str,
    ) -> dict[str, Path]:
        """Materialize provider-specific compatibility artifacts when required."""

        artifact_paths: dict[str, Path] = {}
        allowed_tools = (
            list(profile.allowedTools)
            if profile.allowedTools is not None
            else [
                "@builtin",
                "fs_*",
                "execute_bash",
            ]
        )
        if profile.mcpServers:
            for server_name in profile.mcpServers:
                allowed_tools.append(f"@{server_name}")

        if resolved_provider == "q_cli":
            payload = {
                "name": profile_name,
                "description": profile.description,
                "tools": profile.tools if profile.tools is not None else ["*"],
                "allowedTools": allowed_tools,
                "useLegacyMcpJson": bool(profile.useLegacyMcpJson)
                if profile.useLegacyMcpJson is not None
                else False,
                "resources": [f"file://{context_path.absolute()}"],
                "prompt": profile.prompt,
                "mcpServers": profile.mcpServers,
                "toolAliases": profile.toolAliases,
                "toolsSettings": profile.toolsSettings,
                "hooks": profile.hooks,
                "model": profile.model,
            }
            artifact_path = (
                self.m_config.compatibility_q_agents_dir / f"{profile_name.replace('/', '__')}.json"
            )
            artifact_path.write_text(
                json.dumps(_drop_none(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            artifact_paths["q_cli"] = artifact_path

        if resolved_provider == "kiro_cli":
            payload = {
                "name": profile_name,
                "description": profile.description,
                "tools": profile.tools if profile.tools is not None else ["*"],
                "allowedTools": allowed_tools,
                "useLegacyMcpJson": bool(profile.useLegacyMcpJson)
                if profile.useLegacyMcpJson is not None
                else False,
                "resources": [f"file://{context_path.absolute()}"],
                "prompt": profile.prompt,
                "mcpServers": profile.mcpServers,
                "toolAliases": profile.toolAliases,
                "toolsSettings": profile.toolsSettings,
                "hooks": profile.hooks,
                "model": profile.model,
            }
            artifact_path = (
                self.m_config.compatibility_kiro_agents_dir
                / f"{profile_name.replace('/', '__')}.json"
            )
            artifact_path.write_text(
                json.dumps(_drop_none(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            artifact_paths["kiro_cli"] = artifact_path

        return artifact_paths

    def _write_profile_index_record(
        self,
        *,
        prepared: PreparedCompatibilityProfile,
        requested_provider: str,
    ) -> CompatibilityProfileIndexRecord:
        """Upsert one profile index entry and persist the snapshot."""

        record = CompatibilityProfileIndexRecord(
            profile_name=prepared.profile.name,
            description=prepared.profile.description,
            requested_provider=requested_provider,
            resolved_provider=prepared.resolved_provider,
            markdown_path=str(prepared.markdown_path),
            context_path=str(prepared.context_path),
            provider_artifact_paths={
                key: str(path) for key, path in prepared.provider_artifact_paths.items()
            },
        )
        with self.m_lock:
            snapshot = self._read_profile_index_snapshot()
            records = [
                item for item in snapshot.records if item.profile_name != record.profile_name
            ]
            records.append(record)
            persisted = CompatibilityProfileIndexSnapshot(records=records)
            self.m_config.compatibility_profile_index_path.write_text(
                json.dumps(persisted.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return record

    def _read_profile_index_snapshot(self) -> CompatibilityProfileIndexSnapshot:
        """Read the current profile index snapshot from disk."""

        if not self.m_config.compatibility_profile_index_path.is_file():
            return CompatibilityProfileIndexSnapshot()
        payload = json.loads(
            self.m_config.compatibility_profile_index_path.read_text(encoding="utf-8")
        )
        return CompatibilityProfileIndexSnapshot.model_validate(payload)

    @staticmethod
    def _built_in_profile_store_dir() -> Path | None:
        """Return the pinned upstream built-in profile store when present."""

        repo_root = Path(__file__).resolve().parents[4]
        candidate = (
            repo_root
            / "extern"
            / "tracked"
            / "cli-agent-orchestrator"
            / "src"
            / "cli_agent_orchestrator"
            / "agent_store"
        ).resolve()
        return candidate if candidate.is_dir() else None


def _parse_profile_markdown(*, markdown_text: str) -> CompatibilityAgentProfile:
    """Parse one Markdown profile with required YAML frontmatter."""

    lines = markdown_text.splitlines()
    if len(lines) < 3 or lines[0].strip() != _FRONTMATTER_DELIMITER:
        raise CompatibilityProfileInstallError(
            status_code=422,
            detail="Compatibility profiles must begin with YAML frontmatter delimited by `---`.",
        )

    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == _FRONTMATTER_DELIMITER:
            closing_index = index
            break
    if closing_index is None:
        raise CompatibilityProfileInstallError(
            status_code=422,
            detail="Compatibility profile frontmatter is missing a closing `---` delimiter.",
        )

    frontmatter_payload = yaml.safe_load("\n".join(lines[1:closing_index])) or {}
    if not isinstance(frontmatter_payload, dict):
        raise CompatibilityProfileInstallError(
            status_code=422,
            detail="Compatibility profile frontmatter must decode to a mapping.",
        )
    frontmatter_payload["system_prompt"] = "\n".join(lines[closing_index + 1 :]).strip()

    try:
        return CompatibilityAgentProfile.model_validate(frontmatter_payload)
    except Exception as exc:
        raise CompatibilityProfileInstallError(
            status_code=422,
            detail=f"Compatibility profile validation failed: {exc}",
        ) from exc


def _drop_none(payload: dict[str, object]) -> dict[str, object]:
    """Return a shallow copy without `None` values."""

    return {key: value for key, value in payload.items() if value is not None}
