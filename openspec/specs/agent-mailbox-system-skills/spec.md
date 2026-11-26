## Purpose
Define the runtime-owned mailbox system-skill contract, including env bindings, projection behavior, and shared-mailbox guidance across mailbox transports.
## Requirements
### Requirement: Runtime-owned mailbox system skills are never copied into launched project content
Runtime-owned Houmao mailbox system skills SHALL remain runtime-home assets under the active tool skill destination and SHALL NOT be copied into copied project worktrees, generated demo project content, or other launched project content merely to make ordinary mailbox prompting succeed.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
The system SHALL provide a projected runtime-owned mailbox skill `houmao-process-emails-via-gateway` that defines the workflow for processing gateway-notified Inbox work in bounded rounds.

The `houmao-process-emails-via-gateway/SKILL-MAIN.md` router and `commands/process-round.md` SHALL require the notifier prompt's exact `gateway_base_url`, explicit `offline|online` channel, and `expected_binding_id` for the current round.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The workflow SHALL start by using the shared gateway mailbox API itself to inspect current mailbox state for the round, including listing Inbox mail according to the prompt's notification mode through the shared `/v1/mail/*` surface.

That workflow SHALL start from current mode-eligible metadata such as sender identity, subject, timestamps, and opaque message references before deciding which listed emails are relevant for the current round.

The workflow MAY use additional non-body metadata or lightweight gateway-visible detail to shortlist candidate emails, but it SHALL treat message-body inspection as a later step rather than as part of the initial reminder summary.

Once the workflow selects one or more task-relevant emails for the current round, it SHALL direct the agent to inspect all selected emails needed to decide and complete the work for that round.

Where inspection must leave read state intact until work succeeds, the workflow SHALL use non-mutating `peek`. Deferred or unfinished mail SHALL remain unread in `unread_only` rounds when it started unread.

In an `unread_only` round, the agent SHALL mark successfully processed mail read if it remains unread and the selected binding supports that state change. The workflow SHALL keep read-state changes separate from filing.

The workflow SHALL leave unread emails that were deferred, skipped, or not completed in the unread set for later notifier-driven rounds.

After the agent completes the selected round of work, the workflow SHALL direct the agent to stop and wait for the next notifier wake-up rather than proactively checking for new mail on its own.

The workflow SHALL treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside the agent’s concern for that completed round.

Missing notifier coordinates or a stale binding SHALL end the round with its contract or binding error. The workflow SHALL keep the selected gateway, channel, and binding for all effects during the round.

`commands/process-round.md` SHALL confirm required replies through the compact write receipt and use `peek` on the same channel and binding for any needed read-only reconciliation. On `mail.reply` or `mail.attachment.owner_file` refusal, it SHALL report the exact refusal and leave the message open. A submission-only or uncertain required reply SHALL leave the work open until confirmed.

`references/reply-hardening.md` SHALL preserve optional, lowest-priority `one_off` reminder guidance. It SHALL retain the exact notifier coordinates and reply reference and require a read-only reply-state check before retrying. The round SHALL remove unfired reply reminders after a confirmed ordinary reply and use the binding's authorized completion path for successfully completed messages.

#### Scenario: Metadata-first triage follows an agent-run unread listing step
- **WHEN** the agent begins a notifier-driven email processing round in `unread_only` mode
- **THEN** the workflow directs the agent to inspect current unread mail through the shared gateway mailbox API
- **AND THEN** the workflow starts triage from current unread metadata such as sender, subject, timestamps, and opaque references
- **AND THEN** the agent does not need notifier-rendered unread summaries to start the round

#### Scenario: Selected round-relevant emails are fully inspected before action
- **WHEN** the workflow selects one or more unread emails as relevant to the current round
- **THEN** the workflow directs the agent to inspect all selected emails needed to decide and perform the work for that round
- **AND THEN** the workflow does not require unrelated unread emails to be fully inspected first

#### Scenario: Successfully processed emails are marked read while deferred emails remain unread
- **WHEN** the agent completes work for some but not all unread emails during an `unread_only` round
- **THEN** the workflow directs the agent to mark only successfully processed emails that remain unread when marking is supported
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

#### Scenario: A Required Reply Remains Unconfirmed or Is Refused

