"""Provider adapters for the Houmao-owned CAO-compatible control core."""

from __future__ import annotations

import json
import re
import shlex
import tempfile
import time
from pathlib import Path

from houmao.cao.models import CaoTerminalStatus

from .models import CompatibilityAgentProfile, CompatibilityTerminalStatus
from .tmux_controller import CompatibilityTmuxController

_ANSI_CODE_PATTERN = r"\x1b\[[0-9;]*m"
_SUPPORTED_PROVIDER_IDS = frozenset(
    {
        "claude_code",
        "codex",
        "gemini_cli",
        "kiro_cli",
        "kimi_cli",
        "q_cli",
    }
)


class CompatibilityProviderError(RuntimeError):
    """Raised when provider launch or parsing fails."""


class CompatibilityProviderAdapter:
    """Base provider adapter for tmux-backed compatibility sessions."""

    provider_id: str
    paste_enter_count: int = 2

    def build_command(
        self,
        *,
        profile: CompatibilityAgentProfile,
        profile_name: str,
        terminal_id: str,
        working_directory: Path,
    ) -> str:
        """Return the shell command used to start the provider."""

        del profile, profile_name, terminal_id, working_directory
        raise NotImplementedError

    def get_status(self, *, output_text: str, profile_name: str) -> CompatibilityTerminalStatus:
        """Return the compatibility status for one captured window."""

        del output_text, profile_name
        raise NotImplementedError

    def extract_last_message(self, *, output_text: str, profile_name: str) -> str:
        """Return the provider's last response message from captured output."""

        del profile_name
        return _fallback_last_message(output_text)

    def exit_terminal(
        self,
        *,
        tmux: CompatibilityTmuxController,
        window_id: str,
    ) -> None:
        """Deliver the provider-specific exit action."""

        tmux.send_text(window_id=window_id, text="/exit", enter_count=1)

    def wait_until_ready(
        self,
        *,
        tmux: CompatibilityTmuxController,
        window_id: str,
        profile_name: str,
        timeout_seconds: float,
        polling_interval_seconds: float,
    ) -> None:
        """Wait until the provider reaches an input-ready status."""

        started_at = time.monotonic()
        while time.monotonic() - started_at < timeout_seconds:
            status = self.get_status(
                output_text=tmux.capture_window(window_id=window_id),
                profile_name=profile_name,
            )
            if status in {"idle", "completed"}:
                return
            time.sleep(polling_interval_seconds)
        raise CompatibilityProviderError(
            f"Timed out waiting for provider `{self.provider_id}` to become ready."
        )


