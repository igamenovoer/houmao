## MODIFIED Requirements

### Requirement: Runtime mail commands keep one operator surface while allowing gateway-backed shared mailbox interaction
The runtime SHALL preserve the current operator-facing `mail check`, `mail send`, and `mail reply` command surface across filesystem and `stalwart` sessions.

When the runtime owns mailbox execution directly, including manager-owned direct execution or gateway-backed execution, it SHALL return authoritative mailbox success or failure for the requested operation.

When the runtime executes a mailbox operation by submitting a request through a live TUI session, it SHALL treat the command outcome as non-authoritative request lifecycle state rather than mailbox success or failure recovered from exact transcript parsing.

The runtime SHALL still translate TUI-mediated `mail` invocations into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly manipulating mailbox files or mailbox SQLite state itself.

That mailbox prompt SHALL explicitly tell the agent which discoverable projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation.

For the current mailbox skill contract, that prompt SHALL identify the stable transport-specific mailbox skill name together with the primary visible mailbox skill path under the active skill destination.

The runtime SHALL NOT mention or rely on a hidden `.system/mailbox/...` mailbox path in that prompt.

The mailbox prompt and projected mailbox system skill SHALL prefer a live gateway mailbox facade when that facade is available for the addressed session.

When no live gateway mailbox facade is available, the runtime MAY continue to rely on the direct session-mediated mailbox path appropriate to the selected transport.

The mailbox prompt SHALL follow gateway-aware transport expectations:

- filesystem prompts SHALL continue to instruct the agent to follow filesystem mailbox rules and helper boundaries when those are required for that transport,
- `stalwart` prompts SHALL direct the agent to use the shared gateway mailbox facade when available or Stalwart-backed mailbox bindings when not, without inheriting filesystem-only `rules/` or managed-script instructions.

The runtime-owned prompt-construction path SHALL dispatch by transport and gateway availability rather than assuming filesystem-only mailbox instructions for every mailbox-enabled session.

For TUI-mediated mailbox commands, exact sentinel-delimited structured result parsing SHALL NOT be the correctness boundary for command completion.

For TUI-mediated mailbox commands, shadow parsing and transcript recovery MAY be used for:

- submit-ready versus busy state tracking,
- request-submission confirmation,
- optional preview,
- diagnostics.

For TUI-mediated mailbox commands, the runtime SHALL NOT require exactly one parseable mailbox-result payload for the active request in order to return a non-authoritative submitted or rejected outcome.

If a parseable active-request sentinel payload is recovered in TUI-mediated mode, the runtime MAY surface it as optional diagnostic or preview data. It SHALL NOT be required for the command to return.

For `shadow_only` mailbox commands, prompt-echo mentions of `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` inside ordinary prose, echoed mailbox request content, or echoed response-contract metadata SHALL NOT be treated as authoritative mailbox-result evidence.

For `shadow_only` mailbox commands, mailbox correctness SHALL not depend on `dialog_projection.dialog_text` being an exact recovered reply transcript.

#### Scenario: Verified direct execution returns authoritative mailbox result
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session
- **AND WHEN** the runtime owns the mailbox execution path directly
- **THEN** the runtime returns authoritative mailbox success or failure for that operation
- **AND THEN** the command result reflects protocol-owned or manager-owned mailbox truth rather than transcript recovery

#### Scenario: TUI-mediated mail send returns non-authoritative submitted state
- **WHEN** a developer invokes `mail send` for a mailbox-enabled session
- **AND WHEN** the execution path is prompt submission into a live TUI session
- **THEN** the runtime returns request lifecycle state such as submitted, rejected, interrupted, busy, or TUI error
- **AND THEN** the runtime does not require exact structured mailbox-result parsing to complete the command

#### Scenario: TUI preview data does not redefine mailbox truth
- **WHEN** a mailbox-enabled TUI session emits a parseable sentinel-delimited JSON result or other mailbox-related preview text
- **THEN** the runtime MAY surface that data as optional preview or diagnostics
- **AND THEN** the authoritative outcome contract for the command remains based on execution authority rather than preview transcript recovery

#### Scenario: Mail command fails fast when session cannot accept a new turn
- **WHEN** a developer invokes a runtime `mail` command for a session that is already busy or otherwise cannot safely accept a new prompt turn
- **THEN** the runtime returns an explicit mailbox-command error
- **AND THEN** it does not silently queue hidden mailbox work for later execution