- **WHEN** a required reply produces a submission-only receipt, remains uncertain, or is refused
- **THEN** the round reports the result and leaves the message open while the reply remains unconfirmed
- **AND THEN** any reply-state check stays on the original channel and binding and any later reply still requires the same authority

### Requirement: Mailbox system skills use a stable resolver contract for current mailbox discovery
Projected mailbox skills SHALL discover current mail state through the scoped `houmao-mgr agents self mail resolve-live` or explicitly targeted `agents single` equivalent. The result SHALL expose both optional bindings, owner/channel/binding scope, revisions, canonical mail identity, safe operational information, and the current validated gateway endpoint. It SHALL not depend on inherited mailbox environment snapshots or expose credential material.

#### Scenario: Filesystem mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** an agent resolves its configured offline mail
- **THEN** it receives the current offline binding and selected registry context
- **AND THEN** it can use the supported facade without scraping tmux environment or raw manifests

#### Scenario: Stalwart mailbox skill resolves current mailbox state through the manager-owned resolver
- **WHEN** an agent resolves its configured Stalwart online mail
- **THEN** it receives the online provider identity and current binding revision alongside any offline binding
- **AND THEN** ordinary mailbox work does not require receiving a password or credential-file path

### Requirement: Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver
For tmux-backed managed sessions, projected mailbox system skills SHALL resolve current mailbox bindings through the runtime-owned live resolver exposed by `houmao-mgr agents self mail resolve-live` rather than relying on the provider process's inherited mailbox env snapshot, mailbox-specific tmux env, or a direct Python-module entrypoint.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That live resolver SHALL:

- support same-session discovery when selectors are omitted inside the owning managed tmux session,
- use `HOUMAO_MANIFEST_PATH` as the primary current-session discovery source with `HOUMAO_AGENT_ID` as fallback,
- derive current mailbox state from the durable session mailbox binding instead of from targeted mailbox tmux env keys,
- surface safe current information for both optional bindings, their scopes and revisions, without credential material,
- surface the current validated gateway mail-facade binding for the session when a live gateway is attached,
- avoid requiring the agent to parse raw manifest JSON or enumerate unrelated tmux env vars manually.

When a live gateway is attached, the resolver SHALL return the exact current `gateway.base_url` needed for attached shared-mailbox work.

#### Scenario: Filesystem mailbox skill observes late-registered binding without provider relaunch
- **WHEN** a tmux-backed filesystem mailbox session receives a mailbox task after late registration updated the durable session mailbox binding
- **THEN** the projected mailbox system skill resolves the current mailbox binding through `houmao-mgr agents self mail resolve-live`
- **AND THEN** the skill observes the refreshed filesystem mailbox state without requiring provider relaunch or mailbox-specific tmux env refresh

#### Scenario: Attached mailbox skill resolves the live gateway mail facade through `houmao-mgr agents mail`
- **WHEN** a tmux-backed mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** `houmao-mgr agents self mail resolve-live` returns both the current mailbox binding and the validated live gateway mail-facade binding for that same session
- **AND THEN** the projected mailbox system skill can obtain the exact current gateway `base_url` for attached mailbox work without scraping tmux env or guessing a default port

#### Scenario: Stalwart no-gateway mailbox work uses the live resolver instead of stale process env
- **WHEN** a tmux-backed `stalwart` mailbox session performs mailbox work without a live gateway mailbox facade
- **THEN** the projected mailbox system skill resolves the current binding set through `houmao-mgr agents self mail resolve-live`
- **AND THEN** the skill uses the current mailbox binding returned by that manager-owned discovery surface rather than assuming the provider process inherited still-current values at launch

### Requirement: Runtime-owned mailbox skill guidance keeps tmux integration behind the runtime-owned helper boundary
Projected mailbox system skills for tmux-backed sessions SHALL keep raw tmux integration details behind the runtime-owned helper boundary exposed through `houmao-mgr`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill guidance SHALL NOT require the agent to:

- list all tmux session environment variables,
- guess which tmux session to inspect,
- parse raw `show-environment` output structure,
- parse mailbox binding state directly from the session manifest when the runtime-owned helper is available,
- invoke `python -m houmao.agents.mailbox_runtime_support ...` directly as part of ordinary mailbox work.

