## MODIFIED Requirements

### Requirement: Runtime mail commands keep one operator surface while allowing gateway-backed shared mailbox interaction
The runtime SHALL preserve the current operator-facing `mail check`, `mail send`, and `mail reply` command surface and structured mailbox result shape across filesystem and `stalwart` sessions.

The runtime SHALL translate each `mail` command invocation into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly manipulating mailbox files or mailbox SQLite state itself.

That mailbox prompt SHALL explicitly tell the agent which discoverable projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation and result parsing.

For the current mailbox skill contract, that prompt SHALL identify the stable transport-specific mailbox skill name together with the primary visible mailbox skill path under the active skill destination.

The runtime SHALL NOT mention or rely on a hidden `.system/mailbox/...` mailbox path in that prompt.

The mailbox prompt and projected mailbox system skill SHALL prefer a live gateway mailbox facade when that facade is available for the addressed session.

When no live gateway mailbox facade is available, the runtime MAY continue to rely on the direct session-mediated mailbox path appropriate to the selected transport.

The mailbox prompt SHALL follow gateway-aware transport expectations:

- filesystem prompts SHALL continue to instruct the agent to follow filesystem mailbox rules and helper boundaries when those are required for that transport,
- `stalwart` prompts SHALL direct the agent to use the shared gateway mailbox facade when available or Stalwart-backed mailbox bindings when not, without inheriting filesystem-only `rules/` or managed-script instructions.

The runtime-owned prompt-construction path SHALL dispatch by transport and gateway availability rather than assuming filesystem-only mailbox instructions for every mailbox-enabled session.

The `mail` command handler SHALL validate exactly one structured mailbox result payload returned between `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` sentinels in the agent output and SHALL surface that result to the operator in a parseable form.

That sentinel-delimited structured result contract SHALL be the correctness boundary for mailbox result parsing. The runtime SHALL NOT rely on generic shadow dialog projection fidelity as the guarantee that mailbox result text was recovered exactly.

For `shadow_only` mailbox commands, the runtime SHALL continue polling post-submit shadow text for the active request after generic lifecycle completion becomes provisionally satisfied until exactly one sentinel-delimited mailbox result payload for that request is visible or an existing timeout, stall, blocked-surface, unsupported-surface, or disconnect failure ends the command.

For `shadow_only` mailbox commands, a submit-ready surface without a complete sentinel-delimited mailbox result for the active request SHALL be treated as provisional only. The runtime SHALL NOT return mailbox success or a missing-sentinel parse failure solely because the generic shadow lifecycle gate became satisfied before the sentinel contract was observed.

For `shadow_only` mailbox commands, prompt-echo mentions of `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` inside ordinary prose, echoed mailbox request content, or echoed response-contract metadata SHALL NOT satisfy mailbox completion gating or mailbox result validation by themselves.

For `shadow_only` mailbox commands, mailbox completion gating and mailbox result validation SHALL use the same active-request result-selection contract so that surfaces ignored as prompt-echo noise during provisional completion are not later treated as malformed mailbox results.

#### Scenario: Filesystem mail command prompt includes filesystem-specific mailbox guidance
- **WHEN** a developer invokes a runtime `mail` command for a filesystem mailbox-enabled session
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the discoverable filesystem mailbox system skill the agent should use
- **AND THEN** that prompt points at the primary visible filesystem mailbox skill path without mentioning a hidden `.system` mailbox path
- **AND THEN** that prompt tells the agent to inspect the shared mailbox `rules/` directory before interacting with shared mailbox state
- **AND THEN** that prompt tells the agent to use shared scripts from `rules/scripts/` for any mailbox step that touches `index.sqlite` or `locks/`

#### Scenario: Gateway-aware mail command prompt prefers the shared gateway facade
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session with a live gateway mailbox facade
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the discoverable projected mailbox system skill the agent should use
- **AND THEN** that prompt tells the agent to prefer the live gateway mailbox facade for the shared mailbox operation rather than reasoning about transport details directly

#### Scenario: Stalwart mail command prompt excludes filesystem-only mailbox guidance when direct transport fallback is used
- **WHEN** a developer invokes a runtime `mail` command for a `stalwart` mailbox-enabled session with no live gateway mailbox facade
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the discoverable Stalwart mailbox system skill the agent should use
- **AND THEN** that prompt does not direct the agent to use filesystem mailbox `rules/`, lock files, or managed scripts that are not part of the Stalwart transport
