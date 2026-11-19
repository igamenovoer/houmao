# docs-launch-policy-reference Specification

## Purpose
Define the documentation requirements for the launch policy reference page.
## Requirements

### Requirement: Launch policy reference page exists

The build-phase reference SHALL include `docs/reference/build-phase/launch-policy.md`. The page SHALL explain:

- The available `OperatorPromptMode` values, the limits of the selected execution owner, and the most permissive supported native defaults selected for unattended launch.
- The precedence of authored tool parameters and selected native settings over omitted-field defaults, including the possibility of approval prompts under an explicit setting.
- The difference between user-configurable native values and reserved runtime fields, including the error for a supplied reserved value.
- The role of the brain manifest in recording launch inputs and of the versioned registry in selecting a compatible strategy when the provider starts.
- How provider hooks project effective settings, including how `codex.append_unattended_cli_overrides` emits final non-secret Codex preferences from resolved values.
- The DSH migration from its former workspace-write default, including an explicit workspace-restricted example and the `as_is` behavior.

The page SHALL use the launch policy models, engine, provider hooks, and registry as its source.

#### Scenario: Reader understands launch policy purpose
- **WHEN** a reader opens the launch policy page
- **THEN** it connects requested launch defaults to the native settings that take effect at provider start

#### Scenario: Reader can identify available prompt modes
- **WHEN** a reader compares the operator prompt modes
- **THEN** the reference explains the omitted-field behavior of `as_is` and `unattended`
- **AND THEN** it explains how a supported explicit value changes the effective settings

#### Scenario: Reader understands policy resolution
- **WHEN** a reader wants to understand how a policy is selected
- **THEN** the page describes authored input resolution, versioned strategy selection, and native projection

#### Scenario: Reader understands Gemini unattended launch ownership
- **WHEN** a reader consults the reference for maintained strategy ownership
- **THEN** the page describes the available launch strategies for Claude, Codex, Kimi, and DSH

#### Scenario: Reader can retain a workspace-restricted DSH launch
- **WHEN** a reader needs the previous DSH workspace restriction
- **THEN** the page shows how to set it explicitly and explains that the separate approval setting follows its own precedence

#### Scenario: Reader can resolve a reserved-field error
- **WHEN** a reader wants to set a native session or protocol field reserved by Houmao
- **THEN** the reference explains the reservation and directs the reader to the corresponding managed control when available

### Requirement: Launch policy reference documents Kimi unattended TUI auto mode

The launch policy reference SHALL document separate maintained Kimi contracts for `kimi_headless` and the `raw_launch` TUI strategy. It SHALL give the minimum-only `>=2.1.1` range and explain rejection below the floor.

The page SHALL explain that headless uses its native prompt-mode policy and excludes incompatible `--auto`, `--yolo`, and `--plan` flags. TUI uses `--auto` as the unattended default for fresh and resumed startup and honors supported authored permission settings through native startup inputs. Policy setup SHALL be documented as outside the conversation.

The reference SHALL document native `$KIMI_CODE_HOME/SYSTEM.md` projection, `${base_prompt}` preservation, v2-engine enforcement, rejection of every `${identifier}` placeholder in Houmao prompt text, and conflicts that would bypass the native prompt. It SHALL distinguish role injection from permission mode and credential readiness.

#### Scenario: Reader understands Kimi unattended backend split
- **WHEN** a reader opens the launch policy reference
- **THEN** they can distinguish the headless native prompt-mode constraint from the TUI unattended default and supported overrides
- **AND THEN** they understand native managed-home role projection happens before startup

#### Scenario: Reader understands Kimi version and prompt boundaries
- **WHEN** a reader checks the maintained Kimi strategy
- **THEN** the reference identifies the minimum-only version range and native `SYSTEM.md` contract
- **AND THEN** it presents no earlier-version or auto-skill fallback

#### Scenario: Reader understands Kimi auto mode boundary
- **WHEN** a reader checks Kimi's unattended default
- **THEN** the reference explains that auto handles ordinary approvals and questions without operator input and remains subject to provider hard denials
- **AND THEN** it describes the precedence of an authored supported permission mode

### Requirement: Launch-policy reference excludes Gemini
The launch-policy reference SHALL document no Gemini strategy, version range, owned path, provider hook, unattended behavior, or auth readiness claim.

#### Scenario: Launch-policy inventory omits Gemini
- **WHEN** a reader inspects maintained strategy tables and examples
- **THEN** no Gemini launch-policy entry appears