#### Scenario: Filesystem mailbox skill does not ask the agent to scrape tmux state or call a Python module directly
- **WHEN** a tmux-backed filesystem mailbox session uses the projected mailbox system skill for mailbox work
- **THEN** that skill points the agent at `houmao-mgr agents self mail resolve-live`
- **AND THEN** the skill does not instruct the agent to enumerate unrelated tmux environment state or invoke a direct Python-module resolver entrypoint

### Requirement: Projected mailbox system skills keep routine attached-session actions on the shared gateway facade

When a live gateway exposes the shared `/v1/mail/*` mailbox surface for a mailbox-enabled session, the projected mailbox system skills SHALL use the shared gateway facade for ordinary mailbox work.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Projected mailbox system skills for filesystem and `stalwart` SHALL resolve current mailbox state through `houmao-mgr agents self mail resolve-live` and use a runtime-owned client for live calls. Managed self commands SHALL sign the challenge with the current generation's key. Scoped admins SHALL use an explicit signing key. Skill text, resolver output, and shell examples SHALL omit keys, proof material, and private credential references.

The skills SHALL use the existing separately authorized manager path for ordinary mailbox work when the live gateway is absent. Ordinary mailbox calls through this path SHALL respect the backend's placement restrictions on a protected binding. An admission refusal or unavailable policy from a protected gateway SHALL end the request. Lifecycle actions SHALL retain the selected channel and expected binding. Manager lifecycle commands SHALL include `--channel offline|online`.

Ordinary mailbox work includes:

- checking unread mail
- sending one new message
- replying to one existing message
- marking one processed message read

When projected mailbox skills use `houmao-mgr agents self mail ...` without a live gateway, they SHALL preserve the manager command's authority-aware result:

- `authoritative: true` means Houmao verified the mailbox outcome through manager-owned or gateway-backed execution
- `authoritative: false` means Houmao submitted the request through a TUI-mediated path and separate verification is required

Thin session-local helpers SHALL delegate to the runtime-owned gateway client or maintained `houmao-mgr` mailbox commands. For attached filesystem and `stalwart` sessions, the routine fallback SHALL be manager-owned and transport-neutral.

#### Scenario: Attached mailbox session uses the shared gateway facade when available

- **WHEN** a mailbox-enabled session has a live attached gateway exposing `/v1/mail/*`
- **THEN** the skill resolves the current endpoint through `houmao-mgr agents self mail resolve-live`
- **AND THEN** its runtime-owned client signs the request challenge with the current generation's self key

#### Scenario: Mailbox session without gateway falls back to `houmao-mgr agents mail`

- **WHEN** a mailbox-enabled session has no live shared gateway mailbox facade and the caller has existing manager authority
- **THEN** the skill directs the agent to use `houmao-mgr agents self mail ...` for routine mailbox work
- **AND THEN** the manager uses the established transport-neutral path

#### Scenario: Protected gateway refuses mailbox access

- **WHEN** the runtime-owned client receives an authentication or authorization failure for a protected mailbox operation
- **THEN** it surfaces the refusal as the request outcome
- **AND THEN** neither a local transport nor an admin binding is used as fallback

#### Scenario: Non-authoritative manager fallback result triggers explicit verification

- **WHEN** the manager returns `authoritative: false` for routine send or reply
- **THEN** the skill treats the result as submission-only
- **AND THEN** it verifies the result through supported mailbox state before treating delivery as complete

#### Scenario: Thin shell helpers stay wrappers over supported surfaces

- **WHEN** a projected mailbox skill provides a shell helper for local gateway work
- **THEN** that helper delegates to the runtime-owned client or maintained scoped mailbox commands
- **AND THEN** the same target and credential selection governs the operation

### Requirement: Filesystem mailbox system skills instruct agents to consult shared mailbox rules first
The system SHALL require the projected filesystem mailbox system skill to present shared mailbox `rules/` as mailbox-local policy guidance for agents rather than as an executable mutation contract.

That policy guidance MAY include markdown instructions about:

- message formatting,
- local reply or subject conventions,
- mailbox-local etiquette,
- other presentation or workflow hints specific to that mailbox.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL NOT present mailbox `rules/` as requiring the agent to execute mailbox-owned Python helper scripts for ordinary list, peek, read, send, post, reply, mark, move, or archive work.

