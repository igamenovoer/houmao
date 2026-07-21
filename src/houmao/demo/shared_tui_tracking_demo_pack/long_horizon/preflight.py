"""Unattended provider preparation and native-TUI preflight probes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from houmao.agents.brain_builder import BuildRequest, build_brain_home, load_brain_recipe
from houmao.agents.launch_policy.engine import detect_tool_version, resolve_strategy
from houmao.agents.launch_policy.models import LaunchPolicyRequest
from houmao.agents.realm_controller.backends.tmux_runtime import (
    parse_tmux_control_input,
    send_tmux_control_input,
)
from houmao.agents.system_skills import SystemSkillSelectionPolicy
from houmao.demo.shared_tui_tracking_demo_pack.agent_assets import (
    materialize_generated_agent_tree,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import ProviderName
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.paths import (
    LongHorizonRunPaths,
    require_owned_descendant,
    save_json_atomic,
)
from houmao.demo.shared_tui_tracking_demo_pack.tooling import (
    build_tool_session_name,
    capture_visible_pane_text,
    find_supported_process_pid,
    kill_tmux_session_if_exists,
    launch_tmux_session,
    process_is_alive,
    query_pane_state,
    resolve_active_pane_id,
)


_PRESET_NAME_BY_PROVIDER: dict[ProviderName, str] = {
    "claude": "long-horizon-claude-unattended.yaml",
    "codex": "long-horizon-codex-unattended.yaml",
    "kimi": "long-horizon-kimi-unattended.yaml",
}
_READY_MARKERS_BY_PROVIDER: dict[ProviderName, tuple[str, ...]] = {
    "claude": ('Try "', "Claude Code", "? for shortcuts", "bypass permissions"),
    "codex": ("Find and fix a bug", "? for shortcuts", "Implement {feature}"),
    "kimi": ("type a message or use /help",),
}
_CONFIRMATION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"do you trust",
        r"allow (?:this|the|command)",
        r"approval required",
        r"permission required",
        r"press enter to (?:login|authenticate|continue)",
        r"open (?:a|the) browser",
        r"select (?:a )?session",
        r"update available.*continue",
        r"would you like (?:me|to)",
        r"do you want to use this api key",
        r"run /login",
        r"model:\s+not set",
    )
)
_PROXY_URL = "http://127.0.0.1:7990"
_PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


@dataclass(frozen=True)
class PreparedProviderHome:
    """Sanitized launch metadata plus runtime-only provider paths."""

    provider: ProviderName
    home_path: Path
    manifest_path: Path
    launch_helper_path: Path
    observed_version: str
    strategy_id: str
    launch_command_sha256: str
    environment: dict[str, str]


@dataclass(frozen=True)
class ProviderProbeResult:
    """Evidence and verdict from one disposable native-TUI probe."""

    schema_version: int
    provider: ProviderName
    status: str
    code: str
    session_name: str
    pane_id: str | None
    ready_marker: str | None
    steering_supported: bool | None
    model_selector_supported: bool | None
    empty_editor_exit_supported: bool | None
    confirmation_violation: str | None
    evidence_path: str

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible probe payload."""

        return asdict(self)


