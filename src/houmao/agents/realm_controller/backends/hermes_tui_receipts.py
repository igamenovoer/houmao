"""Typed durable Hermes TUI prompt evidence and identity checks."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from houmao.agents.realm_controller.backends.hermes_native import (
    HermesNativeError,
    read_hermes_evidence,
)
from houmao.agents.realm_controller.models import SessionEvent

HERMES_TUI_ADMISSION_FILE = "hermes-native-admission.json"
HermesTuiAdmissionState = Literal[
    "submitting", "queued", "running", "completed", "failed", "interrupted", "uncertain"
]
HermesTuiTerminalOutcome = Literal["completed", "failed", "interrupted"]


class HermesTuiAdmission(BaseModel):
    """Correlate the original Houmao operation with its exact native admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: str
    generation_id: str
    native_session_id: str
    input_digest: str
    submission_id: str
    daemon_instance_id: str
    native_admission_id: str | None = None
    native_admission_sequence: int | None = Field(default=None, strict=True, gt=0)
    native_authority_epoch: int | None = Field(default=None, strict=True, gt=0)
    native_execution_generation: int | None = Field(default=None, strict=True, gt=0)
    status: HermesTuiAdmissionState = "submitting"
    native_outcome: str | None = None
    replay_epoch: str | None = None
    last_sequence: int = 0
    replay_gap: bool = False
    output_text: str = Field(default="", repr=False)
    events: tuple[SessionEvent, ...] = Field(default=(), repr=False)

    @property
    def state(self) -> HermesTuiAdmissionState:
        """Return the normalized disposition of this native operation."""

        return self.status

    @property
    def terminal(self) -> bool:
        """Report whether the recorded disposition is terminal."""

        return self.status in {"completed", "failed", "interrupted"}

    @property
    def terminal_outcome(self) -> HermesTuiTerminalOutcome | None:
        """Return the outcome only when this record proves exact native settlement."""

        status = self.status
        if status not in ("completed", "failed", "interrupted") or not self._has_native_binding:
            return None
        if status == "completed" and self.native_execution_generation is None:
            return None
        if normalize_hermes_tui_receipt("terminal", self.native_outcome) != status:
            return None
        return status

    @property
    def _has_native_binding(self) -> bool:
        """Check the native fields written with every acknowledged admission."""

        return (
            bool(self.native_admission_id)
            and self.native_admission_sequence is not None
            and self.native_authority_epoch is not None
        )


def read_hermes_tui_admission(
    path: Path,
    *,
    request_id: str,
    generation_id: str,
    native_session_id: str,
) -> HermesTuiAdmission | None:
    """Read owner-private evidence for the exact managed request and native session."""

    try:
        record = read_hermes_evidence(path)
        if record is None:
            return None
        admission = HermesTuiAdmission.model_validate(record)
    except (OSError, ValueError, RecursionError, HermesNativeError):
        return None
    if (admission.request_id, admission.generation_id, admission.native_session_id) != (
        request_id,
        generation_id,
        native_session_id,
    ):
        return None
    if admission.terminal and admission.terminal_outcome is None:
        # An authenticated pre-handoff refusal has no native admission and cannot settle a handoff.
        if not (
            admission.status == "failed"
            and admission.native_admission_id is None
            and admission.native_admission_sequence is None
            and admission.native_authority_epoch is None
            and admission.native_execution_generation is None
            and admission.native_outcome is None
        ):
            return None
    if admission.status in {"queued", "running"} and (
        not admission._has_native_binding
        or admission.native_outcome is not None
        or ((admission.native_execution_generation is None) != (admission.status == "queued"))
    ):
        return None
    return admission


def normalize_hermes_tui_receipt(status: object, outcome: object) -> HermesTuiAdmissionState:
    """Map Hermes durable admission terminology without inferring unsupported outcomes."""

    if status == "queued":
        return "queued"
    if status == "started":
        return "running"
    if status == "unknown":
        return "uncertain"
    if status == "terminal":
        if outcome == "completed":
            return "completed"
        if outcome in ("cancelled", "interrupted", "replaced", "steered"):
            return "interrupted"
        if outcome in ("failed", "rejected", "error"):
            return "failed"
        return "uncertain"
    raise HermesNativeError("Hermes did not return a verified admission status.")