class CodexCompatibilityProvider(CompatibilityProviderAdapter):
    """Compatibility adapter for Codex CLI."""

    provider_id = "codex"

    def build_command(
        self,
        *,
        profile: CompatibilityAgentProfile,
        profile_name: str,
        terminal_id: str,
        working_directory: Path,
    ) -> str:
        """Return the Codex startup command."""

        del profile_name, terminal_id, working_directory
        command_parts = ["codex", "--no-alt-screen", "--disable", "shell_snapshot"]
        system_prompt = (profile.system_prompt or "").strip()
        if system_prompt:
            escaped_prompt = (
                system_prompt.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            )
            command_parts.extend(["-c", f'developer_instructions="{escaped_prompt}"'])
        if profile.mcpServers:
            for server_name, raw_server in profile.mcpServers.items():
                if not isinstance(raw_server, dict):
                    continue
                prefix = f"mcp_servers.{server_name}"
                command = raw_server.get("command")
                if isinstance(command, str) and command.strip():
                    command_parts.extend(["-c", f'{prefix}.command="{command}"'])
                args = raw_server.get("args")
                if isinstance(args, list):
                    args_toml = (
                        "[" + ", ".join(f'"{arg}"' for arg in args if isinstance(arg, str)) + "]"
                    )
                    command_parts.extend(["-c", f"{prefix}.args={args_toml}"])
                env = raw_server.get("env")
                if isinstance(env, dict):
                    for key, value in env.items():
                        if isinstance(key, str) and isinstance(value, str):
                            command_parts.extend(["-c", f'{prefix}.env.{key}="{value}"'])
                env_vars = raw_server.get("env_vars")
                env_var_names = (
                    [name for name in env_vars if isinstance(name, str)]
                    if isinstance(env_vars, list)
                    else []
                )
                if "CAO_TERMINAL_ID" not in env_var_names:
                    env_var_names.append("CAO_TERMINAL_ID")
                env_vars_toml = "[" + ", ".join(f'"{name}"' for name in env_var_names) + "]"
                command_parts.extend(["-c", f"{prefix}.env_vars={env_vars_toml}"])
                if "tool_timeout_sec" not in raw_server:
                    command_parts.extend(["-c", f"{prefix}.tool_timeout_sec=600.0"])
        return shlex.join(command_parts)

    def get_status(self, *, output_text: str, profile_name: str) -> CompatibilityTerminalStatus:
        """Return Codex status from rendered output."""

        del profile_name
        if not output_text.strip():
            return "error"

        clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
        if re.search(r"Approve\b.*\b(?:y/n|yes/no|yes|no)\b", clean_output):
            return "waiting_user_answer"
        if re.search(r"•.*\(\d+s\s*•\s*esc to interrupt\)", clean_output):
            return "processing"
        if re.search(r"^\s*(?:❯|›|codex>)\s*$", clean_output, re.MULTILINE):
            response_match = re.search(
                r"^(?:(?:assistant|codex|agent)\s*:|\s*•)", clean_output, re.MULTILINE
            )
            return "completed" if response_match else "idle"
        if re.search(
            r"\b(thinking|working|running|executing|processing|analyzing)\b", clean_output
        ):
            return "processing"
        if re.search(
            r"^(?:Error:|ERROR:|Traceback \(most recent call last\):|panic:)",
            clean_output,
            re.MULTILINE,
        ):
            return "error"
        return "processing"


class ClaudeCompatibilityProvider(CompatibilityProviderAdapter):
    """Compatibility adapter for Claude Code."""

    provider_id = "claude_code"

    def build_command(
        self,
        *,
        profile: CompatibilityAgentProfile,
        profile_name: str,
        terminal_id: str,
        working_directory: Path,
    ) -> str:
        """Return the Claude Code startup command."""

        del profile_name, working_directory
        command_parts = ["claude", "--dangerously-skip-permissions"]
        system_prompt = (profile.system_prompt or "").strip()
        if system_prompt:
            escaped_prompt = system_prompt.replace("\\", "\\\\").replace("\n", "\\n")
            command_parts.extend(["--append-system-prompt", escaped_prompt])
        if profile.mcpServers:
            mcp_config: dict[str, object] = {}
            for server_name, raw_server in profile.mcpServers.items():
                if not isinstance(raw_server, dict):
                    continue
                server_payload = dict(raw_server)
                raw_env = server_payload.get("env")
                env_payload = dict(raw_env) if isinstance(raw_env, dict) else {}
                env_payload.setdefault("CAO_TERMINAL_ID", terminal_id)
                server_payload["env"] = env_payload
                mcp_config[server_name] = server_payload
            if mcp_config:
                command_parts.extend(["--mcp-config", json.dumps({"mcpServers": mcp_config})])
        return shlex.join(command_parts)

    def get_status(self, *, output_text: str, profile_name: str) -> CompatibilityTerminalStatus:
        """Return Claude Code status from rendered output."""

        del profile_name
        if not output_text.strip():
            return "error"
        clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
        if re.search(r"[✶✢✽✻✳].*…", clean_output):
            return "processing"
        if re.search(r"❯.*\d+\.", clean_output) and "Yes, I trust this folder" not in clean_output:
            return "waiting_user_answer"
        if re.search(r"⏺\s+", clean_output) and re.search(r"[>❯][\s\xa0]", clean_output):
            return "completed"
        if re.search(r"[>❯][\s\xa0]", clean_output):
            return "idle"
        return "processing"

    def extract_last_message(self, *, output_text: str, profile_name: str) -> str:
        """Return the last Claude response from captured output."""

        del profile_name
        clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
        matches = list(re.finditer(r"⏺\s+", clean_output))
        if not matches:
            return _fallback_last_message(output_text)
        remaining = clean_output[matches[-1].end() :]
        lines: list[str] = []
        for raw_line in remaining.splitlines():
            if re.match(r"[>❯]\s", raw_line) or "────────" in raw_line:
                break
            lines.append(raw_line.strip())
        extracted = "\n".join(line for line in lines if line).strip()
        return extracted or _fallback_last_message(output_text)