def prepare_provider_home(
    *,
    repo_root: Path,
    paths: LongHorizonRunPaths,
    provider: ProviderName,
    cell_id: str,
    attempt_number: int,
) -> PreparedProviderHome:
    """Build one unprompted unattended provider home beneath the run root."""

    attempt_root = paths.attempt_root(cell_id=cell_id, attempt_number=attempt_number)
    definition_workdir = attempt_root / "runtime" / "definition-workdir"
    definition_workdir.mkdir(parents=True, exist_ok=True)
    generated_agent_dir = materialize_generated_agent_tree(
        repo_root=repo_root,
        workdir=definition_workdir,
        tool=provider,
        allow_missing_auth=True,
    )
    _project_current_host_auth(generated_agent_dir=generated_agent_dir, provider=provider)
    preset_path = (generated_agent_dir / "presets" / _PRESET_NAME_BY_PROVIDER[provider]).resolve()
    recipe = load_brain_recipe(preset_path)
    if recipe.tool != provider or recipe.skills:
        raise RuntimeError(f"Qualification preset is not bare for {provider}: {preset_path}")
    environment = codex_proxy_environment() if provider == "codex" else {}
    if provider == "codex":
        require_codex_proxy()
    runtime_root = paths.provider_home_root(
        cell_id=cell_id,
        attempt_number=attempt_number,
    )
    require_owned_descendant(paths=paths, target=runtime_root)
    build_result = build_brain_home(
        BuildRequest(
            agent_def_dir=generated_agent_dir,
            tool=recipe.tool,
            skills=list(recipe.skills),
            config_profile=recipe.config_profile,
            credential_profile=recipe.credential_profile,
            recipe_path=preset_path,
            recipe_launch_overrides=getattr(recipe, "launch_overrides", None),
            runtime_root=runtime_root,
            mailbox=None,
            agent_name=None,
            operator_prompt_mode="unattended",
            persistent_env_records={},
            source_system_skill_policy=SystemSkillSelectionPolicy(mode="none"),
            launch_profile_system_skill_policy=SystemSkillSelectionPolicy(mode="none"),
        )
    )
    _assert_bare_manifest(build_result.manifest)
    launch_executable = str(build_result.manifest["runtime"]["launch_executable"])
    version = detect_tool_version(executable=launch_executable)
    strategy, _selection_source = resolve_strategy(
        request=LaunchPolicyRequest(
            tool=provider,
            backend="raw_launch",
            executable=launch_executable,
            base_args=(),
            requested_operator_prompt_mode="unattended",
            working_directory=paths.project_root(
                cell_id=cell_id,
                attempt_number=attempt_number,
            ),
            home_path=build_result.home_path,
            env={**os.environ, **environment},
        ),
        detected_version=version,
    )
    observed_version = version.raw
    launch_digest = hashlib.sha256(build_result.launch_helper_path.read_bytes()).hexdigest()
    prepared = PreparedProviderHome(
        provider=provider,
        home_path=build_result.home_path,
        manifest_path=build_result.manifest_path,
        launch_helper_path=build_result.launch_helper_path,
        observed_version=observed_version,
        strategy_id=strategy.strategy_id,
        launch_command_sha256=launch_digest,
        environment=environment,
    )
    save_json_atomic(
        attempt_root / "runtime" / "provider-launch-manifest.json",
        sanitized_provider_manifest(prepared=prepared),
    )
    return prepared


def require_codex_proxy(*, host: str = "127.0.0.1", port: int = 7990) -> None:
    """Fail closed unless the required Codex proxy accepts a TCP connection."""

    try:
        with socket.create_connection((host, port), timeout=2.0):
            pass
    except OSError as exc:
        raise RuntimeError(f"Required Codex proxy is unreachable at {host}:{port}") from exc


def codex_proxy_environment() -> dict[str, str]:
    """Return the required upper- and lower-case Codex proxy projection."""

    environment = {name: _PROXY_URL for name in _PROXY_VARIABLES}
    no_proxy = "127.0.0.1,localhost,::1"
    environment["NO_PROXY"] = no_proxy
    environment["no_proxy"] = no_proxy
    return environment


def sanitized_provider_manifest(*, prepared: PreparedProviderHome) -> dict[str, Any]:
    """Return allowlisted launch metadata without credential values."""

    proxy_values = {
        name: value
        for name, value in prepared.environment.items()
        if name in _PROXY_VARIABLES and value == _PROXY_URL
    }
    return {
        "schema_version": 1,
        "provider": prepared.provider,
        "observed_version": prepared.observed_version,
        "strategy_id": prepared.strategy_id,
        "operator_prompt_mode": "unattended",
        "home_path": str(prepared.home_path),
        "manifest_path": str(prepared.manifest_path),
        "launch_helper_path": str(prepared.launch_helper_path),
        "launch_command_sha256": prepared.launch_command_sha256,
        "environment_names": sorted(prepared.environment),
        "codex_proxy_projection": proxy_values,
    }