#### Scenario: Filesystem mailbox skill treats mailbox-local rules as policy guidance
- **WHEN** an agent uses the projected filesystem mailbox system skill for mailbox reads or writes
- **THEN** that skill may direct the agent to consult shared mailbox `rules/` for mailbox-local policy guidance
- **AND THEN** the skill does not treat mailbox `rules/` as an executable mutation contract for ordinary mailbox operations

### Requirement: Runtime-owned mailbox system skills are available to launched agents through a unified Houmao mailbox surface
Mailbox-enabled managed homes SHALL receive the agent pack rather than separate top-level mailbox skills.

The one public mailbox-capable surface SHALL be `houmao-agent-entrypoint`. Its protected `houmao-shared-routines` composition SHALL include `houmao-agent-email-comms` for ordinary mailbox work and `houmao-process-emails-via-gateway` for notified unread-mail rounds. Transport-specific ordinary guidance SHALL remain private to the ordinary mailbox routine.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The runtime SHALL NOT project the protected mailbox logical ids as top-level skill directories, SHALL NOT require role-authored mailbox skill content, and SHALL NOT create a parallel hidden mailbox compatibility tree.

#### Scenario: Mailbox-enabled Codex agent receives unified nested surface
- **WHEN** Houmao launches a mailbox-enabled Codex managed agent with default system skills
- **THEN** the Codex skill root contains top-level `houmao-agent-entrypoint`
- **AND THEN** both protected mailbox routines are available beneath its shared-routines mount
- **AND THEN** neither mailbox routine appears as a top-level peer

#### Scenario: Role-authored skills remain independent
- **WHEN** a managed home includes role-authored skills and the agent pack
- **THEN** mailbox behavior remains owned by the protected Houmao routines
- **AND THEN** installation preserves unrelated role-authored skill paths

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
The agent pack's protected composition SHALL include two distinct mailbox logical routines.

`houmao-process-emails-via-gateway` SHALL own notifier-triggered, bounded Inbox work rounds. Its `process-round` workflow SHALL use prompt-supplied gateway coordinates, perform metadata-first triage, inspect selected messages, finish work and any required replies, follow the binding's authorized completion path, and stop for the next notifier wake-up.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

`houmao-agent-email-comms` SHALL own ordinary discovery, status, list, peek, read, send, post, reply, mark, move, and archive behavior where the selected binding supports each operation. It SHALL prefer a gateway base URL already present in prompt or route context and SHALL use the manager-owned live resolver only when current context lacks that URL. Filesystem and Stalwart guidance SHALL remain internal to this protected routine.

The public agent entrypoint SHALL route to the correct protected routine from operation and notifier context. It SHALL NOT project transport-specific or old compatibility mailbox skills as top-level directories.

#### Scenario: Notified round chooses processing routine
- **WHEN** verified agent context contains a notifier-triggered unread-mail round and gateway URL
- **THEN** the agent entrypoint routes to protected `houmao-process-emails-via-gateway`
- **AND THEN** the round stops after processing the selected work and performing any ordinary archive the binding supports

#### Scenario: Ordinary send chooses email-comms routine
- **WHEN** a verified managed agent asks to send or reply outside a notifier round
- **THEN** the agent entrypoint routes to protected `houmao-agent-email-comms`
- **AND THEN** the routine applies the ordinary mailbox discovery and transport guidance

#### Scenario: Top-level mailbox compatibility paths stay absent
- **WHEN** the agent pack is installed
- **THEN** the tool-native skill root does not contain top-level `houmao-process-emails-via-gateway`, `houmao-agent-email-comms`, or transport-specific mailbox compatibility skills

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
Projected runtime-owned mailbox skills SHALL direct agents to the manager-owned live resolver `houmao-mgr agents self mail resolve-live` only when current prompt or context does not already provide the exact current gateway base URL needed for shared `/v1/mail/*` mailbox operations.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When current prompt or context already provides the exact current gateway base URL, runtime-owned mailbox skills SHALL treat that URL as the authoritative endpoint prefix for the current mailbox work and SHALL NOT require redundant manager-based rediscovery.

