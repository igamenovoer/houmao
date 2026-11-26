# houmao-agent-messaging-skill Specification

## Purpose
Define the packaged Houmao-owned system skill that routes communication and control for already-running managed agents.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-messaging` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-messaging` as a parent-scoped child of `houmao-shared-routines`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That skill SHALL instruct agents to communicate with already-existing Houmao-managed agents through these scoped manager and HTTP surfaces:

- `agents single ... state` or verified `agents self state`
- `agents single ... request` for attributed work requests
- scoped `gateway status`, `mail resolve-live`, `prompt`, and `interrupt`
- scoped `gateway prompt|interrupt|send-keys`
- scoped `gateway tui state|history|note-prompt`
- managed-agent HTTP routes under `/houmao/agents/*`

The child `SKILL-MAIN.md` SHALL route to one local action-specific document for `discover`, `request`, `prompt`, `interrupt`, `gateway-queue`, `send-keys`, `mail`, or `reset-context`. The catalog and skill SHALL expose `mail` as the canonical handoff command and `mail-handoff` as its alias.

That packaged skill SHALL remain the canonical Houmao-owned skill for communication with already-running managed agents whether the caller is another managed agent or an external operator.

That packaged skill SHALL delegate the following operations to their owning routines:

- managed-agent launch, join, stop, relaunch, and cleanup
- project specialist and project agent authoring and lifecycle commands
- ordinary mailbox status, reads, writes, and archive
- filesystem or Stalwart mailbox transport internals
- gateway attach and detach

#### Scenario: Installed skill points the agent at supported communication surfaces
- **WHEN** an agent opens the installed `houmao-agent-messaging` skill through its parent
- **THEN** the skill directs the agent to supported work-request, direct prompt, interrupt, gateway, mailbox-discovery, and managed-agent HTTP surfaces

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** `SKILL-MAIN.md` directs the agent to the local document for the requested action
- **AND THEN** `mail` and `mail-handoff` select the same mailbox handoff document

#### Scenario: Installed skill keeps lifecycle and mailbox-operation internals out of scope
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** it delegates managed-agent lifecycle, ordinary mailbox work, and mailbox transport internals

### Requirement: `houmao-agent-messaging` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-agent-messaging` skill SHALL teach agents to resolve `houmao-mgr` for the current workspace. An explicit user choice SHALL take precedence over the default order of PATH lookup, the uv-managed fallback, and a development launcher.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The packaged `houmao-agent-messaging` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed messaging action selected through the packaged skill.

#### Scenario: PATH launcher is preferred before development probing
- **WHEN** `command -v houmao-mgr` succeeds in the current workspace
- **THEN** the skill tells the agent to use that PATH-resolved `houmao-mgr` command for the turn
- **AND THEN** it does not probe `.venv`, Pixi, or project-local uv launchers first

#### Scenario: uv fallback is used when PATH lookup fails
- **WHEN** `command -v houmao-mgr` fails in the current workspace
- **THEN** the skill tells the agent to try `uv tool run --from houmao houmao-mgr`
- **AND THEN** it treats that uv-managed launcher as the ordinary next fallback because Houmao is officially installed through uv tools

#### Scenario: Development launchers are later defaults, not first probes
- **WHEN** `command -v houmao-mgr` fails
- **AND WHEN** the uv-managed fallback does not satisfy the turn
- **AND WHEN** the current workspace provides development launchers such as Pixi, repo-local `.venv`, or project-local uv
- **THEN** the skill tells the agent to choose an appropriate development launcher for that workspace
- **AND THEN** it does not treat those development launchers as the default first search path

