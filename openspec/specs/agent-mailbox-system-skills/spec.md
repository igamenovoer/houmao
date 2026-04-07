## Purpose
Define the runtime-owned mailbox system-skill contract, including env bindings, projection behavior, and shared-mailbox guidance across mailbox transports.
## Requirements
### Requirement: Runtime-owned mailbox system skills are never copied into launched project content
Runtime-owned Houmao mailbox system skills SHALL remain runtime-home assets under the active tool skill destination and SHALL NOT be copied into copied project worktrees, generated demo project content, or other launched project content merely to make ordinary mailbox prompting succeed.

Maintained runtime and demo workflows SHALL treat project content and runtime-owned mailbox skills as separate surfaces:
- copied project content remains ordinary work content,
- runtime-owned mailbox skills remain installed in the tool-native runtime-home skill destination,
- ordinary mailbox prompting relies on the installed runtime-home skill surface rather than on copied project-local mailbox skill mirrors.

#### Scenario: Supported demo prepares a copied project for a mailbox-enabled session
- **WHEN** a maintained demo prepares a copied project worktree for a mailbox-enabled Claude, Codex, or Gemini session
- **THEN** the copied project does not receive Houmao runtime-owned mailbox skills as project content
- **AND THEN** the mailbox skill set remains available only through the tool-native runtime-home skill destination

#### Scenario: Runtime-owned mailbox skills remain separate from copied work content
- **WHEN** an agent session includes both copied project files and runtime-owned mailbox skills
- **THEN** the agent can use the installed mailbox skills without requiring a `project/skills` or worktree-local mailbox mirror
- **AND THEN** success of ordinary mailbox prompting does not depend on copied project-local `SKILL.md` files

### Requirement: Runtime-owned gateway email processing skill defines round-oriented notified email workflow
The system SHALL provide a projected runtime-owned mailbox skill `houmao-process-emails-via-gateway` that defines the workflow for processing gateway-notified unread emails in bounded rounds.

That workflow SHALL assume the current notifier round already provides the exact current gateway base URL needed for shared mailbox operations.

The workflow SHALL start by using the shared gateway mailbox API itself to inspect current mailbox state for the round, including listing unread mail through the shared `/v1/mail/*` surface.

That workflow SHALL start from current unread metadata such as sender identity, subject, timestamps, and opaque message references before deciding which unread emails are relevant for the current round.

The workflow MAY use additional non-body metadata or lightweight gateway-visible detail to shortlist candidate emails, but it SHALL treat message-body inspection as a later step rather than as part of the initial reminder summary.

Once the workflow selects one or more task-relevant emails for the current round, it SHALL direct the agent to inspect all selected emails needed to decide and complete the work for that round.

The workflow SHALL direct the agent to perform the requested work before mutating read state.

The workflow SHALL direct the agent to mark only the successfully processed emails read at the end of that round.

The workflow SHALL leave unread emails that were deferred, skipped, or not completed in the unread set for later notifier-driven rounds.

After the agent completes the selected round of work, the workflow SHALL direct the agent to stop and wait for the next notifier wake-up rather than proactively checking for new mail on its own.

The workflow SHALL treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside the agent’s concern for that completed round.

If the gateway base URL is missing from the notifier round context, the workflow SHALL treat that as a contract failure for the current round rather than silently switching to manager-based rediscovery.

#### Scenario: Metadata-first triage follows an agent-run unread listing step
- **WHEN** the agent begins one notifier-driven email processing round
- **THEN** the workflow directs the agent to inspect current unread mail through the shared gateway mailbox API
- **AND THEN** the workflow starts triage from current unread metadata such as sender, subject, timestamps, and opaque references
- **AND THEN** the agent does not need notifier-rendered unread summaries to start the round

