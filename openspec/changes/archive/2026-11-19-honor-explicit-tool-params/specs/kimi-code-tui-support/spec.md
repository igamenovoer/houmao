# Spec Delta

## MODIFIED Requirements

### Requirement: Kimi unattended TUI startup establishes policy without a conversational turn

Maintained Kimi 2.1.1-or-later TUI startup SHALL apply the resolved native permission mode after role projection and before managed input. Houmao SHALL use `--auto` for the omitted unattended permission mode and a qualified native startup surface for a supported authored value. Launch SHALL establish policy and role outside the conversation.

Under the unattended default, normal startup and work SHALL proceed without approval, answer, or confirmation states. A deliberate approval-setting override SHALL retain its native behavior. If a provider-required intervention remains, Houmao SHALL preserve the evidence and report the intervention.

#### Scenario: Fresh unattended Kimi starts without policy or role chat
- **WHEN** Houmao launches a fresh maintained Kimi TUI in unattended mode with permission mode omitted
- **THEN** the final launch command includes native `--auto` and the managed native prompt is already projected
- **AND THEN** the first managed conversational input is workload content

#### Scenario: Fresh unattended Kimi starts prompt-free
- **WHEN** Houmao starts a fresh maintained Kimi TUI with the unattended default permission mode
- **THEN** native `--auto` and native `SYSTEM.md` establish policy and role before conversation
- **AND THEN** startup sends no policy or role bootstrap prompt

#### Scenario: A user selects a mode for a resumed TUI
- **WHEN** a Kimi TUI relaunch resumes its saved session with a supported explicit permission mode
- **THEN** that mode takes effect at native startup
- **AND THEN** Houmao sends no policy-changing conversation input to establish it

#### Scenario: Avoidable confirmation fails unattended validation
- **WHEN** a Kimi TUI using the unattended default presents a confirmation or question that a supported startup setting can suppress
- **THEN** validation reports the unattended compatibility failure
- **AND THEN** the harness preserves the native intervention as evidence
