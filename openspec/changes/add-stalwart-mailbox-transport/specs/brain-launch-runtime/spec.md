## MODIFIED Requirements

### Requirement: Mailbox enablement is resolved before session start and persisted for resume
The runtime SHALL enable mailbox support through declarative recipe configuration and MAY allow explicit `start-session` CLI overrides for transport-specific ad hoc sessions.

The runtime SHALL resolve one effective mailbox configuration before building the launch plan, SHALL persist that resolved mailbox configuration in the session manifest, and SHALL restore it when resuming the session.

The resolved mailbox configuration SHALL preserve transport-specific binding data appropriate to the selected transport.

For filesystem sessions, that resolved configuration MAY include a filesystem mailbox root and registration-derived filesystem bindings.

For `stalwart` sessions, that resolved configuration SHALL include the mailbox transport identity, mailbox principal identity, mailbox address, and transport-safe endpoint or credential-reference metadata needed to restore the same mailbox binding and construct the same gateway mailbox adapter later without persisting inline secrets in the manifest payload.

#### Scenario: Recipe configuration enables Stalwart mailbox support
- **WHEN** a developer starts an agent session whose resolved recipe enables `stalwart` mailbox support
- **THEN** the runtime resolves that mailbox configuration before building the launch plan
- **AND THEN** the resolved session uses that mailbox transport and principal binding for subsequent mailbox-aware runtime work

#### Scenario: Start session CLI overrides mailbox transport-specific settings
- **WHEN** a developer starts an agent session with explicit mailbox CLI overrides such as mailbox transport or transport-specific mailbox location or endpoint settings
- **THEN** the runtime applies those overrides to the effective mailbox configuration for that session
- **AND THEN** the resulting session manifest records the overridden mailbox transport and transport-safe mailbox bindings rather than forcing resume to re-derive them from recipe defaults

#### Scenario: Resume restores persisted Stalwart mailbox bindings
- **WHEN** a developer resumes a previously started `stalwart` mailbox-enabled session
- **THEN** the runtime restores the mailbox transport, principal binding, mailbox address, and transport-safe mailbox binding metadata from the persisted session manifest
- **AND THEN** runtime mailbox commands for that resumed session preserve the same sender principal and Stalwart mailbox identity unless an explicit refresh changes them later

### Requirement: Mailbox-enabled runtime sessions project mailbox system skills and mailbox env bindings
When mailbox support is enabled for a started session, the runtime SHALL project the platform-owned mailbox system skills into the active agent skillset under a reserved runtime-owned namespace and SHALL populate the transport-specific mailbox binding env contract before mailbox-related work is expected from the agent.

When the selected transport is `filesystem`, the runtime SHALL continue to derive and publish the filesystem mailbox content root and registration-dependent filesystem mailbox bindings for that session.

When the selected transport is `stalwart`, the runtime SHALL publish the real-mail mailbox binding env vars for that session and SHALL NOT synthesize filesystem path bindings that do not belong to that transport.

#### Scenario: Start session projects mailbox system skills with filesystem bindings
- **WHEN** a developer starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the filesystem mailbox binding env vars needed by those mailbox system skills

#### Scenario: Start session projects mailbox system skills with Stalwart bindings
- **WHEN** a developer starts an agent session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skills for that session into the tool adapter's active skills destination under the reserved runtime-owned namespace
- **AND THEN** the runtime starts the session with the email mailbox binding env vars needed by those mailbox system skills
- **AND THEN** the runtime does not populate filesystem mailbox root or mailbox-path bindings for that Stalwart session

### Requirement: Runtime mail commands keep one operator surface while allowing gateway-backed shared mailbox interaction
The runtime SHALL preserve the current operator-facing `mail check`, `mail send`, and `mail reply` command surface and structured mailbox result shape across filesystem and `stalwart` sessions.

The runtime SHALL translate each `mail` command invocation into a runtime-owned mailbox prompt delivered through the existing prompt-turn control path rather than directly mutating mailbox transport state itself.

That mailbox prompt SHALL explicitly tell the agent which projected mailbox system skill to use for the mailbox operation and SHALL append structured mailbox metadata needed for the mailbox operation and result parsing.

The mailbox prompt and projected mailbox system skill SHALL prefer a live gateway mailbox facade when that facade is available for the addressed session.

When no live gateway mailbox facade is available, the runtime MAY continue to rely on the direct session-mediated mailbox path appropriate to the selected transport.

The mailbox prompt SHALL follow gateway-aware transport expectations:

- filesystem prompts SHALL continue to instruct the agent to follow filesystem mailbox rules and helper boundaries when those are required for that transport,
- `stalwart` prompts SHALL direct the agent to use the shared gateway mailbox facade when available or Stalwart-backed mailbox bindings when not, without inheriting filesystem-only `rules/` or managed-script instructions.

The `mail` command handler SHALL validate exactly one structured mailbox result payload returned between `AGENTSYS_MAIL_RESULT_BEGIN` and `AGENTSYS_MAIL_RESULT_END` sentinels in the agent output and SHALL surface that result to the operator in a parseable form.

That sentinel-delimited structured result contract SHALL remain the correctness boundary for mailbox result parsing.

#### Scenario: Filesystem mail command prompt includes filesystem-specific mailbox guidance
- **WHEN** a developer invokes a runtime `mail` command for a filesystem mailbox-enabled session
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the projected filesystem mailbox system skill the agent should use
- **AND THEN** that prompt may direct the agent to inspect filesystem mailbox `rules/` guidance and helper boundaries appropriate to that transport

#### Scenario: Gateway-aware mail command prompt prefers the shared gateway facade
- **WHEN** a developer invokes a runtime `mail` command for a mailbox-enabled session with a live gateway mailbox facade
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the projected mailbox system skill the agent should use
- **AND THEN** that prompt tells the agent to prefer the live gateway mailbox facade for the shared mailbox operation rather than reasoning about transport details directly

#### Scenario: Stalwart mail command prompt excludes filesystem-only mailbox guidance when direct transport fallback is used
- **WHEN** a developer invokes a runtime `mail` command for a `stalwart` mailbox-enabled session with no live gateway mailbox facade
- **THEN** the runtime delivers a runtime-owned mailbox prompt through the existing prompt-turn control surface for that session
- **AND THEN** that prompt explicitly names the projected Stalwart mailbox system skill the agent should use
- **AND THEN** that prompt does not direct the agent to use filesystem mailbox `rules/`, lock files, or managed scripts that are not part of the Stalwart transport

#### Scenario: Mail command returns structured mailbox result
- **WHEN** a mailbox-enabled agent completes a runtime `mail` request
- **THEN** the agent returns one structured mailbox result payload describing the mailbox operation outcome between the required sentinels
- **AND THEN** the runtime validates and prints that result in a parseable form for the operator