#### Scenario: Selected round-relevant emails are fully inspected before action
- **WHEN** the workflow selects one or more unread emails as relevant to the current round
- **THEN** the workflow directs the agent to inspect all selected emails needed to decide and perform the work for that round
- **AND THEN** the workflow does not require unrelated unread emails to be fully inspected first

#### Scenario: Successfully processed emails are marked read while deferred emails remain unread
- **WHEN** the agent completes work for some but not all unread emails during one round
- **THEN** the workflow directs the agent to mark only the successfully processed emails read
- **AND THEN** deferred or unfinished emails remain unread for later notifier-driven handling

#### Scenario: Completed round waits for the next notification
- **WHEN** the agent finishes the selected work for one email-processing round
- **THEN** the workflow directs the agent to stop rather than proactively polling for more mail
- **AND THEN** the agent waits for the next notifier-triggered wake-up to begin another round

#### Scenario: Missing base URL is treated as a notifier-round contract failure
- **WHEN** the agent begins the notifier-driven workflow for one round
- **AND WHEN** the current round context does not provide the gateway base URL
- **THEN** the workflow does not silently switch to manager-based rediscovery for that round
- **AND THEN** the missing gateway bootstrap is treated as a contract failure for the current wake-up

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

### Requirement: Joined-session adoption installs Houmao-owned mailbox skills by default
When `houmao-mgr agents join` adopts a mailbox-enabled session, the join workflow SHALL install the current Houmao-owned system-skill selection resolved from the packaged catalog’s managed-join auto-install set list for the adopted tool home by default so later runtime-owned prompts can rely on the current Houmao-owned mailbox skills being installed.

That joined-session installation SHALL:
- resolve the adopted tool home through the join workflow’s authoritative home-resolution path,
- invoke the shared Houmao system-skill installer rather than a mailbox-only installation code path,
- include the current Houmao-owned mailbox skills in the resolved managed-join auto-install selection for the adopted tool,
- project Houmao-owned mailbox skills only under reserved `houmao-<skillname>` paths in the visible skill destination for that tool,
- preserve unrelated user-authored skill directories,
- fail explicitly when default installation is required but the target skill destination cannot be resolved or updated safely.

The join workflow MAY expose an explicit operator opt-out for default Houmao-owned skill installation. When that opt-out is used, later runtime-owned mailbox prompts and docs SHALL NOT assume the current Houmao-owned mailbox skills are installed for that joined session.

#### Scenario: Joined mailbox-enabled session receives the managed-join mailbox skill set by default
- **WHEN** an operator uses `houmao-mgr agents join` to adopt a mailbox-enabled session without opting out of Houmao skill installation
- **THEN** the join workflow installs the current Houmao-owned system-skill selection resolved from the managed-join auto-install set list into the adopted tool home
- **AND THEN** that resolved selection includes the current Houmao-owned mailbox skills needed for later runtime-owned mailbox prompts

#### Scenario: Join preserves unrelated user-authored skills
- **WHEN** `houmao-mgr agents join` installs the current Houmao-owned system-skill selection resolved from the managed-join auto-install set list into an adopted tool home
- **THEN** it writes only to reserved Houmao-owned skill paths for the current skill set
- **AND THEN** it does not delete or overwrite unrelated user-authored non-Houmao skill directories in that same skill destination

#### Scenario: Join fails closed when required default Houmao-owned skill installation cannot complete
- **WHEN** `houmao-mgr agents join` is using default Houmao-owned current-skill installation
- **AND WHEN** the adopted tool home or skill destination cannot be resolved or updated safely
- **THEN** the join command fails explicitly
- **AND THEN** it does not publish a managed session whose later runtime prompts would assume missing Houmao-owned mailbox skills