class _PromptNamedAgentCompatibilityProvider(CompatibilityProviderAdapter):
    """Shared adapter for Q CLI and Kiro CLI."""

    executable: str

    def build_command(
        self,
        *,
        profile: CompatibilityAgentProfile,
        profile_name: str,
        terminal_id: str,
        working_directory: Path,
    ) -> str:
        """Return the named-agent chat command."""

        del profile, terminal_id, working_directory
        return shlex.join([self.executable, "chat", "--agent", profile_name])

    def get_status(self, *, output_text: str, profile_name: str) -> CompatibilityTerminalStatus:
        """Return prompt-based named-agent status."""

        if not output_text.strip():
            return "error"
        clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
        idle_prompt_pattern = rf"\[{re.escape(profile_name)}\]\s*(?:\d+%\s*)?(?:\u03bb\s*)?!?>\s*"
        if not re.search(idle_prompt_pattern, clean_output):
            return "processing"
        if re.search(
            r"Allow this action\?.*?\[.*?y.*?/.*?n.*?/.*?t.*?\]:", clean_output, re.DOTALL
        ):
            return "waiting_user_answer"
        if re.search(r"^>\s*", clean_output, re.MULTILINE):
            prompt_matches = list(re.finditer(idle_prompt_pattern, clean_output))
            arrow_matches = list(re.finditer(r"^>\s*", clean_output, re.MULTILINE))
            if (
                prompt_matches
                and arrow_matches
                and prompt_matches[-1].start() > arrow_matches[-1].end()
            ):
                return "completed"
        return "idle"

    def extract_last_message(self, *, output_text: str, profile_name: str) -> str:
        """Return the last prompt-based named-agent response."""

        clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
        idle_prompt_pattern = rf"\[{re.escape(profile_name)}\]\s*(?:\d+%\s*)?(?:\u03bb\s*)?!?>\s*"
        arrows = list(re.finditer(r"^>\s*", clean_output, re.MULTILINE))
        prompts = list(re.finditer(idle_prompt_pattern, clean_output))
        if not arrows or not prompts:
            return _fallback_last_message(output_text)
        last_arrow = arrows[-1].end()
        for prompt in prompts:
            if prompt.start() > last_arrow:
                extracted = clean_output[last_arrow : prompt.start()].strip()
                return extracted or _fallback_last_message(output_text)
        return _fallback_last_message(output_text)


class QCompatibilityProvider(_PromptNamedAgentCompatibilityProvider):
    """Compatibility adapter for Amazon Q CLI."""

    provider_id = "q_cli"
    executable = "q"


class KiroCompatibilityProvider(_PromptNamedAgentCompatibilityProvider):
    """Compatibility adapter for Kiro CLI."""

    provider_id = "kiro_cli"
    executable = "kiro-cli"


