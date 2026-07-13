"""Compile reviewed UC-02 instructions into exact terminal operations."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.catalog import (
    expand_prompt_tokens,
)
from houmao.demo.shared_tui_tracking_demo_pack.long_horizon.models import (
    PlannedCell,
    PlannedOperation,
    ProviderName,
)


GateKind = Literal["none", "ready", "active", "first_response"]
CompiledActionKind = Literal["send_sequence", "tmux_control", "repeat_operation"]


_PLACEHOLDER_BY_PROVIDER: dict[ProviderName, str] = {
    "claude": 'Try "fix typecheck errors"',
    "codex": "Find and fix a bug in @filename",
    "kimi": "type a message or use /help for commands.",
}
_WAIT_ACTIVE_BEFORE: set[tuple[str, int]] = {
    ("st-02", 2),
    ("st-02", 4),
    ("st-02", 7),
    ("st-02", 11),
    ("st-02", 15),
    ("st-04", 17),
    ("st-05", 5),
    ("st-05", 13),
}
_WAIT_FIRST_RESPONSE_BEFORE: set[tuple[str, int]] = {
    ("st-02", 7),
    ("st-04", 17),
    ("st-05", 5),
}
_WAIT_READY_AFTER_KEYS: set[tuple[str, int]] = {
    ("st-01", 4),
    ("st-01", 8),
    ("st-01", 14),
    ("st-01", 17),
    ("st-01", 19),
    ("st-02", 9),
    ("st-02", 19),
    ("st-04", 9),
    ("st-04", 20),
    ("st-05", 3),
    ("st-05", 7),
    ("st-05", 14),
    ("st-05", 18),
}
_SUBMITS_WITHOUT_READY_WAIT: set[tuple[str, int]] = {
    ("st-02", 1),
    ("st-02", 10),
    ("st-04", 16),
    ("st-05", 4),
    ("st-05", 12),
}
_KEY_NAME_MAP = {
    "Backspace": "BSpace",
    "Ctrl+C": "C-c",
    "Ctrl+D": "C-d",
    "Ctrl+U": "C-u",
    "Down": "Down",
    "Enter": "Enter",
    "Escape": "Escape",
    "Left": "Left",
    "Right": "Right",
    "Up": "Up",
}
_INLINE_CODE_PATTERN = re.compile(r"`([^`]*)`")


@dataclass(frozen=True)
class CompiledOperation:
    """One exact terminal or pane-control action ready for execution."""

    event_id: str
    provider: ProviderName
    procedure_id: str
    number: int
    source_instruction: str
    expanded_instruction: str
    action_kind: CompiledActionKind
    sequence: str | None
    tmux_commands: tuple[tuple[str, ...], ...]
    repeat_operation_number: int | None
    before_gate: GateKind
    after_gate: GateKind
    hold_after_seconds: float

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-compatible compiled-operation payload."""

        return asdict(self)


def compile_cell_operations(
    *,
    cell: PlannedCell,
    safe_prefix: str,
    pane_id: str,
    launch_command: str,
) -> tuple[CompiledOperation, ...]:
    """Compile every reviewed operation for one concrete provider cell."""

    values = {
        "SAFE": safe_prefix,
        "PLACEHOLDER_LITERAL": _PLACEHOLDER_BY_PROVIDER[cell.provider],
        "PANE": pane_id,
        "LAUNCH_COMMAND": launch_command,
    }
    return tuple(_compile_operation(operation=item, values=values) for item in cell.operations)


def _compile_operation(*, operation: PlannedOperation, values: dict[str, str]) -> CompiledOperation:
    """Compile one reviewed natural-language instruction without improvisation."""

    expanded_instruction = expand_prompt_tokens(text=operation.instruction, values=values)
    sequence: str | None = None
    commands: tuple[tuple[str, ...], ...] = ()
    repeat_number: int | None = None
    action_kind: CompiledActionKind
    if operation.kind == "submit_text":
        prompt = _extract_submit_text(expanded_instruction)
        sequence = f"{prompt}<[Enter]>"
        action_kind = "send_sequence"
    elif operation.kind == "type_text":
        sequence = _extract_type_text(expanded_instruction)
        action_kind = "send_sequence"
    elif operation.kind == "send_keys":
        sequence = _extract_key_sequence(expanded_instruction)
        action_kind = "send_sequence"
    elif operation.kind == "repeat_operation":
        match = re.search(r"operation\s+(\d+)", expanded_instruction, re.IGNORECASE)
        if match is None:
            raise ValueError(f"Repeat operation has no source number: {expanded_instruction}")
        repeat_number = int(match.group(1))
        action_kind = "repeat_operation"
    elif operation.kind == "tmux_control":
        commands = _extract_tmux_commands(expanded_instruction)
        action_kind = "tmux_control"
    elif operation.kind == "restart_provider":
        sequence = f"{values['LAUNCH_COMMAND']}<[Enter]>"
        action_kind = "send_sequence"
    else:  # pragma: no cover - catalog validation guards the closed operation kind
        raise ValueError(f"Unsupported operation kind: {operation.kind}")
    key = (operation.procedure_id, operation.number)
    before_gate: GateKind = "none"
    if key in _WAIT_FIRST_RESPONSE_BEFORE:
        before_gate = "first_response"
    elif key in _WAIT_ACTIVE_BEFORE:
        before_gate = "active"
    after_gate: GateKind = "none"
    if operation.kind == "submit_text" and key not in _SUBMITS_WITHOUT_READY_WAIT:
        after_gate = "ready"
    if key in _WAIT_READY_AFTER_KEYS or operation.kind == "restart_provider":
        after_gate = "ready"
    hold_after_seconds = 4.0 if key == ("st-04", 13) else 0.0
    if key == ("st-05", 21):
        hold_after_seconds = 1.1
    return CompiledOperation(
        event_id=operation.event_id,
        provider=operation.provider,
        procedure_id=operation.procedure_id,
        number=operation.number,
        source_instruction=operation.instruction,
        expanded_instruction=expanded_instruction,
        action_kind=action_kind,
        sequence=sequence,
        tmux_commands=commands,
        repeat_operation_number=repeat_number,
        before_gate=before_gate,
        after_gate=after_gate,
        hold_after_seconds=hold_after_seconds,
    )