When the manager-owned live resolver returns a `gateway` object, runtime-owned mailbox skills SHALL treat `gateway.base_url` as the exact current endpoint prefix for channel-selected `/v1/mail/{channel}/...` mailbox operations. The routine SHALL preserve the selected channel and expected binding ID.

Projected runtime-owned mailbox skills SHALL NOT present `pixi run houmao-mgr agents self mail resolve-live` as part of ordinary mailbox operation workflow.

Projected runtime-owned mailbox skills SHALL NOT present `python -m houmao.agents.mailbox_runtime_support resolve-live` as part of the ordinary mailbox operation workflow.

#### Scenario: Unified ordinary-mailbox skill obtains the current endpoint from prompt context when available
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context already provides the exact current gateway base URL
- **THEN** the skill uses that context-provided base URL as the endpoint prefix for `/v1/mail/*`
- **AND THEN** the agent does not need to rerun manager-based discovery first

#### Scenario: Unified ordinary-mailbox skill falls back to `houmao-mgr agents mail resolve-live`
- **WHEN** an agent follows the runtime-owned unified ordinary-mailbox skill for attached shared mailbox work
- **AND WHEN** the current prompt or recent mailbox context does not provide the exact current gateway base URL
- **THEN** the skill directs the agent to run `houmao-mgr agents self mail resolve-live`
- **AND THEN** the agent obtains the exact live mailbox endpoint from the returned `gateway.base_url`

#### Scenario: Unified ordinary-mailbox skill avoids `pixi` and direct Python-module resolver guidance
- **WHEN** an agent follows the projected mailbox skills for ordinary mailbox work
- **THEN** those skills do not instruct the agent to use `pixi run houmao-mgr agents self mail resolve-live`
- **AND THEN** they do not instruct the agent to invoke `python -m houmao.agents.mailbox_runtime_support resolve-live` directly

### Requirement: Runtime-owned mailbox workflow skills use archive as completion
Projected runtime-owned mailbox workflow skills SHALL use archive to close processed Inbox work on bindings that support ordinary archive. On protected bindings, the agent SHALL report successfully processed messages for independently authorized mailbox-owner filing through the backend and finish the round after any required reply succeeds.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The `houmao-process-emails-via-gateway` workflow SHALL direct agents to list open inbox work through the gateway, choose relevant messages for the current round, peek or read selected messages intentionally, perform the requested work, reply or acknowledge when appropriate, archive only successfully processed messages where ordinary archive is supported, and stop after the round.

Deferred, skipped, or not-yet-completed messages SHALL remain unarchived so later notifier rounds can wake the agent again.

#### Scenario: Successfully processed mail is archived
- **WHEN** an agent finishes processing selected mailbox work during a notifier-driven round on a binding that supports ordinary archive
- **THEN** the projected workflow skill instructs the agent to archive the successfully processed messages through the gateway or manager fallback surface
- **AND THEN** unfinished messages remain unarchived for later notification

#### Scenario: A protected mailbox leaves filing to the backend

- **WHEN** an agent finishes selected work and any required reply on a protected binding
- **THEN** the skill directs the agent to report the completed messages for independently authorized owner filing and end the round
- **AND THEN** the skill omits ordinary archive, move, and placement-changing mark from the round and forbids switching to a fallback to perform them

### Requirement: Runtime-owned mailbox skills distinguish list, peek, read, mark, move, and archive
Projected runtime-owned mailbox skills SHALL present the ordinary mailbox action set as status, list, peek, read, send, post, reply, mark, move, archive, and resolve-live where the selected binding supports each action.

The skills SHALL explain that listing and peeking leave read state intact, reading sets read, reply marks the parent answered, and archive closes processed Inbox work where the binding permits it.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skills SHALL keep manual marking available as a repair or operator-directed action rather than as the normal completion step for processed mail. `move`, `archive`, and `mark` with an archived-state update SHALL require explicit binding placement capability even when ordinary read-state updates are supported.

#### Scenario: Skill user can inspect without marking read
- **WHEN** an agent follows projected mailbox skill guidance to inspect a message for triage
- **THEN** the skill presents `peek` as the non-mutating body-inspection action
- **AND THEN** it reserves `read` for the action that marks the message read

