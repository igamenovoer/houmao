## Purpose
Define the runtime-owned mailbox system-skill contract, including env bindings, projection behavior, and shared-mailbox guidance across mailbox transports.
## Requirements

### Requirement: Runtime-owned mailbox system skills are available to launched agents
The system SHALL provide implemented mailbox access to agents through runtime-owned mailbox system skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These mailbox system skills SHALL be projected into mailbox-enabled sessions in a discoverable non-hidden mailbox subtree under the active skill destination using the same active skill-destination contract as other projected skills.

For the current tool adapters whose active skill destination is `skills`, the mailbox system skill surface SHALL be `skills/mailbox/...`.

The projected mailbox skill set MAY vary by the selected mailbox transport, including filesystem-backed and real-mail-backed transports.

#### Scenario: Filesystem mailbox-enabled agent receives projected mailbox system skills
- **WHEN** the runtime starts an agent session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the filesystem mailbox skill is available through the discoverable mailbox subtree rather than through hidden `.system` entries
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Stalwart mailbox-enabled agent receives projected mailbox system skills
- **WHEN** the runtime starts an agent session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the Stalwart mailbox skill is available through the discoverable mailbox subtree rather than through hidden `.system` entries
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** the mailbox system skills use a reserved runtime-owned mailbox subtree under the active skill destination
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

#### Scenario: Hidden mailbox compatibility mirror is not projected
- **WHEN** the runtime projects mailbox system skills for a mailbox-enabled session
- **THEN** the runtime does not create a parallel `skills/.system/mailbox/...` mailbox skill tree for that session
- **AND THEN** ordinary mailbox-skill discovery and prompting depend only on the visible `skills/mailbox/...` mailbox subtree

### Requirement: Runtime-owned mailbox skill projection separates gateway operations from transport-specific guidance and uses Houmao-owned skill naming
The system SHALL project a common runtime-owned mailbox skill for shared gateway mailbox operations into every mailbox-enabled session in addition to the active transport-specific mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible mailbox subtree so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

That common skill SHALL live under the visible mailbox subtree alongside transport skills and SHALL be available at `skills/mailbox/houmao-email-via-agent-gateway/` for current adapters whose skill destination is `skills`.

The common gateway skill SHALL:
- use `SKILL.md` as a short index rather than a monolithic operation manual,
- publish operation-specific subdocuments for live discovery, check, read, send, reply, and mark-read behavior,
- publish explicit curl-first endpoint references for the shared `/v1/mail/*` surface,
- direct agents to discover the live gateway endpoint through `pixi run houmao-mgr agents mail resolve-live`,
- act as the default installed runtime-owned procedure for attached shared-mailbox work when a live gateway facade is available.

Transport-specific mailbox skills such as `houmao-email-via-filesystem` and `houmao-email-via-stalwart` SHALL remain projected and SHALL narrow their ordinary guidance to transport validation, transport-specific context, and fallback behavior when the gateway facade is unavailable.

#### Scenario: Mailbox-enabled session receives both gateway and transport runtime-owned skills
- **WHEN** the runtime starts a mailbox-enabled session
- **THEN** it projects `skills/mailbox/houmao-email-via-agent-gateway/` into the active skill destination
- **AND THEN** it also projects the runtime-owned mailbox skill for the active transport
- **AND THEN** the agent can discover both skills from the visible mailbox subtree without relying on hidden `.system` entries

#### Scenario: Houmao-owned mailbox skill naming requires explicit `houmao` invocation
- **WHEN** a runtime-owned mailbox skill is intended to be triggered through agent instructions
- **THEN** that skill uses a `houmao-<skillname>` name
- **AND THEN** the instruction text includes the keyword `houmao` when it intends to trigger that Houmao-owned skill
- **AND THEN** ordinary non-Houmao wording does not rely on implicit activation of the Houmao-owned skill

#### Scenario: Gateway mailbox skill uses action subdocuments instead of one packed instruction file
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md`
- **THEN** that entry document points the agent at action-specific subdocuments for `resolve-live`, `check`, `read`, `send`, `reply`, and `mark-read`
- **AND THEN** it does not pack the full operation guidance only into the top-level `SKILL.md`

#### Scenario: Gateway mailbox skill documents curl-first mailbox operations
- **WHEN** an agent needs to perform ordinary shared mailbox work through the live gateway facade
- **THEN** the runtime-owned gateway skill provides explicit curl examples for `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state`
- **AND THEN** the skill treats those explicit endpoint calls as the ordinary attached-session workflow once `gateway.base_url` is available

#### Scenario: Projected gateway skill is treated as installed operational guidance
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-email-via-agent-gateway` skill is already projected into that session
- **AND THEN** notifier and other runtime-owned guidance may instruct the agent to use that installed skill directly for the current mailbox turn