#### Scenario: Explicit join opt-out disables the installed-mailbox-skill assumption
- **WHEN** an operator uses the explicit opt-out for default Houmao-owned skill installation during `houmao-mgr agents join`
- **THEN** the join workflow may continue without projecting the current Houmao-owned mailbox skills
- **AND THEN** later runtime-owned mailbox prompts for that joined session do not assume the current Houmao-owned mailbox skills are installed

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, projected mailbox system skills SHALL resolve current mailbox bindings through the runtime-owned live resolver exposed by `houmao-mgr agents mail resolve-live` rather than relying on the provider process's inherited mailbox env snapshot, mailbox-specific tmux env, or a direct Python-module entrypoint.

That live resolver SHALL:

- support same-session discovery when selectors are omitted inside the owning managed tmux session,
- use `HOUMAO_MANIFEST_PATH` as the primary current-session discovery source with `HOUMAO_AGENT_ID` as fallback,
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

### Requirement: Runtime-owned mailbox system skills are available to launched agents through a unified Houmao mailbox surface
The system SHALL provide implemented mailbox access to agents through runtime-owned mailbox system skills projected from platform-owned templates rather than requiring role-authored mailbox skill content.

These mailbox system skills SHALL be projected into mailbox-enabled sessions in a discoverable non-hidden tool-native location under the active skill destination using the same active skill-destination contract as other projected skills.

For Claude sessions whose active skill destination root is `skills` under `CLAUDE_CONFIG_DIR`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `skills/mailbox/...`.

For Codex sessions whose active skill destination root remains `skills`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `skills/mailbox/...`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the mailbox system skill surface SHALL use top-level Houmao-owned skill directories rather than `.gemini/skills/mailbox/...`.

For every mailbox-enabled session, the top-level visible Houmao mailbox skill surface SHALL include:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The top-level installed mailbox skill names SHALL remain the same across supported mailbox transports, and transport-specific ordinary mailbox guidance SHALL be discovered inside `houmao-agent-email-comms` rather than through separate installed top-level skill directories.

Runtime-owned mailbox skills SHALL remain distinguishable from role-authored skills through reserved Houmao-owned skill names and tool-native projected paths.

The runtime SHALL NOT create a parallel hidden `.system/mailbox/...` mailbox skill tree for ordinary mailbox-skill discovery.

#### Scenario: Filesystem mailbox-enabled Claude agent receives the unified mailbox surface
- **WHEN** the runtime starts a Claude session with filesystem mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** `houmao-process-emails-via-gateway` and `houmao-agent-email-comms` are available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** filesystem-specific ordinary mailbox guidance is available through the unified skill rather than through a separate top-level filesystem mailbox skill

#### Scenario: Stalwart mailbox-enabled Claude agent receives the unified mailbox surface
- **WHEN** the runtime starts a Claude session with `stalwart` mailbox support enabled
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** `houmao-process-emails-via-gateway` and `houmao-agent-email-comms` are available through top-level Houmao-owned skill directories discoverable by Claude native skill lookup
- **AND THEN** Stalwart-specific ordinary mailbox guidance is available through the unified skill rather than through a separate top-level Stalwart mailbox skill

#### Scenario: Codex mailbox-enabled agent receives the unified mailbox surface
- **WHEN** the runtime starts a Codex mailbox-enabled session
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into the active skill destination
- **AND THEN** the mailbox skills are available through top-level Houmao-owned skill directories discoverable by Codex native skill lookup
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Gemini mailbox-enabled agent receives the unified mailbox surface
- **WHEN** the runtime starts a Gemini mailbox-enabled session
- **THEN** the runtime projects the mailbox system skill set for that session from platform-owned templates into `.gemini/skills/`
- **AND THEN** the mailbox skills are available through top-level Houmao-owned Gemini skill directories rather than through `.gemini/skills/mailbox/...`
- **AND THEN** those mailbox system skills are available to the agent without requiring the role or recipe to select or author a mailbox-specific skill manually

#### Scenario: Runtime-owned mailbox skills stay separate from role-authored skills
- **WHEN** an agent session includes both role-authored skills and runtime-owned mailbox system skills
- **THEN** runtime-owned mailbox skills remain distinguishable through reserved Houmao-owned skill names and tool-native projected paths
- **AND THEN** the agent can use those mailbox system skills without overriding or depending on role-authored skill content