#### Scenario: Manual marking is not the normal completion path
- **WHEN** an agent follows projected mailbox skill guidance after completing a mailbox task
- **THEN** the skill directs the agent to archive the processed message where ordinary archive is supported
- **AND THEN** it presents manual `mark` only for explicit state repair or operator-directed state changes

### Requirement: Notifier-driven mailbox skills honor notification mode
The runtime-owned `houmao-process-emails-via-gateway` workflow skill SHALL understand notifier prompts that identify notification mode as `any_inbox` or `unread_only`.

When the prompt identifies mode `any_inbox`, the workflow SHALL direct the agent to list open inbox mail through the shared gateway mailbox API and process relevant selected mail for the round.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

When the prompt identifies mode `unread_only`, the workflow SHALL direct the agent to start from unread inbox mail through the shared gateway mailbox API for that round.

In both modes, the workflow SHALL close successfully processed Inbox work through archive where the selected binding supports ordinary archive. Reading, peeking, replying, or acknowledging SHALL leave placement to the backend.

#### Scenario: Any-inbox notification uses open inbox triage
- **WHEN** an agent begins a notifier-driven round whose prompt states mode `any_inbox`
- **THEN** the workflow skill directs the agent to list open inbox mail through the shared gateway mailbox API
- **AND THEN** where ordinary archive is supported, selected processed mail is archived only after the corresponding work and any required reply succeed

#### Scenario: Unread-only notification starts from unread inbox triage
- **WHEN** an agent begins a notifier-driven round whose prompt states mode `unread_only`
- **THEN** the workflow skill directs the agent to start from unread inbox mail through the shared gateway mailbox API
- **AND THEN** ordinary archive closes successfully processed mail where the binding supports it

#### Scenario: Skill does not restore read-as-completion semantics
- **WHEN** an agent follows the notifier-driven workflow in either mode
- **THEN** the workflow treats marking a message read as a change to unread eligibility
- **AND THEN** deferred, skipped, or unfinished messages remain unarchived for later handling according to the configured notifier mode

#### Scenario: The agent ends a round while Inbox mail remains on a protected binding

- **WHEN** the notified work is complete and the backend still lists the processed mail in Inbox
- **THEN** the workflow directs the agent to report the successfully processed mail for independently authorized owner filing and end the round
- **AND THEN** `any_inbox` can remind the agent again while the mail remains in Inbox, while `unread_only` applies the current read state

### Requirement: Mailbox system skills are not projected into Gemini homes
Runtime mailbox-skill projection SHALL expose no Gemini destination, `.gemini/skills` path, or Gemini discovery contract.

#### Scenario: Mailbox skill destination rejects Gemini
- **WHEN** mailbox skill projection receives Gemini as its target tool
- **THEN** projection fails as unsupported
- **AND THEN** it does not create `.gemini/skills` content

### Requirement: Runtime mailbox prompts enter through the managed-agent entrypoint
Runtime-owned notifier, mailbox, and gateway prompts that require Houmao system-skill behavior SHALL invoke or direct the managed agent to `houmao-agent-entrypoint` with the mailbox operation and notifier context.

The public entrypoint SHALL verify managed self identity before routing to the protected `houmao-process-emails-via-gateway` or `houmao-agent-email-comms` routine. Runtime prompts SHALL NOT instruct the agent to invoke either protected logical id as a top-level skill.

#### Scenario: Notifier starts an unread-mail round
- **WHEN** the runtime wakes a managed agent for gateway-notified unread mail
- **THEN** the prompt enters through `houmao-agent-entrypoint` with the current gateway context
- **AND THEN** the entrypoint verifies self identity before routing to the protected processing routine

### Requirement: Generated mailbox prompts require both static routing siblings
Mailbox command prompts and gateway notifier prompts SHALL use the `$houmao-agent-entrypoint` route only when the target tool-native skill root contains both `houmao-agent-entrypoint/SKILL.md` and `houmao-shared-routines/SKILL.md`.

Presence of only one sibling SHALL be treated as an incomplete skill route. The generated prompt SHALL use the maintained API fallback and SHALL NOT claim that entrypoint routing is installed.

#### Scenario: Agent entrypoint exists without shared routines
- **WHEN** prompt generation finds `houmao-agent-entrypoint/SKILL.md` but not `houmao-shared-routines/SKILL.md`
- **THEN** the prompt uses the API-oriented fallback
- **AND THEN** it does not instruct the agent to invoke a missing shared mailbox route