def find_confirmation_violation(
    *,
    visible_text: str,
    allowlist_patterns: tuple[str, ...] = (),
) -> str | None:
    """Return the first unallowlisted native intervention surface."""

    plain_text = _ANSI_RE.sub("", visible_text)
    for allowlist_pattern in allowlist_patterns:
        if re.search(allowlist_pattern, plain_text, re.IGNORECASE):
            return None
    for pattern in _CONFIRMATION_PATTERNS:
        match = pattern.search(plain_text)
        if match is not None:
            return match.group(0)
    return None


def detect_ready_marker(*, provider: ProviderName, visible_text: str) -> str | None:
    """Return one provider-native prompt marker without reducing tracker state."""

    plain_text = _ANSI_RE.sub("", visible_text)
    if provider == "codex" and re.search(r"›\x1b\[0m \x1b\[2m", visible_text):
        return "native-input-prompt"
    if provider == "claude" and re.search(r"(?m)^❯\s", plain_text):
        return "native-input-prompt"
    if provider == "kimi" and re.search(r"(?m)^\s*│ >\s", plain_text):
        return "native-input-prompt"
    lowered = plain_text.lower()
    for marker in _READY_MARKERS_BY_PROVIDER[provider]:
        if marker.lower() in lowered:
            return marker
    return None


def run_disposable_probe(
    *,
    paths: LongHorizonRunPaths,
    prepared: PreparedProviderHome,
    project_root: Path,
    require_model_selector: bool = False,
    require_empty_editor_exit: bool = False,
    require_steering: bool = False,
    timeout_seconds: float = 45.0,
) -> ProviderProbeResult:
    """Launch an owned TUI and probe exact native surfaces without the tracker."""

    session_name = build_tool_session_name(
        tool=prepared.provider,
        run_id=f"probe-{prepared.home_path.parent.name}",
    )
    evidence_dir = paths.preflight_dir / "providers" / prepared.provider
    evidence_dir.mkdir(parents=True, exist_ok=True)
    frames_path = evidence_dir / "probe-frames.ndjson"
    pane_id: str | None = None
    marker: str | None = None
    steering_supported: bool | None = None
    model_supported: bool | None = None
    exit_supported: bool | None = None
    violation: str | None = None
    try:
        launch_tmux_session(
            session_name=session_name,
            workdir=project_root,
            launch_script=prepared.launch_helper_path,
        )
        pane_id = resolve_active_pane_id(session_name=session_name)
        marker, violation = _wait_for_native_ready(
            provider=prepared.provider,
            pane_id=pane_id,
            frames_path=frames_path,
            timeout_seconds=timeout_seconds,
        )
        if violation is None and require_steering:
            steering_supported = _probe_steering(pane_id=pane_id, frames_path=frames_path)
        if violation is None and require_model_selector:
            before = capture_visible_pane_text(pane_id=pane_id)
            _send_sequence(pane_id=pane_id, sequence="/model<[Enter]>")
            time.sleep(1.0)
            after = capture_visible_pane_text(pane_id=pane_id)
            model_supported = after != before and "model" in after.lower()
            _append_frame(frames_path=frames_path, event="model_selector", visible_text=after)
            _send_sequence(pane_id=pane_id, sequence="<[Escape]>")
        if violation is None and require_empty_editor_exit:
            _send_sequence(pane_id=pane_id, sequence="<[C-d]>")
            exit_supported = _wait_for_provider_exit(
                provider=prepared.provider,
                session_name=session_name,
                pane_id=pane_id,
                timeout_seconds=5.0,
            )
    finally:
        kill_tmux_session_if_exists(session_name=session_name)
    status = "pass"
    code = "pass"
    if violation is not None:
        status = "fail"
        code = "unattended_confirmation_violation"
    elif marker is None:
        status = "fail"
        code = "provider_preflight_failed"
    elif require_steering and not steering_supported:
        status = "incomplete"
        code = "unsupported_steering_surface"
    elif require_model_selector and not model_supported:
        status = "incomplete"
        code = "unsupported_navigation_surface"
    elif require_empty_editor_exit and not exit_supported:
        status = "incomplete"
        code = "unsupported_exit_surface"
    result = ProviderProbeResult(
        schema_version=1,
        provider=prepared.provider,
        status=status,
        code=code,
        session_name=session_name,
        pane_id=pane_id,
        ready_marker=marker,
        steering_supported=steering_supported,
        model_selector_supported=model_supported,
        empty_editor_exit_supported=exit_supported,
        confirmation_violation=violation,
        evidence_path=str(frames_path),
    )
    save_json_atomic(evidence_dir / "probe-result.json", result.to_payload())
    return result