#### Scenario: Explicit user launcher choice overrides the default order
- **WHEN** the user explicitly asks to use `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, project-local `uv run houmao-mgr`, or another specific launcher
- **THEN** the skill tells the agent to honor that requested launcher
- **AND THEN** it does not replace the user-requested launcher with the default PATH-first or uv-fallback choice

### Requirement: `houmao-agent-messaging` handles reset-context and lower-level gateway control honestly
The packaged `houmao-agent-messaging` skill SHALL describe clear-context and chat-session control using the currently implemented gateway control surfaces rather than inventing unsupported `houmao-mgr` flags.

For TUI-backed managed agents, the skill SHALL describe reset-then-send behavior through `POST /houmao/agents/{agent_ref}/gateway/control/prompt` or direct `POST /v1/control/prompt` with `chat_session.mode = "new"` when immediate clear-and-send control is required.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For headless managed agents, the skill SHALL describe both:

- direct prompt control with `chat_session.mode = "new"`, and
- one-shot next-prompt override through `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` or direct `POST /v1/control/headless/next-prompt-session`

The skill SHALL state that direct gateway HTTP requires the exact live gateway base URL already present in current context or another supported discovery result, and SHALL NOT guess gateway host or port.

The skill SHALL state when the requested reset or chat-session behavior cannot stay entirely on the current `houmao-mgr` surface because the CLI does not yet expose a first-class flag for that behavior.

#### Scenario: TUI reset-context points to prompt-control with `mode = new`
- **WHEN** the user asks to clear context and immediately send a new prompt to a TUI-backed managed agent
- **THEN** the skill directs the agent to the managed-agent or direct gateway prompt-control route with `chat_session.mode = "new"`
- **AND THEN** it does not fabricate a nonexistent `houmao-mgr` reset-context flag

#### Scenario: Headless one-shot override uses next-prompt-session
- **WHEN** the user asks to prepare the next headless prompt for a fresh chat session without sending the prompt immediately
- **THEN** the skill directs the agent to the managed-agent or direct gateway `next-prompt-session` route
- **AND THEN** it does not misdescribe that one-shot override as a queued gateway prompt request

#### Scenario: Direct gateway URL is not guessed
- **WHEN** the requested reset or lower-level gateway operation would require direct gateway HTTP
- **AND WHEN** the current context does not provide an exact live gateway base URL
- **THEN** the skill does not guess a gateway host or port
- **AND THEN** it instead directs the agent to a supported higher-level managed-agent surface or reports that the required lower-level gateway endpoint is unavailable

### Requirement: `houmao-agent-messaging` delegates mailbox behavior to the current Houmao mailbox skills
When mailbox-related messaging requires notifier-round workflow, ordinary mailbox actions, or transport-specific guidance, the packaged `houmao-agent-messaging` skill SHALL direct the agent to the current Houmao mailbox skills instead of duplicating that detail locally.

At minimum, that delegation SHALL cover:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The packaged `houmao-agent-messaging` skill SHALL keep its own mailbox coverage at the communication-routing and mailbox-handoff level and SHALL NOT restate filesystem layout, Stalwart credential handling, managed-agent mailbox operation routes, or the lower-level `/v1/mail/*` contract in full.

#### Scenario: Gateway mailbox round work delegates to the processing skill
- **WHEN** the messaging task becomes a notifier-driven mailbox-processing round with a live gateway mailbox facade
- **THEN** the skill directs the agent to `houmao-process-emails-via-gateway`
- **AND THEN** it does not duplicate that round workflow inside `houmao-agent-messaging`

#### Scenario: Ordinary mailbox work delegates to the unified ordinary-mailbox skill
- **WHEN** the messaging task needs ordinary mailbox work, live mailbox discovery follow-through, or transport-local mailbox guidance
- **THEN** the skill directs the agent to `houmao-agent-email-comms`
- **AND THEN** it does not restate that ordinary mailbox guidance as part of the generic managed-agent messaging skill

### Requirement: `houmao-agent-messaging` describes TUI interrupt as best-effort `Escape`
The packaged `houmao-agent-messaging` skill SHALL describe `houmao-mgr agents interrupt` as the default transport-neutral interrupt path for already-running managed agents.

For TUI-backed managed agents, the skill SHALL explain that ordinary interrupt means one best-effort `Escape` delivery and that the caller does not need to switch to raw `send-keys` merely to get that TUI interrupt behavior.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For TUI-backed managed agents, the skill SHALL explain that interrupt MAY still be useful when currently reported TUI state looks idle because tracked TUI state can lag the live visible surface.

For headless managed agents, the skill SHALL explain that ordinary interrupt targets active execution work and MAY return no-op semantics when no headless work is active.

The skill SHALL continue treating `houmao-mgr agents gateway send-keys` as the exact raw control-input path for slash menus, cursor movement, partial typing, or other precise TUI shaping.

#### Scenario: Skill describes ordinary TUI interrupt without redirecting to raw send-keys
- **WHEN** the user asks to interrupt a managed TUI agent
- **THEN** the skill directs the agent to use `houmao-mgr agents interrupt`
- **AND THEN** it explains that the TUI interrupt path delivers best-effort `Escape` rather than redirecting the caller to `houmao-mgr agents gateway send-keys`

#### Scenario: Skill explains delayed TUI tracking honestly
- **WHEN** the user asks why TUI interrupt may still be attempted while reported state looks idle
- **THEN** the skill explains that tracked TUI state can lag the live visible pane
- **AND THEN** it does not describe the idle tracked posture as proof that a TUI interrupt request would be meaningless

#### Scenario: Skill keeps headless interrupt semantics distinct
- **WHEN** the user asks to interrupt a managed headless agent
- **THEN** the skill explains that ordinary interrupt targets active execution work
- **AND THEN** it does not describe headless interrupt as unconditional `Escape` delivery

### Requirement: `houmao-agent-messaging` delegates generic managed-agent inspection to `houmao-agent-inspect`
The packaged `houmao-agent-messaging` skill SHALL treat generic requests to inspect managed-agent liveness, transport detail, mailbox posture, runtime artifacts, logs, or direct tmux backing as outside its primary ownership.

For those generic inspection requests, the packaged skill SHALL direct the caller to `houmao-agent-inspect`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The packaged skill MAY continue using `agents state`, `agents gateway status`, `agents mail resolve-live`, and gateway-owned TUI tracker surfaces when that inspection is inseparable from the currently selected messaging workflow, such as prompt-lane discovery, queue-specific validation, or explicit prompt-provenance work.

#### Scenario: Generic inspection request routes to the inspect skill
- **WHEN** a caller asks the messaging skill to inspect what one managed agent is doing, which pane backs it, or which logs and artifacts should be examined
- **THEN** the skill directs the caller to `houmao-agent-inspect`
- **AND THEN** it does not present generic managed-agent inspection as primary messaging guidance

#### Scenario: Queue-specific tracker inspection stays available inside messaging
- **WHEN** a caller explicitly needs gateway-owned TUI state or history as part of queued prompt, queued interrupt, or prompt-provenance work
- **THEN** the skill may still direct the caller to the supported gateway TUI tracker surfaces inside the messaging workflow
- **AND THEN** it does not claim ownership of generic managed-agent inspection outside that messaging-specific context

### Requirement: Messaging skill selects explicit gateway prompt admission policy

The packaged `houmao-agent-messaging` skill SHALL teach agents to select `ready-only`, `if-no-pending`, or `always` for gateway prompt admission based on caller intent.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The packaged `houmao-agent-messaging` skill SHALL teach agents to map caller intent to the maintained gateway prompt admission policies:

- use `ready-only` when the prompt must be processed immediately and the agent SHALL back off while the CLI is busy,
- use `if-no-pending` when the prompt may enter a busy provider CLI but SHALL back off if a submitted prompt is already pending or pending state is unknown,
- use `always` when the caller explicitly wants submission regardless of tracked readiness or pending-input state.

The skill SHALL explain that non-default policies apply to TUI-backed targets, that structural gateway failures still reject every policy, and that if-no-pending is observational rather than an atomic queue reservation.

The skill SHALL use `--admission-policy` in current `houmao-mgr agents single|self ... gateway prompt` examples and SHALL NOT instruct agents to use the removed `--force` option.

#### Scenario: Busy-sensitive caller intent selects ready-only

- **WHEN** the caller says to submit only if the target will process the prompt immediately
- **THEN** the messaging skill directs the agent to `--admission-policy ready-only`
- **AND THEN** it explains that a busy TUI causes the command to back off

#### Scenario: Empty-queue caller intent selects if-no-pending

- **WHEN** the caller allows submission while the TUI is busy but does not want to add behind an existing provider-native queued prompt
- **THEN** the messaging skill directs the agent to `--admission-policy if-no-pending`
- **AND THEN** it explains that both `pending_input=yes` and `pending_input=unknown` cause refusal

#### Scenario: Explicit unconditional caller intent selects always

- **WHEN** the caller explicitly requests prompt submission regardless of busy and pending posture
- **THEN** the messaging skill directs the agent to `--admission-policy always`
- **AND THEN** it does not claim that this bypasses detachment, reconciliation, validation, or unsupported-target failures

#### Scenario: Skill does not promise one-winner concurrency

- **WHEN** an agent considers multiple closely spaced if-no-pending submissions
- **THEN** the skill explains that each call uses the latest observed TUI state independently
- **AND THEN** it does not promise that only one call can reach the CLI before repaint

### Requirement: Messaging separates agent selectors from transport overrides
The messaging skill SHALL select a peer with `agents single --agent-id ID` or `--agent-name NAME` and use `agents self` only for verified current-session scope. It SHALL describe `--port` and `--pair-port` as transport options on the commands that accept them.

#### Scenario: The caller supplies a port but no selected agent
- **WHEN** a caller asks to prompt a peer and gives only a passive server port
- **THEN** the skill asks for the peer identity
- **AND THEN** it retains the supplied port as a transport option for the selected command

### Requirement: Messaging guidance uses the gateway prompt receipt

The packaged messaging skill SHALL report admission and handoff from the first gateway prompt receipt. It SHALL use read-only evidence for further observation and preserve uncertainty when that evidence cannot establish the outcome.

#### Scenario: The target queues a prompt

- **WHEN** the receipt reports `outcome: queued` and `sent: false`
- **THEN** the skill reports accepted queueing with the available operation and native IDs
- **AND THEN** it retains that result without another submission for confirmation or output formatting

#### Scenario: The caller needs to observe a prior submission

- **WHEN** the caller needs more than the prompt receipt
- **THEN** the skill directs it to a saved headless turn or authorized service request lookup when the receipt identifies one
- **AND THEN** it explains the limits of Web and TUI state or history when no exact read result is available

### Requirement: Agent messaging rewrites request.md stub and covers DSH, service/web, and CCCC distinctions
`houmao-agent-messaging` SHALL rewrite the 11-line `commands/request.md` stub with numbered `## Workflow`, fallback, `## Guardrails`, neutral prose, automatic managed-session peer-signer default, and full flags (required `--text`, `--url`, `--passive-url`, `--source-agent-id`, `--unsigned`, `--context-id`, `--generation`, `--presence`, `--ca-bundle`), update `prompt.md` for `dsh`, `service`/`web`, and `agent-operator`, and distinguish `houmao-cccc` chat from prompt/mail.

#### Scenario: Request subcommand provides full conforming workflow and CCCC boundaries stay clear
- **WHEN** an agent or operator invokes `houmao-agent-messaging->request()` or `prompt()`
- **THEN** `commands/request.md` follows `imsight-agent-skill-handling` with numbered `## Workflow`, fallback, `## Guardrails`, neutral caller/target prose, required `--text`, and automatic current managed-session peer signing when `--source-agent-id` and `--unsigned` are omitted
- **AND THEN** `commands/prompt.md` covers `dsh`, `service`/`web` outcomes, and `agent-operator` authority while distinguishing `houmao-cccc` chat from Houmao prompt/mail

### Requirement: Agent messaging strips cross-skill boilerplate from SKILL-MAIN.md
`houmao-agent-messaging/SKILL-MAIN.md` SHALL remove duplicated launcher, Missing-Input, `houmao-cli`, and redundant Supported/Out-of-Scope/Routing lists into a lean ~90-line entrypoint per `imsight-agent-skill-handling`.

#### Scenario: Messaging entrypoint keeps only skill-specific workflow, routing, and guardrails
- **WHEN** a reviewer inspects `houmao-agent-messaging/SKILL-MAIN.md`
- **THEN** duplicated cross-skill boilerplate is absent and `## Subcommands` cleanly links all eight command pages including `request`

### Requirement: Agent messaging preserves peer posture, channel separation, and admission policies
`houmao-agent-messaging` SHALL preserve `## Actor Frame Gate`, peer-directed messaging in `actor_kind=agent`, strict channel separation (`request` vs `prompt` vs `gateway-queue` vs `send-keys` vs `mail` vs `reset-context`), `--admission-policy` (`ready-only`, `if-no-pending`, `always`), and no silent cross-channel retries.

#### Scenario: Denied or failed work request does not fall back to direct prompt or mail
- **WHEN** `agents single ... request` fails admission or is refused by target policy
- **THEN** `houmao-agent-messaging` reports the exact refusal without retrying via `prompt`, `send-keys`, `--unsigned`, or `mail`
### Requirement: Messaging Selects a Route by Intent and Reports the Selected Outcome
The packaged `houmao-agent-messaging` skill SHALL tell the agent to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target or messaging intent that is not explicit in current or recent conversation context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL select commands by communication intent:

- use `houmao-mgr agents single ... request` to ask a peer to perform work as an attributed request
- use scoped `houmao-mgr agents single|self ... prompt` for an explicitly intended synchronous conversational turn through verified native execution authority
- use scoped `houmao-mgr agents single|self ... interrupt` for the transport-neutral interrupt path with its applicable authority
- use the supported managed-agent gateway request route or gateway `/v1/requests` with the applicable admission lane for explicitly requested durable queue behavior
- use scoped `gateway prompt|interrupt` or the applicable signed direct gateway route for explicit gateway controls
- use scoped `gateway send-keys` for authorized exact raw control input
- use scoped `mail resolve-live` when the task needs mailbox discovery, current mailbox capability, or the exact live `gateway.base_url` before mailbox handoff
- use scoped `state` when the next action needs current runtime posture and `gateway status` when it needs verified gateway status

For outbound agent mail, `commands/mail.md` SHALL use a known or resolved recipient address for the explicit channel and act through the sending agent's verified mailbox binding. It SHALL report the selected transport's outcome with recipient mail rules, placement, notification, and processing left unspecified.

The skill SHALL prefer `houmao-mgr agents ...` and managed-agent `/houmao/agents/*` routes over direct gateway listener URLs when those higher-level surfaces already satisfy the current task.

#### Scenario: Ordinary conversation uses the default prompt path
- **WHEN** an authorized execution owner requests a direct conversational turn with a managed agent and wants to wait for its outcome
- **THEN** the skill directs the caller to use the scoped `houmao-mgr agents single ... prompt` or verified self equivalent
- **AND THEN** it preserves the synchronous execution path

#### Scenario: Raw terminal shaping uses send-keys instead of prompt submission
- **WHEN** the user requests slash-command menus, arrow navigation, `Escape`, or partial typing in a live TUI session
- **THEN** the skill directs an authorized caller to scoped `gateway send-keys`
- **AND THEN** it identifies this as raw terminal shaping with its own authority

#### Scenario: Queued control uses the gateway request surface
- **WHEN** the user explicitly wants a durable gateway queue for a direct prompt or interrupt
- **THEN** the skill uses the authorized request queue route and selects the typed effect for the intended operation
- **AND THEN** it preserves the queue receipt and distinguishes immediate `gateway prompt` admission from durable queue admission

#### Scenario: Mailbox work uses discovery before handoff
- **WHEN** the user asks for mailbox-related work against a managed agent
- **THEN** the skill directs the agent to use scoped `mail resolve-live` or the equivalent managed-agent discovery route first when current mailbox posture or `gateway.base_url` is needed
- **AND THEN** it hands ordinary mailbox operations off to the applicable mailbox skill after discovery

#### Scenario: Missing target requires a user question
- **WHEN** the selected messaging action still lacks a required target after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing selector before proceeding
- **AND THEN** it does not guess the target managed agent

#### Scenario: Recipient contact is enough for ordinary mail

- **WHEN** a managed agent needs to send ordinary mail to a named peer
- **THEN** the skill uses the peer's known address or the peer's `mail resolve-live` result for the requested channel
- **AND THEN** the skill sends through `agents self mail send` using the sender's verified binding without preflighting the recipient gateway's roles
- **AND THEN** it describes online confirmation as provider-confirmed submission and offline confirmation as transport-confirmed deposit
- **AND THEN** it reports transport confirmation without inferring the backend's placement, agent notification, or processing

#### Scenario: The Mail Transport Refuses Submission or Deposit

- **WHEN** verified Alice submits ordinary mail to Bob and the selected transport refuses submission or deposit
- **THEN** the skill reports that transport's refusal and keeps Alice as the sender
- **AND THEN** it performs no retry through a different recipient channel or Bob's delegated mailbox sender identity

#### Scenario: Bob's Backend Applies His Mailbox Policy

- **WHEN** Bob asks how his mailbox policy affects an ordinary incoming message
- **THEN** the skill explains that his mailbox backend checks sender metadata at delivery and files matching new messages directly into Archive outside ordinary Inbox work and reminders
- **AND THEN** it explains that rule changes leave existing Inbox mail in place and that unblocking leaves archived mail in Archive
- **AND THEN** it preserves the same sender-facing acceptance receipt whether the backend files the message in Inbox or Archive and treats sender metadata separately from verified gateway identity

#### Scenario: Gateway is detached for a normal prompt

- **WHEN** a direct conversational turn is explicitly requested and the target has no live gateway
- **THEN** the skill uses the scoped managed-agent prompt command through the recorded owner route if authorized and available
- **AND THEN** it reports unavailability when no authorized owner route can admit the prompt

### Requirement: Messaging Guidance Distinguishes Typed Requests From Direct Control

The skill's `commands/request.md` SHALL use the typed work-request command through a verified gateway or qualified direct passive path. It SHALL select the path and proof before submission and explain eligibility for default admission. Direct prompts, native slash commands, and interruption SHALL require explicit intent and applicable authority. Observation, raw keys, and admission overrides SHALL retain separate effects.

#### Scenario: Alice Requests That Bob Review a Patch

- **WHEN** Alice has `builtin:agent-requester` or a higher cumulative peer role on Bob and wants to ask Bob to review a patch
- **THEN** the skill routes the work through `agents single --agent-id <bob-id> request --text <text>` with the stable peer signer
- **AND THEN** it reports the available request admission or handoff evidence and relies on separately authorized surfaces for any later output

#### Scenario: New Alice Contacts Bob Through the Default Group

- **WHEN** Alice has no explicit `builtin:` group assignment on Bob, qualifies for fallback, and needs to submit a work request
- **THEN** the skill selects the verified target and uses the typed request command without requiring enrollment on Bob
- **AND THEN** it uses independently verified identity when available on the selected path, or uses explicit `--unsigned` when the caller has selected anonymous submission and the operation permits it
- **AND THEN** it reports unsupported proof or verification refusal as applicable and preserves the selected caller attribution
- **AND THEN** it reports the target's admission outcome and preserves the distinction between verified and anonymous attribution

#### Scenario: Bob Refuses a Signed Work Request from Status-Only Alice

- **WHEN** Alice has Bob's exact status grant and default fallback is disabled for her verified identity
- **THEN** the skill reports Bob's refusal of an ungranted work request
- **AND THEN** it preserves the signed refusal even if the configured default would authorize a separate unsigned request

#### Scenario: Alice Intentionally Submits an Unsigned Work Request

- **WHEN** Alice explicitly chooses unsigned submission before contacting Bob and Bob's current default permits the typed request
- **THEN** `commands/request.md` uses `--unsigned` and reports anonymous attribution
- **AND THEN** it explains that Bob's verified per-principal fallback restriction applies to requests carrying Alice's proof

#### Scenario: Alice Submits a Slash Command as Request Content

- **WHEN** a work request contains the text `/compact`
- **THEN** the skill explains that Bob receives attributed request content
- **AND THEN** it reserves native slash invocation for the explicitly authorized direct lane

#### Scenario: Alice Has Direct Turn Control

- **WHEN** Alice intends to send text verbatim, invoke a supported slash command, or interrupt Bob's current turn
- **THEN** the skill uses the corresponding supported direct operation under the same selected target and applicable caller proof
- **AND THEN** it identifies `builtin:agent-operator` or separate direct grants as the applicable authority
- **AND THEN** raw keys and session, model, or admission overrides retain their own authorization

#### Scenario: Alice Maintains Bob's Common Plugins

- **WHEN** Alice has `builtin:agent-maintainer` on Bob and asks Bob to act on a plugin change
- **THEN** the skill routes communication through the attributed work-request command
- **AND THEN** it hands qualified skill and MCP editing and publication to the file-edit workflow
- **AND THEN** the common-plugin role alone does not authorize a direct prompt, slash command, or interruption

#### Scenario: The Work Request Cannot Be Admitted

- **WHEN** Alice's selected request path is unavailable or denies her work request
- **THEN** the skill preserves the requested operation and reports the reason
- **AND THEN** it performs no direct prompt, raw-key, unsigned, mail, or other-path retry

#### Scenario: Carol Sends Wrapped Work to Bob Through the Passive Server

- **WHEN** Bob's gateway is detached and Carol chooses a qualified direct passive work-request path
- **THEN** the routine uses the typed request command and reports the admission or handoff evidence from the passive server
- **AND THEN** the routine preserves the distinction among accepted work, confirmed handoff, and eventual task completion

#### Scenario: Carol Contacts Bob While His Gateway Is Detached

- **WHEN** Carol wants to ask detached Bob to review a patch and chooses mail for the handoff
- **THEN** the routine uses Carol's own sender binding and Bob's verified mailbox address
- **AND THEN** it reports the mail transport's outcome without contacting Bob's gateway to check recipient permissions
- **AND THEN** it explains that Bob's backend applies its configured placement policy while his gateway is detached