#### Scenario: Transport-specific mailbox skill narrows to transport context and fallback
- **WHEN** an agent opens `skills/mailbox/houmao-email-via-filesystem/SKILL.md` or `skills/mailbox/houmao-email-via-stalwart/SKILL.md`
- **THEN** that transport skill explains transport-specific constraints, references, and no-gateway fallback behavior
- **AND THEN** it points the agent at `skills/mailbox/houmao-email-via-agent-gateway/` for the shared `/v1/mail/*` operation contract instead of duplicating the entire gateway operation tutorial

### Requirement: Mailbox system skills use a stable resolver contract for current mailbox discovery
The system SHALL expose current mailbox discovery for projected mailbox system skills through `houmao-mgr agents mail resolve-live` rather than through mailbox-specific `AGENTSYS_MAILBOX_*` env bindings.

The resolver output SHALL provide the current mailbox binding in structured form, including the selected transport, principal id, mailbox address, transport-specific actionable fields derived from the durable session mailbox binding, and any validated live gateway mail-facade binding for the same session.

Projected mailbox system skills SHALL treat that resolver output as the supported mailbox-discovery contract and SHALL NOT require mailbox-specific shell export steps before ordinary mailbox work.

#### Scenario: Filesystem mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** the runtime starts an agent session with the filesystem mailbox transport
- **THEN** the projected mailbox system skill directs the agent to `houmao-mgr agents mail resolve-live`
- **AND THEN** the returned structured mailbox binding includes the current derived filesystem mailbox state needed for mailbox work without relying on `AGENTSYS_MAILBOX_*`

#### Scenario: Stalwart mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** the runtime starts an agent session with the `stalwart` mailbox transport
- **THEN** the projected mailbox system skill directs the agent to `houmao-mgr agents mail resolve-live`
- **AND THEN** the returned structured mailbox binding includes the current derived Stalwart mailbox state needed for mailbox work without relying on `AGENTSYS_MAILBOX_*`

### Requirement: Runtime-owned mailbox skills use the manager-owned live resolver as the ordinary gateway discovery contract
Projected runtime-owned mailbox skills SHALL direct agents to the manager-owned live resolver `pixi run houmao-mgr agents mail resolve-live` as the ordinary discovery path for the current mailbox binding and any attached gateway facade.

When that resolver returns a `gateway` object, runtime-owned mailbox skills SHALL treat `gateway.base_url` as the exact current endpoint prefix for shared `/v1/mail/*` mailbox operations.

Projected runtime-owned mailbox skills SHALL NOT present `python -m houmao.agents.mailbox_runtime_support resolve-live` as part of the ordinary mailbox operation workflow.