def remove_sensitive_provider_home(
    *, paths: LongHorizonRunPaths, prepared: PreparedProviderHome
) -> None:
    """Remove credential-bearing provider state after its owned process stops."""

    require_owned_descendant(paths=paths, target=prepared.home_path)
    runtime_root = prepared.home_path
    while (
        runtime_root.parent != paths.provider_homes_dir and runtime_root != paths.provider_homes_dir
    ):
        runtime_root = runtime_root.parent
    if runtime_root == paths.provider_homes_dir:
        raise ValueError("Provider home does not identify a cell-owned runtime root")
    shutil.rmtree(runtime_root)


def _project_current_host_auth(*, generated_agent_dir: Path, provider: ProviderName) -> None:
    """Project current host CLI authentication into the disposable run definition."""

    auth_root = generated_agent_dir / "tools" / provider / "auth" / "default"
    if auth_root.is_symlink() or auth_root.is_file():
        auth_root.unlink()
    elif auth_root.is_dir():
        shutil.rmtree(auth_root)
    auth_root.mkdir(parents=True)
    (auth_root / "env").mkdir()
    (auth_root / "env" / "vars.env").write_text("", encoding="utf-8")
    home = Path.home()
    if provider == "claude":
        source = home / ".config" / "claude-kimi" / "env"
        if not source.is_file():
            raise RuntimeError(f"Current claude-kimi authentication is missing: {source}")
        source_text = source.read_text(encoding="utf-8")
        if "ANTHROPIC_BASE_URL=" not in source_text:
            source_text += "\nANTHROPIC_BASE_URL=https://api.kimi.com/coding/\n"
        (auth_root / "env" / "vars.env").write_text(source_text, encoding="utf-8")
        return
    if provider == "codex":
        source = home / ".codex" / "auth.json"
        if not source.is_file():
            raise RuntimeError(f"Current Codex host authentication is missing: {source}")
        files_dir = auth_root / "files"
        files_dir.mkdir()
        (files_dir / "auth.json").symlink_to(source)
        proxy_environment = codex_proxy_environment()
        (auth_root / "env" / "vars.env").write_text(
            "".join(f"{name}={value}\n" for name, value in proxy_environment.items()),
            encoding="utf-8",
        )
        return
    source_config = home / ".kimi-code" / "config.toml"
    source_credentials = home / ".kimi-code" / "credentials"
    if not source_config.is_file() or not source_credentials.is_dir():
        raise RuntimeError("Current Kimi host authentication is missing under ~/.kimi-code")
    files_dir = auth_root / "files"
    files_dir.mkdir()
    (files_dir / "config.toml").symlink_to(source_config)
    (files_dir / "credentials").symlink_to(source_credentials, target_is_directory=True)


