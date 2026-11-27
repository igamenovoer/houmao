# docs-launch-policy-reference Specification

## Purpose
Define the documentation requirements for the launch policy reference page.
## Requirements

### Requirement: Launch policy reference page exists

The build-phase reference SHALL include `docs/reference/build-phase/launch-policy.md` to document launch policy.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The build-phase reference SHALL include `docs/reference/build-phase/launch-policy.md`. The page SHALL explain:

- The available `OperatorPromptMode` values, the selected execution owner's limits, and the maximum qualified native permission posture required for unattended launch for each supported provider and run mode.
- How normalized effective permission values are validated under `unattended`, how launch reports a conflict, and how `as_is` retains supported authored values and native behavior for omissions.
- The difference between user-configurable native values and reserved runtime fields, including the error for a supplied reserved value.
- The role of the brain manifest in recording launch inputs and of the versioned registry in selecting a compatible strategy when the provider starts.
- How provider hooks project effective settings, including how `codex.append_unattended_cli_overrides` emits final non-secret Codex preferences from resolved values.
- How to migrate a definition that previously selected restrictive permissions under `unattended` by choosing `as_is`, including an explicit DSH workspace-restricted example.

The page SHALL use the launch policy models, engine, provider hooks, and registry as its source.

#### Scenario: Reader understands launch policy purpose
- **WHEN** a reader opens the launch policy page
- **THEN** it connects the requested operator prompt mode to the native permission posture that takes effect at provider start and explicit relaunch

#### Scenario: Reader can identify available prompt modes
- **WHEN** a reader compares the operator prompt modes
- **THEN** the reference explains that unattended launch uses the qualified posture for omitted or matching effective inputs and rejects conflicting values
- **AND THEN** it explains that `as_is` allows supported authored values and native defaults for omitted permission fields

#### Scenario: Reader understands policy resolution
- **WHEN** a reader wants to understand how a policy is selected
- **THEN** the page describes authored input resolution, versioned strategy selection, and native projection

#### Scenario: Reader understands Gemini unattended launch ownership
- **WHEN** a reader consults the reference for maintained strategy ownership
- **THEN** the page describes the qualified unattended permission posture for Claude, Codex, Kimi, DSH, and Hermes

#### Scenario: Reader can retain a workspace-restricted DSH launch
- **WHEN** a reader needs the previous DSH workspace restriction
- **THEN** the page shows how to select `as_is` and an explicit workspace-restricted sandbox
- **AND THEN** it explains how DSH determines approval policy when the example omits it

#### Scenario: Reader can resolve a reserved-field error
- **WHEN** a reader wants to set a native session or protocol field reserved by Houmao
- **THEN** the reference explains the reservation and directs the reader to the corresponding managed control when available

#### Scenario: Reader diagnoses a conflicting launch permission

- **WHEN** a reader looks up a conflict from a stored setup, profile, direct override, or generated launch helper
- **THEN** the page explains how the effective source and required value appear in diagnostics
- **AND THEN** it explains that unattended permission validation runs before provider-start mutation and leaves the existing agent and authored settings intact

### Requirement: Launch-policy reference lists inclusive executable minimums

The reference SHALL list the applicable DSH, Kimi Code, Claude Code, and Codex minimums by launch mode or backend, including accepted release channels. It SHALL explain that newer eligible builds pass the version check and that native startup can still report a protocol, capability, or identity failure. Qualification records SHALL identify the builds actually tested.

#### Scenario: An operator checks which build to install

- **WHEN** an operator looks up a tool and mode in the launch-policy reference
- **THEN** they can identify the applicable minimum and the native startup checks that determine readiness

#### Scenario: A native mode guide names a qualified build

- **WHEN** a Kimi Web, Kimi ACP, or Codex app-server guide cites a tested release
- **THEN** its launch instructions state the inclusive minimum and label the specific release as evidence

### Requirement: Launch policy reference documents Kimi unattended TUI auto mode

The launch policy reference SHALL document separate maintained Kimi contracts for `kimi_headless` and the `raw_launch` TUI strategy. It SHALL give the minimum-only `>=2.1.1` range and explain rejection below the floor.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The page SHALL explain that headless uses its native prompt-mode policy and excludes incompatible `--auto`, `--yolo`, and `--plan` flags. TUI uses `--auto` for fresh and resumed unattended startup. A conflicting effective permission setting requires `as_is` and a startup path that supports the authored setting. Policy setup SHALL be documented as outside the conversation.

The reference SHALL document native `$KIMI_CODE_HOME/SYSTEM.md` projection, `${base_prompt}` preservation, v2-engine enforcement, rejection of every `${identifier}` placeholder in Houmao prompt text, and conflicts that would bypass the native prompt. It SHALL distinguish role injection from permission mode and credential readiness.

#### Scenario: Reader understands Kimi unattended backend split
- **WHEN** a reader opens the launch policy reference
- **THEN** they can distinguish headless native `auto` from the TUI's explicit `--auto` and supported `as_is` restrictions
- **AND THEN** they understand native managed-home role projection happens before startup

#### Scenario: Reader understands Kimi version and prompt boundaries
- **WHEN** a reader checks the maintained Kimi strategy
- **THEN** the reference identifies the minimum-only version range and native `SYSTEM.md` contract
- **AND THEN** it presents no earlier-version or auto-skill fallback

#### Scenario: Reader understands Kimi auto mode boundary
- **WHEN** a reader checks Kimi's unattended permission posture
- **THEN** the reference explains that auto handles ordinary approvals and questions without operator input and remains subject to provider hard denials
- **AND THEN** it explains how to use a supported authored permission mode with `as_is`

### Requirement: Launch-policy reference excludes Gemini
The launch-policy reference SHALL document no Gemini strategy, version range, owned path, provider hook, unattended behavior, or auth readiness claim.

#### Scenario: Launch-policy inventory omits Gemini
- **WHEN** a reader inspects maintained strategy tables and examples
- **THEN** no Gemini launch-policy entry appears
