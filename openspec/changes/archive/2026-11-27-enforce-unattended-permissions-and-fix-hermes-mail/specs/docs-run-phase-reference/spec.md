# Spec Delta

## MODIFIED Requirements

### Requirement: Run-phase reference documents Kimi unattended TUI startup and relaunch
The run-phase backend and lifecycle references SHALL document that maintained Kimi Code 2.1.1-or-later local-interactive sessions can run with `operator_prompt_mode = unattended` while remaining visible TUI sessions.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The reference SHALL explain that `--auto` supplies the required Kimi TUI unattended posture for fresh and resumed start. It SHALL document conflict rejection, supported `as_is` permission values, and their applicable continuation limits. It SHALL describe native managed-home role projection before startup, support for `--auto` with `--continue` or `--session <session_id>`, and policy setup outside the conversation.

The reference SHALL distinguish Kimi `as_is` TUI launch from unattended TUI launch, identify 2.1.1 as the minimum maintained version, state that Kimi releases before it are unsupported, and state that support has no upper version limit.

#### Scenario: Reader sees Kimi TUI unattended behavior
- **WHEN** a reader opens the Kimi local-interactive backend reference
- **THEN** it states that native `--auto` supplies the required unattended posture
- **AND THEN** it states that native role instructions are in place before workload prompts

#### Scenario: Reader sees Kimi resumed startup behavior
- **WHEN** a reader opens the Kimi relaunch reference
- **THEN** it shows native `--auto` combined with `--continue` or `--session <session_id>` for unattended relaunch
- **AND THEN** it describes no post-readiness auto-mode or role-prompt command

#### Scenario: Reader can distinguish as-is from unattended
- **WHEN** a reader compares Kimi launch prompt modes
- **THEN** the reference explains that `as_is` respects supported authored settings and uses native permission behavior for omissions
- **AND THEN** it explains that `unattended` uses native `auto` and rejects a conflicting effective authored permission

#### Scenario: Reader sees current Kimi system-prompt evidence
- **WHEN** a reader opens the Kimi role-injection reference
- **THEN** the documentation describes the Kimi `>=2.1.1` native `SYSTEM.md` integration from current baseline source evidence
- **AND THEN** it presents no below-floor compatibility path

## ADDED Requirements

### Requirement: Run-phase reference explains managed sandbox and approval behavior

The run-phase provider references SHALL describe the effective unattended native permission posture, its conflict diagnostic, and the corresponding `as_is` settings where supported. They SHALL distinguish configurable native permissions from immutable provider rules, execution-owner limits, and Houmao gateway authorization.

#### Scenario: Reader needs a restricted or interactive DSH session

- **WHEN** a reader consults the DSH headless, service, or Web launch guide
- **THEN** the guide explains that unattended startup requires `danger-full-access` and `never`
- **AND THEN** it shows how to select `as_is` for a custom sandbox or browser approval interaction
- **AND THEN** it identifies any runtime mode that lacks a native human answerer

#### Scenario: Reader checks Hermes approval behavior

- **WHEN** a reader consults the Hermes runtime reference
- **THEN** it describes the unattended native approval policy for TUI, headless, and ACP and the service's verified native edit mode
- **AND THEN** it explains that ACP can grant a qualified attributable tool request once and refuses unsupported interactions
- **AND THEN** it describes how manual TUI users see and resolve approval waits and how state represents unavailable evidence

#### Scenario: Reader observes a live interactive change

- **WHEN** a reader checks how an intentional permission change in a live native surface affects manager state, gateway reattachment, or relaunch
- **THEN** the reference explains that observation and reattachment report live state without reapplying startup permissions
- **AND THEN** it explains that an explicit relaunch revalidates and projects the selected startup posture