def _assert_bare_manifest(manifest: dict[str, Any]) -> None:
    """Reject provider-visible Houmao prompts and all projected skills."""

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        raise RuntimeError("Built provider manifest has no inputs object")
    if inputs.get("skills") != []:
        raise RuntimeError("Qualification provider home contains requested skills")
    forbidden = {"role_prompt_text", "managed_prompt_header", "houmao_system_prompt_layout"}
    present = forbidden.intersection(inputs)
    if present:
        raise RuntimeError(f"Qualification provider home contains prompt fields: {present}")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise RuntimeError("Built provider manifest has no runtime object")
    provenance = (
        runtime.get("launch_contract", {})
        .get("construction_provenance", {})
        .get("system_skills", {})
    )
    if not isinstance(provenance, dict) or provenance.get("public_skills") != []:
        raise RuntimeError("Qualification provider home contains system skills")


def _wait_for_native_ready(
    *,
    provider: ProviderName,
    pane_id: str,
    frames_path: Path,
    timeout_seconds: float,
) -> tuple[str | None, str | None]:
    """Wait for a raw provider marker while policing confirmation surfaces."""

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        visible_text = capture_visible_pane_text(pane_id=pane_id)
        _append_frame(frames_path=frames_path, event="readiness", visible_text=visible_text)
        violation = find_confirmation_violation(visible_text=visible_text)
        if violation is not None:
            return None, violation
        marker = detect_ready_marker(provider=provider, visible_text=visible_text)
        if marker is not None:
            return marker, None
        time.sleep(0.25)
    return None, None


def _wait_for_provider_exit(
    *, provider: ProviderName, session_name: str, pane_id: str, timeout_seconds: float
) -> bool:
    """Wait until the provider process below one tmux pane exits."""

    pane_state = query_pane_state(session_name=session_name, pane_id=pane_id)
    pane_pid = pane_state.get("pane_pid") if pane_state is not None else None
    if not isinstance(pane_pid, int):
        return True
    provider_pid = find_supported_process_pid(root_pid=pane_pid, tool=provider)
    if provider_pid is None:
        return True
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not process_is_alive(provider_pid):
            return True
        time.sleep(0.2)
    return False


def _probe_steering(*, pane_id: str, frames_path: Path) -> bool:
    """Probe active-turn draft steering in one disposable provider session."""

    prompt = (
        "Read every Python file directly under this project and prepare at least 60 numbered "
        "bullets. Do not edit files."
    )
    marker = "Steer probe: list files alphabetically."
    _send_sequence(pane_id=pane_id, sequence=f"{prompt}<[Enter]>")
    time.sleep(0.75)
    _send_sequence(pane_id=pane_id, sequence=marker)
    time.sleep(0.5)
    visible_text = capture_visible_pane_text(pane_id=pane_id)
    _append_frame(frames_path=frames_path, event="steering", visible_text=visible_text)
    supported = marker in visible_text
    _send_sequence(pane_id=pane_id, sequence="<[C-u]>")
    _send_sequence(pane_id=pane_id, sequence="<[Escape]>")
    return supported


def _send_sequence(*, pane_id: str, sequence: str) -> None:
    """Send one exact semantic sequence to the disposable pane."""

    send_tmux_control_input(
        target=pane_id,
        segments=parse_tmux_control_input(sequence=sequence),
    )


def _append_frame(*, frames_path: Path, event: str, visible_text: str) -> None:
    """Append one timestamped raw preflight frame."""

    frames_path.parent.mkdir(parents=True, exist_ok=True)
    with frames_path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "event": event,
                    "monotonic_seconds": time.monotonic(),
                    "visible_text": _sanitize_visible_evidence(visible_text),
                }
            )
            + "\n"
        )


def _sanitize_visible_evidence(visible_text: str) -> str:
    """Redact credential-shaped values from retained preflight screens."""

    return re.sub(r"sk-[A-Za-z0-9_-]+", "<redacted-api-key>", visible_text)
