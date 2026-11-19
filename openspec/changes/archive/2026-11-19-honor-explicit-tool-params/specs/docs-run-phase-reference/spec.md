# Spec Delta

## MODIFIED Requirements

### Requirement: Run-phase reference documents Kimi unattended TUI startup and relaunch
The run-phase backend and lifecycle references SHALL document that maintained Kimi Code 2.1.1-or-later local-interactive sessions can run with `operator_prompt_mode = unattended` while remaining visible TUI sessions.

The reference SHALL explain that `--auto` supplies the Kimi TUI unattended default when permission mode is omitted. It SHALL document supported authored modes and applicable continuation limits. It SHALL describe native managed-home role projection before startup, support for `--auto` with `--continue` or `--session <session_id>`, and policy setup outside the conversation.

The reference SHALL distinguish Kimi `as_is` TUI launch from unattended TUI launch, identify 2.1.1 as the minimum maintained version, state that Kimi releases before it are unsupported, and state that support has no upper version limit.

#### Scenario: Reader sees Kimi TUI unattended behavior
- **WHEN** a reader opens the Kimi local-interactive backend reference
- **THEN** it states that native `--auto` supplies the unattended default for an omitted permission setting
- **AND THEN** it states that native role instructions are in place before workload prompts

#### Scenario: Reader sees Kimi resumed startup behavior
- **WHEN** a reader opens the Kimi relaunch reference
- **THEN** it shows the default native `--auto` combined with `--continue` or `--session <session_id>`
- **AND THEN** it describes no post-readiness auto-mode or role-prompt command

#### Scenario: Reader can distinguish as-is from unattended
- **WHEN** a reader compares Kimi launch prompt modes
- **THEN** `as_is` uses native permission behavior for omitted settings
- **AND THEN** `unattended` supplies the native no-question default while supported authored permission values retain their effect

#### Scenario: Reader sees current Kimi system-prompt evidence
- **WHEN** a reader opens the Kimi role-injection reference
- **THEN** the documentation describes the Kimi `>=2.1.1` native `SYSTEM.md` integration from current baseline source evidence
- **AND THEN** it presents no below-floor compatibility path