#### Scenario: Gateway mailbox skill obtains the current endpoint from `houmao-mgr agents mail resolve-live`
- **WHEN** an agent follows the runtime-owned gateway mailbox skill for attached shared mailbox work
- **THEN** the skill directs the agent to run `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** the agent obtains the exact live mailbox endpoint from the returned `gateway.base_url`

#### Scenario: Runtime-owned mailbox skills avoid direct Python-module resolver guidance
- **WHEN** an agent follows the projected mailbox skills for ordinary mailbox work
- **THEN** those skills use `pixi run houmao-mgr agents mail resolve-live` as the supported discovery contract
- **AND THEN** they do not instruct the agent to invoke `python -m houmao.agents.mailbox_runtime_support resolve-live` directly

### Requirement: Joined-session adoption installs Houmao-owned mailbox skills by default
When `houmao-mgr agents join` adopts a mailbox-enabled session, the join workflow SHALL install the Houmao-owned mailbox skill set into the adopted tool home by default so later runtime-owned prompts can rely on those skills being installed.

That joined-session installation SHALL:
- resolve the adopted tool home through the join workflow’s authoritative home-resolution path,
- project Houmao-owned mailbox skills only under reserved `houmao-<skillname>` paths in the adapter’s skill destination,
- preserve unrelated user-authored skill directories,
- fail explicitly when default installation is required but the target skill destination cannot be resolved or updated safely.

The join workflow MAY expose an explicit operator opt-out for Houmao-owned mailbox skill installation. When that opt-out is used, later runtime-owned mailbox prompts and docs SHALL NOT assume those skills are installed for that joined session.

#### Scenario: Joined mailbox-enabled session receives Houmao-owned mailbox skills by default
- **WHEN** an operator uses `houmao-mgr agents join` to adopt a mailbox-enabled session without opting out of Houmao skill installation
- **THEN** the join workflow projects the Houmao-owned mailbox skills into the adopted tool home under the adapter’s skill destination
- **AND THEN** later runtime-owned mailbox and gateway prompts may rely on those installed skill paths for that joined session

#### Scenario: Join preserves unrelated user-authored skills
- **WHEN** `houmao-mgr agents join` installs Houmao-owned mailbox skills into an adopted tool home
- **THEN** it writes only to reserved Houmao-owned mailbox skill paths
- **AND THEN** it does not delete or overwrite unrelated user-authored non-Houmao skill directories in that same skill destination

#### Scenario: Join fails closed when required Houmao-owned skill installation cannot complete
- **WHEN** `houmao-mgr agents join` is using default Houmao mailbox skill installation
- **AND WHEN** the adopted tool home or skill destination cannot be resolved or updated safely
- **THEN** the join command fails explicitly
- **AND THEN** it does not publish a managed session whose later runtime prompts would assume missing Houmao-owned mailbox skills

#### Scenario: Explicit join opt-out disables the installed-skill assumption
- **WHEN** an operator uses the explicit opt-out for Houmao mailbox skill installation during `houmao-mgr agents join`
- **THEN** the join workflow may continue without projecting those Houmao-owned mailbox skills
- **AND THEN** later runtime-owned mailbox prompts for that joined session do not assume the Houmao-owned mailbox skills are installed

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, projected mailbox system skills SHALL resolve current mailbox bindings through the runtime-owned live resolver exposed by `houmao-mgr agents mail resolve-live` rather than relying on the provider process's inherited mailbox env snapshot, mailbox-specific tmux env, or a direct Python-module entrypoint.

That live resolver SHALL:

- support same-session discovery when selectors are omitted inside the owning managed tmux session,
- use `AGENTSYS_MANIFEST_PATH` as the primary current-session discovery source with `AGENTSYS_AGENT_ID` as fallback,
- derive current mailbox state from the durable session mailbox binding instead of from targeted mailbox tmux env keys,
- surface transport-specific actionable mailbox fields needed for current mailbox work,
- surface the current validated gateway mail-facade binding for the session when a live gateway is attached,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

When a live gateway is attached, the resolver SHALL return the exact current `gateway.base_url` needed for attached shared-mailbox work.

#### Scenario: Filesystem mailbox skill observes late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the durable session mailbox binding
- **THEN** the projected mailbox system skill resolves the current mailbox binding through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill observes the refreshed filesystem mailbox state without requiring provider relaunch or mailbox-specific tmux env refresh

#### Scenario: Attached mailbox skill resolves the live gateway mail facade through `houmao-mgr agents mail`
- **WHEN** a tmux-backed mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** `houmao-mgr agents mail resolve-live` returns both the current mailbox binding and the validated live gateway mail-facade binding for that same session
- **AND THEN** the projected mailbox system skill can obtain the exact current gateway `base_url` for attached mailbox work without scraping tmux env or guessing a default port

#### Scenario: Stalwart no-gateway mailbox work uses the live resolver instead of stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current binding set through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill uses the current mailbox binding returned by that manager-owned discovery surface rather than assuming the provider process inherited still-current values at launch

### Requirement: Runtime-owned mailbox skill guidance keeps tmux integration behind the runtime-owned helper boundary
Projected mailbox system skills for tmux-backed sessions SHALL keep raw tmux integration details behind the runtime-owned helper boundary exposed through `houmao-mgr`.

The skill guidance SHALL NOT require the agent to:

- list all tmux session environment variables,
- guess which tmux session to inspect,
- parse raw `show-environment` output structure,
- parse mailbox binding state directly from the session manifest when the runtime-owned helper is available,
- invoke `python -m houmao.agents.mailbox_runtime_support ...` directly as part of ordinary mailbox work.

#### Scenario: Filesystem mailbox skill does not ask the agent to scrape tmux state or call a Python module directly
- **WHEN** a tmux-backed filesystem mailbox session uses the projected mailbox system skill for mailbox work
- **THEN** that skill points the agent at `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill does not instruct the agent to enumerate unrelated tmux environment state or invoke a direct Python-module resolver entrypoint

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade
When a live loopback gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL treat that shared gateway facade as the default routine action surface for ordinary mailbox work.

Projected mailbox system skills for both filesystem and `stalwart` transports SHALL present that default structurally: resolve current mailbox state through `houmao-mgr agents mail resolve-live`, use gateway HTTP when it is available, and fall back to `houmao-mgr agents mail ...` when it is not.

For this change, ordinary mailbox work includes:

- checking unread mail,
- sending one new message,
- replying to one existing message,
- marking one processed message read.

When projected mailbox skills use the `houmao-mgr agents mail ...` fallback path, they SHALL preserve the manager command's authority-aware result contract:

- `authoritative: true` means Houmao verified the mailbox outcome through manager-owned or gateway-backed execution,
- `authoritative: false` means Houmao only submitted the mailbox request through a TUI-mediated fallback path and separate verification is required.

When projected mailbox skills expose thin tmux-session-local shell helpers, those helpers SHALL delegate only to gateway HTTP or `houmao-mgr agents mail ...` rather than to direct Python-module entrypoints or mailbox-owned scripts.

For attached filesystem sessions, projected mailbox system skills SHALL NOT present direct mailbox-owned Python scripts as the ordinary no-gateway fallback path for those routine actions.

For attached `stalwart` sessions, projected mailbox system skills SHALL NOT present direct Python-module mailbox discovery as the ordinary no-gateway fallback path for those routine actions.

#### Scenario: Attached mailbox session uses the shared gateway facade when available
- **WHEN** a mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** the projected mailbox system skill resolves the current gateway endpoint through `houmao-mgr agents mail resolve-live`
- **AND THEN** the skill directs the agent to use gateway HTTP for the shared mailbox operation instead of reasoning about transport details directly

#### Scenario: Mailbox session without gateway falls back to `houmao-mgr agents mail`
- **WHEN** a mailbox-enabled session has no live shared gateway mailbox facade
- **THEN** the projected mailbox system skill directs the agent to use `houmao-mgr agents mail ...` for routine mailbox work
- **AND THEN** the fallback remains manager-owned and transport-neutral from the agent's perspective

#### Scenario: Non-authoritative manager fallback result triggers explicit verification
- **WHEN** a projected mailbox system skill uses `houmao-mgr agents mail send ...` or `reply ...`
- **AND WHEN** that command returns `authoritative: false`
- **THEN** the skill treats the result as submission-only rather than verified mailbox success
- **AND THEN** the skill uses `houmao-mgr agents mail check`, `status`, or transport-owned mailbox state to verify the requested outcome before assuming the mailbox mutation completed

#### Scenario: Thin shell helpers stay wrappers over supported surfaces
- **WHEN** a projected mailbox skill provides a shell helper for tmux-session-local mailbox work
- **THEN** that helper wraps `houmao-mgr agents mail resolve-live`, gateway HTTP, or `houmao-mgr agents mail ...`
- **AND THEN** it does not become a second canonical mailbox contract with independent transport logic

### Requirement: Filesystem mailbox system skills instruct agents to consult shared mailbox rules first
The system SHALL require the projected filesystem mailbox system skill to present shared mailbox `rules/` as mailbox-local policy guidance for agents rather than as an executable mutation contract.

That policy guidance MAY include markdown instructions about:

- message formatting,
- local reply or subject conventions,
- mailbox-local etiquette,
- other presentation or workflow hints specific to that mailbox.

The skill SHALL NOT present mailbox `rules/` as requiring the agent to execute mailbox-owned Python helper scripts for ordinary send, reply, check, or mark-read work.

#### Scenario: Filesystem mailbox skill treats mailbox-local rules as policy guidance
- **WHEN** an agent uses the projected filesystem mailbox system skill for mailbox reads or writes
- **THEN** that skill may direct the agent to consult shared mailbox `rules/` for mailbox-local policy guidance
- **AND THEN** the skill does not treat mailbox `rules/` as an executable mutation contract for ordinary mailbox operations

### Requirement: Filesystem mailbox system skills instruct agents to mark processed mail read explicitly
The system SHALL require the projected filesystem mailbox system skill to distinguish between discovering unread mail and marking a message read after processing.

That skill SHALL instruct agents to mark a message read only after the agent has actually processed that message successfully.

When the agent is using gateway HTTP, the skill SHALL direct the agent to `POST /v1/mail/state`.

When the agent is using the manager-owned fallback path, the skill SHALL direct the agent to `houmao-mgr agents mail mark-read`.

The skill SHALL NOT instruct agents to mark a message read merely because unread mail was detected or because a reminder prompt mentioned the message.

#### Scenario: Agent marks processed message read through the selected manager or gateway surface
- **WHEN** an agent finishes processing an unread mailbox message successfully
- **THEN** the projected mailbox system skill instructs the agent to mark that message read through `POST /v1/mail/state` when gateway HTTP is in use or `houmao-mgr agents mail mark-read` when the manager fallback path is in use
- **AND THEN** the agent does not treat message discovery or reminder prompts as implicit read-state mutation

#### Scenario: Non-authoritative mark-read fallback still requires verification
- **WHEN** an agent uses `houmao-mgr agents mail mark-read` through a manager fallback path
- **AND WHEN** that command returns `authoritative: false`
- **THEN** the projected mailbox system skill treats the result as submission-only rather than verified read-state mutation
- **AND THEN** the agent verifies read state through a follow-up mailbox check or transport-owned state before assuming the message is now read