#### Scenario: Hidden mailbox compatibility mirror is not projected
- **WHEN** the runtime projects mailbox system skills for a mailbox-enabled session
- **THEN** the runtime does not create a parallel hidden `.system/mailbox/...` mailbox skill tree for that session
- **AND THEN** Claude and Codex sessions do not rely on a parallel `skills/mailbox/...` compatibility mirror for ordinary mailbox-skill discovery
- **AND THEN** Gemini sessions do not rely on a parallel `.gemini/skills/mailbox/...` compatibility mirror for ordinary mailbox-skill discovery

### Requirement: Runtime-owned mailbox skill projection pairs a unified ordinary mailbox skill with the separate processing workflow
The system SHALL project a round-oriented runtime-owned mailbox workflow skill for gateway-notified email processing into every mailbox-enabled session in addition to a unified runtime-owned ordinary-mailbox skill.

Projected Houmao-owned mailbox skills SHALL use a `houmao-<skillname>` naming convention under the visible tool-native mailbox skill surface so runtime-owned Houmao skills are distinguishable from role-authored or third-party skill names.

That `houmao-<skillname>` convention SHALL also define the activation boundary for Houmao-owned skills: the instruction text must include the keyword `houmao` when it intends to trigger a Houmao-owned skill.

For Claude sessions whose active skill destination root is `skills`, the round-oriented workflow skill SHALL be available at `skills/houmao-process-emails-via-gateway/`.

For Claude sessions whose active skill destination root is `skills`, the unified ordinary-mailbox skill SHALL be available at `skills/houmao-agent-email-comms/`.

For Codex sessions whose active skill destination root remains `skills`, the round-oriented workflow skill SHALL be available at `skills/houmao-process-emails-via-gateway/`.

For Codex sessions whose active skill destination root remains `skills`, the unified ordinary-mailbox skill SHALL be available at `skills/houmao-agent-email-comms/`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the round-oriented workflow skill SHALL be available at `.gemini/skills/houmao-process-emails-via-gateway/`.

For Gemini sessions whose active skill destination root is `.gemini/skills`, the unified ordinary-mailbox skill SHALL be available at `.gemini/skills/houmao-agent-email-comms/`.

The round-oriented workflow skill SHALL:

- act as the default installed runtime-owned procedure for notifier-triggered shared mailbox processing rounds when a live gateway facade is available,
- assume the notifier round already provides the exact current gateway base URL,
- define gateway-API-first metadata triage, unread-listing, relevant-message selection, selective inspection, work execution, and post-success mark-read behavior for the current round,
- tell the agent to stop after the current round and wait for the next notification rather than proactively polling for more mail.

The unified ordinary-mailbox skill SHALL:

- remain the lower-level operational skill for live discovery, status, check, read, send, reply, and mark-read behavior,
- use a gateway base URL already present in prompt or context when that URL is available,
- fall back to `houmao-mgr agents mail resolve-live` only when the current gateway base URL cannot be determined from prompt or context,
- keep filesystem-specific and Stalwart-specific ordinary mailbox guidance as internal pages or references within the same skill package,
- support the round-oriented workflow skill rather than replacing it as the notifier-facing entrypoint.

