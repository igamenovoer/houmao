# Spec Delta

## REMOVED Requirements

### Requirement: `codex_app_server` remains explicit opt-in during one deprecation window
**Reason**: The deprecation window closes: `codex_app_server` has not been tested or qualified against current Codex releases for a long time and is declared unmaintained. Continuing to honor explicit opt-in requests presents unmaintained behavior as supported.

**Migration**: Use `codex_headless` for structured non-interactive Codex sessions or `local_interactive` for tracked Codex TUI sessions. Persisted manifests naming `codex_app_server` are rejected at session creation with an explicit unmaintained-backend error.

## ADDED Requirements

### Requirement: `codex_app_server` is unmaintained and blocked at launch
The `codex_app_server` backend is unmaintained and no longer supported for launching. The runtime SHALL reject session-start requests with `backend=codex_app_server` via an explicit unmaintained-backend error before provider start, naming the backend and the maintained alternatives; retained manifests naming it SHALL be rejected before new session creation. The module MAY remain as dead code; no runtime path SHALL silently honor or substitute it.

#### Scenario: Explicit codex_app_server request is rejected
- **WHEN** a developer requests `backend=codex_app_server` for a new session
- **THEN** the runtime fails with an explicit unmaintained-backend error naming `codex_app_server`
- **AND THEN** no Codex process is started

#### Scenario: Retained codex_app_server manifest is rejected
- **WHEN** a persisted session manifest names `codex_app_server` and a new session creation is attempted from it
- **THEN** the runtime rejects the request with the same explicit unmaintained-backend error
- **AND THEN** it does not silently substitute another backend

#### Scenario: Error names maintained alternatives
- **WHEN** the unmaintained-backend error surfaces to an operator
- **THEN** the message names `codex_headless` and `local_interactive` as the maintained Codex backends

## MODIFIED Requirements

### Requirement: Codex runtime launch applies non-interactive home bootstrap
For Codex launches, the runtime SHALL apply a runtime-owned bootstrap step to the generated Codex home configuration before starting the tool for:
- `backend=codex_headless`
- `backend=cao_rest`

Bootstrap behavior SHALL include:
- ensuring launch-context trust is recorded for the active workspace target in Codex project config, and
- seeding required notice state needed to avoid interactive onboarding/warning prompts for the selected policy profile, and
- applying configured non-interactive launch flags needed to reduce interactive startup prompts (including `approval_policy` / `sandbox_mode` only when explicitly present in the selected Codex setup bundle; the runtime SHALL NOT hardcode new approval/sandbox defaults).

#### Scenario: CAO Codex launch seeds trust for launch workspace
- **WHEN** a Codex CAO-backed session is started with a resolved working directory
- **THEN** runtime bootstrap writes/updates Codex runtime-home config so the launch workspace trust decision is pre-seeded before terminal start

#### Scenario: Codex headless launch uses the same bootstrap contract
- **WHEN** a Codex headless session is started from a generated brain home
- **THEN** runtime applies the same Codex bootstrap contract before the first headless CLI turn