#### Scenario: Both static siblings exist
- **WHEN** prompt generation finds both required standalone entrypoints
- **THEN** the prompt invokes `$houmao-agent-entrypoint` with the appropriate mailbox route
- **AND THEN** it describes delegation to the shared-routines sibling rather than protected traversal below the entrypoint

### Requirement: Static shared routines preserve distinct mailbox owners
The static `houmao-shared-routines` skill SHALL own separate parent-scoped children for ordinary email communication and notifier-driven gateway email rounds.

`houmao-agent-email-comms` SHALL preserve ordinary resolver, status, list, peek, read, send, post, reply, mark, move, archive, and transport fallback behavior where each operation is supported on the selected binding. `houmao-process-emails-via-gateway` SHALL preserve one prompt-bootstrapped, metadata-first, stop-after-round workflow.

#### Scenario: Verified agent receives notifier prompt
- **WHEN** the agent entrypoint receives a notifier-driven round with the exact gateway base URL
- **THEN** it delegates through static shared routines to `houmao-process-emails-via-gateway`
- **AND THEN** the selected child stops after the bounded round

#### Scenario: Verified agent sends ordinary mail
- **WHEN** the agent entrypoint receives an ordinary send or reply request
- **THEN** it delegates through static shared routines to `houmao-agent-email-comms`
- **AND THEN** it does not use the notifier-round child

### Requirement: Managed mailbox installation uses top-level static siblings
A default mailbox-capable managed home SHALL receive the complete agent pack as four top-level static skill roots. Mailbox children SHALL remain parent-scoped beneath `houmao-shared-routines` and SHALL NOT be copied beneath `houmao-agent-entrypoint`.

#### Scenario: Codex managed home is prepared for mailbox work
- **WHEN** Houmao installs default system skills for a mailbox-capable Codex agent
- **THEN** `houmao-agent-entrypoint` and `houmao-shared-routines` are top-level siblings
- **AND THEN** ordinary and notifier mailbox children exist only inside shared routines
### Requirement: Mailbox skill workflows select channels explicitly
Ordinary and notifier-driven routines SHALL retain the selected channel and expected binding ID through mailbox operations. Canonical online-first identity SHALL not act as transport selection. A notifier round SHALL use its supplied channel, binding ID, and exact gateway endpoint. Binding mismatch SHALL end that round explicitly rather than silently switching to a replacement mailbox.

#### Scenario: Dual-mail agent processes an offline reminder
- **WHEN** the public agent entrypoint routes an offline notification round to its protected mailbox routine
- **THEN** every operation for that round uses the offline channel
- **AND THEN** the online canonical identity does not redirect the round

#### Scenario: Round lacks channel context
- **WHEN** a notifier-driven round has a gateway URL but no selected channel
- **THEN** the routine reports a contract error rather than guessing from the canonical address

### Requirement: Mailbox skill installation is independent of late binding health
Supported runtime prompts SHALL continue using the public agent entrypoint only when its required static routing siblings are installed. Otherwise they SHALL provide maintained API guidance for the selected channel without requiring a body restart, copying skills into project content, or claiming that newly written skill files are already known to a running CLI.

#### Scenario: Already-running mailbox-disabled body gains offline mail
- **WHEN** late registration enables offline mail on a body without an available native mailbox skill route
- **THEN** the notifier supplies the selected channel and direct API workflow
- **AND THEN** it does not require native skill hot-reload to make attachment actionable

### Requirement: Mailbox routines triage bounded metadata pages
Ordinary and notifier-driven routines SHALL start with one bounded metadata page on the selected channel and binding. They SHALL page only within the round budget and fetch content only for selected messages. They SHALL use the authorized filing path only for successfully processed mail after any required replies and stop after the round.

#### Scenario: Inbox is larger than one processing round
- **WHEN** the first metadata page has continuation but the round budget is reached
- **THEN** the routine leaves deferred work unarchived for later periodic reminders
- **AND THEN** it does not fetch all retained bodies before selecting work

#### Scenario: Bounded List Examples Pin the Selected Binding