The runtime SHALL NOT project separate top-level installed skill directories for `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, or `houmao-email-via-stalwart` once the unified ordinary-mailbox skill is in use.

#### Scenario: Claude mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Claude session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` and `skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** Claude can discover both skills through native skill discovery without relying on a mailbox namespace subtree
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Codex mailbox-enabled session receives the processing skill and unified ordinary-mailbox skill
- **WHEN** the runtime starts a mailbox-enabled Codex session
- **THEN** it projects `skills/houmao-process-emails-via-gateway/` and `skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** the agent can discover both skills through native skill discovery without relying on a mailbox namespace subtree or hidden `.system` entries
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Gemini mailbox-enabled session receives native top-level unified mailbox skills
- **WHEN** the runtime starts a mailbox-enabled Gemini session
- **THEN** it projects `.gemini/skills/houmao-process-emails-via-gateway/` and `.gemini/skills/houmao-agent-email-comms/` into the active skill destination
- **AND THEN** Gemini can discover both skills through native skill discovery without relying on a `mailbox/` namespace subtree
- **AND THEN** the runtime does not also project separate top-level gateway, filesystem, or Stalwart ordinary-mailbox skills

#### Scenario: Processing skill remains the notifier-round workflow entrypoint
- **WHEN** a mailbox-enabled session has the shared gateway mailbox facade available
- **THEN** the runtime-owned `houmao-process-emails-via-gateway` skill is already projected into that session through the tool-native visible mailbox skill surface
- **AND THEN** notifier prompts may instruct the agent to use that installed skill directly for the current mailbox round
- **AND THEN** ordinary mailbox actions within that round may rely on `houmao-agent-email-comms` as supporting material

#### Scenario: Unified ordinary-mailbox skill remains the operational reference
- **WHEN** an agent opens the installed `houmao-agent-email-comms` skill document from the visible mailbox skill surface for its tool
- **THEN** that entry document points the agent at internal action-specific or transport-specific subdocuments for resolver and mailbox-operation behavior
- **AND THEN** it does not replace `houmao-process-emails-via-gateway` as the notifier-facing entrypoint
- **AND THEN** it does not require a separate installed top-level transport skill for filesystem or Stalwart guidance

### Requirement: Unified ordinary-mailbox skill uses the manager-owned live resolver as the ordinary gateway discovery contract
Projected runtime-owned mailbox skills SHALL direct agents to the manager-owned live resolver `houmao-mgr agents mail resolve-live` only when current prompt or context does not already provide the exact current gateway base URL needed for shared `/v1/mail/*` mailbox operations.

When current prompt or context already provides the exact current gateway base URL, runtime-owned mailbox skills SHALL treat that URL as the authoritative endpoint prefix for the current mailbox work and SHALL NOT require redundant manager-based rediscovery.

When the manager-owned live resolver returns a `gateway` object, runtime-owned mailbox skills SHALL treat `gateway.base_url` as the exact current endpoint prefix for shared `/v1/mail/*` mailbox operations.

Projected runtime-owned mailbox skills SHALL NOT present `pixi run houmao-mgr agents mail resolve-live` as part of ordinary mailbox operation workflow.

Projected runtime-owned mailbox skills SHALL NOT present `python -m houmao.agents.mailbox_runtime_support resolve-live` as part of the ordinary mailbox operation workflow.

#### Scenario: Unified ordinary-mailbox skill obtains the current endpoint from prompt context when available
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context already provides the exact current gateway base URL
- **THEN** the skill uses that context-provided base URL as the endpoint prefix for `/v1/mail/*`
- **AND THEN** the agent does not need to rerun manager-based discovery first

#### Scenario: Unified ordinary-mailbox skill falls back to `houmao-mgr agents mail resolve-live`
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for attached shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context does not provide the exact current gateway base URL
- **THEN** the skill directs the agent to run `houmao-mgr agents mail resolve-live`
- **AND THEN** the agent obtains the exact live mailbox endpoint from the returned `gateway.base_url`

#### Scenario: Unified ordinary-mailbox skill avoids `pixi` and direct Python-module resolver guidance
- **WHEN** an agent follows the projected mailbox skills for ordinary mailbox work
- **THEN** those skills do not instruct the agent to use `pixi run houmao-mgr agents mail resolve-live`
- **AND THEN** they do not instruct the agent to invoke `python -m houmao.agents.mailbox_runtime_support resolve-live` directly