class GeminiCompatibilityProvider(CompatibilityProviderAdapter):
    """Compatibility adapter for Gemini CLI."""

    provider_id = "gemini_cli"

    def build_command(
        self,
        *,
        profile: CompatibilityAgentProfile,
        profile_name: str,
        terminal_id: str,
        working_directory: Path,
    ) -> str:
        """Return the Gemini startup command."""

        del profile_name, terminal_id, working_directory
        command_parts = ["gemini", "--yolo", "--sandbox", "false"]
        system_prompt = (profile.system_prompt or "").strip()
        if system_prompt:
            command_parts.extend(["-i", system_prompt])
        return shlex.join(command_parts)

    def get_status(self, *, output_text: str, profile_name: str) -> CompatibilityTerminalStatus:
        """Return Gemini status from rendered output."""

        del profile_name
        if not output_text.strip():
            return "error"
        clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
        if re.search(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏].*\(esc to cancel", clean_output):
            return "processing"
        if re.search(
            r"^(?:Error:|ERROR:|Traceback \(most recent call last\):|ConnectionError:|APIError:)",
            clean_output,
            re.MULTILINE,
        ):
            return "error"
        idle_match = re.search(r"\*\s+Type your message", clean_output)
        if re.search(r"✦\s", clean_output) and idle_match:
            return "completed"
        if idle_match:
            return "idle"
        return "processing"

    def exit_terminal(
        self,
        *,
        tmux: CompatibilityTmuxController,
        window_id: str,
    ) -> None:
        """Exit Gemini using EOF."""

        tmux.send_special_key(window_id=window_id, key_name="C-d")


class KimiCompatibilityProvider(CompatibilityProviderAdapter):
    """Compatibility adapter for Kimi CLI."""

    provider_id = "kimi_cli"
    paste_enter_count = 1

    def build_command(
        self,
        *,
        profile: CompatibilityAgentProfile,
        profile_name: str,
        terminal_id: str,
        working_directory: Path,
    ) -> str:
        """Return the Kimi startup command."""

        del terminal_id, working_directory
        command_parts = ["kimi", "--yolo"]
        temp_dir = Path(tempfile.mkdtemp(prefix="houmao_kimi_"))
        system_prompt = (profile.system_prompt or "").strip()
        if system_prompt:
            prompt_file = temp_dir / "system.md"
            prompt_file.write_text(system_prompt + "\n", encoding="utf-8")
            agent_file = temp_dir / "agent.yaml"
            agent_file.write_text(
                "\n".join(
                    (
                        "version: 1",
                        "agent:",
                        "  extend: default",
                        "  system_prompt_path: ./system.md",
                        "",
                    )
                ),
                encoding="utf-8",
            )
            command_parts.extend(["--agent-file", str(agent_file)])
        if profile.mcpServers:
            command_parts.extend(["--mcp-config", json.dumps(profile.mcpServers)])
        return f"cd {shlex.quote(str(temp_dir))} && TERM=xterm-256color {shlex.join(command_parts)}"

    def get_status(self, *, output_text: str, profile_name: str) -> CompatibilityTerminalStatus:
        """Return Kimi status from rendered output."""

        del profile_name
        if not output_text.strip():
            return "error"
        clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
        idle_match = re.search(r"(?:\w+@[\w.-]+)?[✨💫]", clean_output)
        if re.search(
            r"^(?:Error:|ERROR:|Traceback \(most recent call last\):|ConnectionError:|APIError:)",
            clean_output,
            re.MULTILINE,
        ):
            return "error"
        if idle_match and re.search(r"^•\s", clean_output, re.MULTILINE):
            return "completed"
        if idle_match:
            return "idle"
        return "processing"


def supported_provider_ids() -> tuple[str, ...]:
    """Return the current v1 provider identifiers accepted by the control core."""

    return tuple(sorted(_SUPPORTED_PROVIDER_IDS))


def require_provider_adapter(provider_id: str) -> CompatibilityProviderAdapter:
    """Return the adapter bound to one supported compatibility provider id."""

    adapters: dict[str, CompatibilityProviderAdapter] = {
        "claude_code": ClaudeCompatibilityProvider(),
        "codex": CodexCompatibilityProvider(),
        "gemini_cli": GeminiCompatibilityProvider(),
        "kiro_cli": KiroCompatibilityProvider(),
        "kimi_cli": KimiCompatibilityProvider(),
        "q_cli": QCompatibilityProvider(),
    }
    try:
        return adapters[provider_id]
    except KeyError as exc:
        supported = ", ".join(sorted(adapters))
        raise CompatibilityProviderError(
            f"Unsupported compatibility provider `{provider_id}`. Expected one of: {supported}."
        ) from exc


def normalize_terminal_status(status: CompatibilityTerminalStatus) -> CaoTerminalStatus:
    """Convert one compatibility status string into the shared CAO enum."""

    return CaoTerminalStatus(status)


def _fallback_last_message(output_text: str) -> str:
    """Return a coarse best-effort last-message fallback."""

    clean_output = re.sub(_ANSI_CODE_PATTERN, "", output_text)
    lines = [line.strip() for line in clean_output.splitlines() if line.strip()]
    if not lines:
        return ""
    tail = lines[-20:]
    return "\n".join(tail).strip()