def _extract_submit_text(instruction: str) -> str:
    """Extract the exact prompt from one reviewed submit instruction."""

    if instruction.startswith("Submit:"):
        inline = _inline_code(instruction)
        if len(inline) != 1:
            raise ValueError(f"Submitted prompt must contain one code span: {instruction}")
        return inline[0]
    stripped = instruction.strip()
    if stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1]
    raise ValueError(f"Unable to compile submitted prompt: {instruction}")


def _extract_type_text(instruction: str) -> str:
    """Extract exact non-submitted text from a reviewed editor action."""

    inline = _inline_code(instruction)
    if not inline:
        raise ValueError(f"Typed text instruction has no code span: {instruction}")
    if instruction.startswith("Append the literal nine characters"):
        return inline[-1]
    if "type without submitting:" in instruction.lower():
        return inline[-1]
    if instruction.startswith("Type the literal") or instruction.startswith("Type `"):
        return inline[0]
    if (
        instruction.lower().startswith("while ")
        and "type without submitting:" in instruction.lower()
    ):
        return inline[-1]
    raise ValueError(f"Unable to compile typed text: {instruction}")


def _extract_key_sequence(instruction: str) -> str:
    """Translate one exact reviewed key action into control-input syntax."""

    inline = _inline_code(instruction)
    if instruction.startswith("Send the key sequence"):
        if inline != ["/model Enter"]:
            raise ValueError(f"Unknown navigation key sequence: {instruction}")
        return "/model<[Enter]>"
    if instruction.startswith("Send `"):
        names = inline[0].split()
        return "".join(_key_token(name) for name in names)
    if "press `" in instruction.lower() or instruction.startswith("Press `"):
        if not inline:
            raise ValueError(f"Pressed key instruction has no code span: {instruction}")
        name = inline[-1]
        repeat = 9 if "exactly nine times" in instruction else 1
        return _key_token(name) * repeat
    raise ValueError(f"Unable to compile key sequence: {instruction}")


def _key_token(name: str) -> str:
    """Return one supported control-input token or literal space."""

    if name == "Space":
        return " "
    mapped = _KEY_NAME_MAP.get(name)
    if mapped is None:
        raise ValueError(f"Unsupported reviewed key name: {name}")
    return f"<[{mapped}]>"


def _extract_tmux_commands(instruction: str) -> tuple[tuple[str, ...], ...]:
    """Compile one of UC-02's three reviewed tmux control forms."""

    inline = _inline_code(instruction)
    if "resize-window" in instruction:
        match = re.search(r"tmux resize-window -t (\S+) -x (\d+) -y (\d+)", inline[0])
        if match is None:
            raise ValueError(f"Unable to compile resize control: {instruction}")
        return (
            ("resize-window", "-t", match.group(1), "-x", match.group(2), "-y", match.group(3)),
        )
    if "copy-mode" in instruction:
        pane_match = re.search(r"-t (\S+)", inline[0])
        if pane_match is None:
            raise ValueError(f"Unable to compile copy-mode control: {instruction}")
        pane = pane_match.group(1)
        return (
            ("copy-mode", "-t", pane),
            ("send-keys", "-t", pane, "-X", "page-up"),
        )
    if "-X cancel" in instruction:
        pane_match = re.search(r"-t (\S+)", inline[0])
        if pane_match is None:
            raise ValueError(f"Unable to compile copy-mode cancel: {instruction}")
        return (("send-keys", "-t", pane_match.group(1), "-X", "cancel"),)
    raise ValueError(f"Unsupported tmux control instruction: {instruction}")


def _inline_code(text: str) -> list[str]:
    """Return Markdown inline-code spans in source order."""

    return _INLINE_CODE_PATTERN.findall(text)