- **WHEN** the routine illustrates a direct HTTP list request
- **THEN** the example uses `schema_version: 3`, `expected_binding_id`, and a bounded metadata-only listing without `include_body`

#### Scenario: Metadata is insufficient for a selected task
- **WHEN** an agent selects a message as relevant
- **THEN** it explicitly peeks or reads the needed content and checks any completeness limitation
- **AND THEN** it does not assume a preview is the full task request

### Requirement: Online binding changes end stale processing rounds explicitly
A round SHALL retain its expected binding ID and channel. If attachment controls replace or detach that binding, the routine SHALL treat the conflict as an interrupted round rather than rediscover another account and continue its old actions. Credential refresh for the same binding SHALL not itself require a new agent identity or body conversation.

#### Scenario: Account changes before a fresh reply or send
- **WHEN** the expected online binding no longer matches during a round
- **THEN** the routine reports the conflict and does not send through the replacement account
- **AND THEN** uncompleted mail remains governed by its original mailbox state

### Requirement: Runtime mailbox guidance keeps credential administration outside ordinary mail work
Ordinary agent mailbox guidance SHALL use current scoped APIs or manager helpers and SHALL not instruct the agent to print, copy into project files, or discover unrelated credentials. Authorized operator guidance SHALL document explicit online attachment, private credential refresh, reconnect, and detach separately from routine mail processing.

#### Scenario: Online authentication expires during a round
- **WHEN** the online provider rejects the configured credential
- **THEN** the routine reports the binding's sanitized authentication failure
- **AND THEN** it does not scan ambient authentication files or switch to offline mail
### Requirement: Gateway email-processing skill covers compact reply receipts and permission failure handling
`houmao-process-emails-via-gateway` SHALL document the compact CLI reply receipt and the `POST /v1/mail/{channel}/reply` action response, with read-only reconciliation on the same binding and explicit fail-closed reporting on `mail.reply` or `mail.attachment.owner_file` authorization failures.

#### Scenario: Agent reconciles reply receipts and permission refusals during a round
- **WHEN** a managed agent replies to or attaches files for a notified email during a gateway round
- **THEN** the workflow uses the CLI `message_ref` or HTTP `message.message_ref` for a same-binding `peek` when needed, and treats offline deposit and provider submission as distinct transport outcomes
- **AND THEN** a `mail.reply` or `mail.attachment.owner_file` denial or an unconfirmed required reply leaves the message open for follow-up

### Requirement: Gateway email-processing skill adopts progressive disclosure into commands and references
`houmao-process-emails-via-gateway` SHALL refactor its 169-line `SKILL-MAIN.md` monolith into a lean ~70-line router (`SKILL-MAIN.md`) with `commands/process-round.md` (carrying its own numbered `## Workflow` and fallback) and `references/reply-hardening.md` (carrying the reminder contract and prompt template) per `imsight-agent-skill-handling`.

#### Scenario: Entrypoint stays concise while round procedure and template live in subfiles
- **WHEN** a reviewer inspects `houmao-process-emails-via-gateway`
- **THEN** `SKILL-MAIN.md` provides concise `## Workflow`, `## Actor Frame Gate`, `## Subcommands` (`help`, `process-round`), and `## Guardrails`
- **AND THEN** `commands/process-round.md` owns the bounded round steps and `references/reply-hardening.md` owns the reminder payload and template

### Requirement: Gateway email-processing skill preserves fail-closed round, reply-hardening, and non-polling invariants
`houmao-process-emails-via-gateway` SHALL preserve agent-only `## Actor Frame Gate`, fail-closed reliance on prompt-supplied `gateway_base_url`, `channel`, and `expected_binding_id`, stalled-work-first ordering, `one_off` lowest-priority (`--after-all` / `start_after_seconds: 15`) reply hardening, and stopping without polling. The binding's placement capability governs filing after successfully processing and replying.

#### Scenario: Missing gateway URL or binding mismatch terminates the round fail-closed
- **WHEN** a notifier prompt lacks `gateway_base_url`, `channel`, or `expected_binding_id`, or the binding mismatches
- **THEN** `houmao-process-emails-via-gateway` stops with a contract failure without running `resolve-live`
- **AND THEN** a successful round archives completed items after any required reply where the binding permits it, or reports them for independently authorized owner filing on a protected binding
