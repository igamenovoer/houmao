## MODIFIED Requirements

### Requirement: Name-addressed tmux-backed session control SHALL recover `agent_def_dir` from session environment
For tmux-backed session-control commands that accept `--agent-identity` (`send-prompt`, `send-keys`, and `stop-session`), the system SHALL allow callers to omit `--agent-def-dir` when the identity is name-based rather than path-like.

When `--agent-identity` is name-based and `--agent-def-dir` is omitted, the
system SHALL:
- resolve the addressed tmux session by canonical agent identity,
- prefer the tmux-published `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values when they are present and valid,
- fall back to fresh shared-registry discovery metadata when tmux-local discovery pointers are missing, blank, or stale, and
- use the recovered absolute agents root for resume or control operations.

The shared-registry fallback SHALL apply only to discovery-pointer unavailability. Hard validation mismatches such as a manifest whose persisted tmux session identity does not match the addressed agent name SHALL still fail fast.

When `--agent-def-dir` is provided explicitly, the system SHALL use the
explicit CLI value instead of the tmux-published or registry-published fallback.

Manifest-path control flows are unchanged by this requirement.

#### Scenario: Name-based send-prompt omits explicit agent-def-dir
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hello"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and delivers the prompt without requiring explicit `--agent-def-dir`

#### Scenario: Name-based stop-session omits explicit agent-def-dir
- **WHEN** a developer runs `stop-session --agent-identity chris`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and stops the addressed session without requiring explicit `--agent-def-dir`

#### Scenario: Name-based send-keys omits explicit agent-def-dir
- **WHEN** a developer runs `send-keys --agent-identity chris --sequence "<[Escape]>"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** that tmux session publishes valid `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` values
- **THEN** the runtime resumes and delivers the control-input request without requiring explicit `--agent-def-dir`

#### Scenario: Explicit CLI agent-def-dir overrides tmux fallback
- **WHEN** a developer runs `stop-session --agent-identity chris --agent-def-dir /abs/custom/agents`
- **AND WHEN** tmux session `AGENTSYS-chris` publishes a different `AGENTSYS_AGENT_DEF_DIR`
- **THEN** the runtime uses `/abs/custom/agents` as the effective agent-definition root

#### Scenario: Registry fallback covers missing tmux manifest pointer
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hi"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** `AGENTSYS_MANIFEST_PATH` is missing, blank, or stale in that tmux session environment
- **AND WHEN** a fresh shared-registry record exists for `AGENTSYS-chris`
- **THEN** the runtime resolves the session through the shared-registry record instead of failing immediately on the tmux-local pointer problem

#### Scenario: Registry fallback covers missing tmux agent-def-dir pointer
- **WHEN** a developer runs `send-prompt --agent-identity chris --prompt "hi"`
- **AND WHEN** tmux session `AGENTSYS-chris` exists
- **AND WHEN** `AGENTSYS_AGENT_DEF_DIR` is missing, blank, or stale in that tmux session environment
- **AND WHEN** a fresh shared-registry record exists for `AGENTSYS-chris`
- **THEN** the runtime resolves the effective agent-definition root through the shared-registry record instead of failing immediately on the tmux-local pointer problem

#### Scenario: Identity mismatch still fails fast instead of falling back
- **WHEN** a developer runs a tmux-backed name-based control command for `AGENTSYS-chris`
- **AND WHEN** a candidate tmux-local or shared-registry manifest resolves to persisted tmux session identity other than `AGENTSYS-chris`
- **THEN** the runtime rejects the operation with an explicit mismatch error
- **AND THEN** it does not silently recover by targeting a different live session

#### Scenario: Manifest-path control does not depend on tmux fallback
- **WHEN** a developer runs `stop-session --agent-identity /abs/runtime/sessions/cao_rest/session.json`
- **THEN** the runtime keeps the existing manifest-path control flow
- **AND THEN** this change does not require tmux session environment lookup for that request

## ADDED Requirements

### Requirement: Registry refresh failures do not overturn already-successful runtime control actions
When a tmux-backed runtime action has already completed its primary control work successfully and later manifest persistence attempts to refresh shared-registry discovery metadata, the system SHALL preserve the successful primary action result even if the registry refresh fails.

This applies at minimum to prompt delivery, interrupt, raw control input, mailbox-binding refresh, and other manifest-persisting runtime control flows that reuse the same live session.

The system SHALL still surface the registry refresh problem through an explicit warning, diagnostic, or equivalent operator-visible reporting path.

#### Scenario: Successful prompt delivery remains successful when registry refresh fails
- **WHEN** a tmux-backed runtime session successfully processes a prompt submission
- **AND WHEN** manifest persistence later encounters a shared-registry refresh failure
- **THEN** the prompt operation still reports success for the completed primary action
- **AND THEN** the registry failure is surfaced separately as a warning or diagnostic rather than replacing the prompt result

#### Scenario: Successful mailbox binding refresh remains successful when registry refresh fails
- **WHEN** a tmux-backed mailbox-enabled runtime session successfully refreshes its mailbox bindings
- **AND WHEN** the follow-on shared-registry refresh fails
- **THEN** the mailbox-binding refresh still reports success for the completed primary action
- **AND THEN** the registry refresh problem is surfaced separately from the mailbox result

### Requirement: Stop-session success is preserved when shared-registry cleanup fails after termination
When authoritative `stop-session` teardown has already terminated the addressed runtime-owned tmux-backed session successfully, a later shared-registry cleanup failure SHALL NOT change that stop result into a failed stop outcome.

The runtime SHALL still surface the registry cleanup failure separately so operators know cleanup did not finish cleanly.

#### Scenario: Registry cleanup failure does not negate a successful stop
- **WHEN** the runtime successfully terminates a runtime-owned tmux-backed session through `stop-session`
- **AND WHEN** later shared-registry record removal fails because of a filesystem or permission problem
- **THEN** the stop operation still reports the successful termination result
- **AND THEN** the registry cleanup problem is surfaced separately for operator follow-up
