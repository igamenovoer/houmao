# agent-gateway-reference-docs Specification

## Purpose
Define the structure, coverage, and quality bar for agent gateway reference documentation in the repository.
## Requirements
### Requirement: Agent gateway reference documentation is organized under a dedicated subtree
The repository SHALL publish the agent gateway reference documentation under `docs/reference/gateway/` with an `index.md` entrypoint instead of concentrating the full gateway reference inside broader runtime pages.

That subtree SHALL provide a navigational overview that directs readers to detailed gateway documentation pages by topic.

#### Scenario: Gateway reference entrypoint is a navigational index
- **WHEN** a reader opens the agent gateway reference entrypoint
- **THEN** the repository presents `docs/reference/gateway/index.md`
- **AND THEN** that page explains the structure of the gateway reference subtree and links to the detailed pages

#### Scenario: Top-level docs navigation reaches the gateway subtree
- **WHEN** a reader browses top-level reference indexes or broader runtime reference pages
- **THEN** those pages link to the agent gateway reference subtree
- **AND THEN** the subtree is discoverable without requiring the reader to inspect source directories directly

### Requirement: Agent gateway reference documentation separates contracts, operations, and internals
The `docs/reference/gateway/` subtree SHALL separate detailed gateway documentation into distinct categories for contracts, operations, and internals.

The gateway reference SHALL include at minimum one detailed page in each of those categories.

#### Scenario: Gateway contracts, operations, and internals have distinct pages
- **WHEN** a reader navigates the agent gateway reference subtree
- **THEN** the subtree provides dedicated detailed pages for gateway contracts, operational workflows, and internal architecture
- **AND THEN** those pages do not rely on one mixed catch-all page to explain all gateway topics

### Requirement: Agent gateway reference pages combine intuitive explanations with exact technical detail
Each detailed gateway page SHALL start with a short scope and plain-language explanation, then give the exact constraints, contracts, and artifact details readers need for implementation, debugging, or maintenance. It SHALL include a concrete example, representative payload, or artifact shape when one materially helps readers understand the topic.

#### Scenario: New reader can orient before reading exact gateway contracts
- **WHEN** a first-time reader opens a detailed agent gateway reference page
- **THEN** the page first explains the purpose of the topic in accessible language
- **AND THEN** the reader can build an intuitive mental model before encountering the full technical detail

#### Scenario: Developer can still find exact gateway specifics
- **WHEN** a developer opens a detailed agent gateway reference page to answer an implementation or debugging question
- **THEN** the page includes the exact gateway constraints, contracts, or artifact details relevant to that topic
- **AND THEN** the page is not limited to high-level explanatory prose alone

### Requirement: Important gateway procedures include embedded Mermaid sequence diagrams
For important procedures with multiple participants or steps, gateway reference pages SHALL pair prose with an embedded Mermaid `sequenceDiagram`. At minimum this covers launch-time auto-attach and attach-later flows, request acceptance and queued execution, detach and restart, stale live-binding cleanup, and recovery or reconciliation affected by managed-agent continuity.

#### Scenario: Procedure page includes an embedded sequence diagram
- **WHEN** a gateway reference page introduces an important gateway procedure
- **THEN** that page includes an embedded Mermaid `sequenceDiagram` block in the Markdown content
- **AND THEN** the diagram appears alongside the written explanation of the procedure

#### Scenario: Diagram supplements rather than replaces the written procedure
- **WHEN** a reader uses the documentation to understand an important gateway procedure
- **THEN** the page provides both prose explanation and a Mermaid sequence diagram
- **AND THEN** the reader is not required to infer the full procedure from the diagram alone

### Requirement: Gateway contract documentation covers the implemented v1 gateway surfaces
The gateway contract docs SHALL explain implemented v1 attach, listener, request, status, storage, validation, and error contracts. They SHALL identify supported live adapters and request behavior within the current implementation boundary.

#### Scenario: Contract documentation covers attach, status, and request surfaces
- **WHEN** a reader needs the normative gateway reference for current v1 behavior
- **THEN** the gateway contract pages describe attach metadata, live env bindings, the HTTP surface, request kinds, and the status model
- **AND THEN** the reader does not need to reconstruct those contracts only from scattered source files

#### Scenario: Contract documentation stays within implemented v1 scope
- **WHEN** a reader uses the gateway reference docs to understand supported behavior
- **THEN** the documentation makes clear the currently implemented v1 scope and boundaries
- **AND THEN** the docs do not describe future extensibility as if it were already implemented behavior

#### Scenario: Contract Pages Identify Binding and State Details
- **WHEN** a reader follows the v1 gateway contract to attach a session or interpret its state
- **THEN** the pages distinguish a gateway-capable session from a live attached session, and stable attachability metadata from live bindings
- **AND THEN** the pages describe the strict attach contract, tmux-published environment pointers, and the distinction between desired and live listeners
- **AND THEN** the pages specify the implemented HTTP routes, request kinds, versioned status model and current status axes, responsibilities of durable state artifacts, and observable validation and error semantics

### Requirement: Gateway operational documentation covers lifecycle and operator-facing workflows
The gateway operations docs SHALL explain safe v1 attach, detach, status, recovery, and control workflows. They SHALL document current managed-agent command surfaces, strict current-session discovery, and the operating effects of direct and queued control.

#### Scenario: Operational guidance covers gateway lifecycle actions
- **WHEN** an operator or developer needs to understand how a gateway starts, attaches, detaches, or disappears from a running session
- **THEN** the gateway operations pages explain those lifecycle actions and their observable runtime effects
- **AND THEN** the explanation is concrete enough for a new reader to follow the intended sequence safely

#### Scenario: Operational guidance explains gateway-capable versus live-gateway states
- **WHEN** a reader needs to understand why a session is gateway-capable but not currently attached to a live gateway
- **THEN** the gateway operations pages explain the distinction between stable attachability and live bindings
- **AND THEN** the reader can tell which gateway-aware actions require a live attached instance

#### Scenario: Current-session attach guidance reflects strict manifest-first discovery

- **WHEN** a reader needs to use current-session gateway attach
- **THEN** the gateway operations pages explain that attach resolves through `HOUMAO_MANIFEST_PATH` first and `HOUMAO_AGENT_ID` plus fresh shared-registry `runtime.manifest_path` second
- **AND THEN** the pages explain that current-session pair attach remains unavailable until the matching managed-agent registration exists on the persisted pair authority

#### Scenario: Operator can distinguish gateway command families safely

- **WHEN** a reader needs to choose between gateway prompt, raw send-keys, TUI inspection, or mail-notifier control
- **THEN** the gateway operations pages explain the purpose and boundary of each operator-facing surface
- **AND THEN** the pages do not imply that non-zero tmux windows can be rediscovered heuristically instead of following the recorded `current-instance.json` handle

#### Scenario: Operator Finds Lifecycle and Control Choices
- **WHEN** an operator chooses a v1 gateway workflow
- **THEN** the operations pages explain launch-time auto-attach, attach-later behavior, explicit selectors, current-session resolution and its pair-managed registration precondition
- **AND THEN** they explain how detach interacts with stopping a session, how to inspect offline, unavailable and live states, and how stale live bindings are invalidated or cleaned up
- **AND THEN** they identify `gateway/run/current-instance.json` as the authoritative same-session live execution record for a gateway hosted in an auxiliary tmux window
- **AND THEN** they cover prompt, interrupt, send-keys, TUI inspection, and mail-notifier commands and explain when to use direct runtime control or gateway-routed queued control

### Requirement: Gateway internal documentation explains queueing, epochs, and recovery boundaries
The gateway internals SHALL document the durable queue and event log, current-instance state and epochs, admission and single active execution, restart recovery for accepted work, and replay blocking or reconciliation after a managed-agent instance changes. They SHALL describe the v1 live-adapter boundary and explain why gateway-local health and managed-agent availability are separate.

#### Scenario: Internal docs explain queueing and current-instance state
- **WHEN** a maintainer needs to understand how gateway-managed work is accepted, persisted, and executed
- **THEN** the gateway internals pages explain the durable queue, current-instance state, and active execution model
- **AND THEN** the reader can relate those docs to the gateway implementation without reverse-engineering the queue behavior from code alone

#### Scenario: Internal docs explain recovery and replay boundaries
- **WHEN** a maintainer needs to understand how gateway behavior changes across restart, managed-agent outage, or managed-agent epoch change
- **THEN** the gateway internals pages explain the recovery, reconciliation, and replay-blocking boundaries in the implemented v1 flow
- **AND THEN** the documentation makes clear why gateway-local health and managed-agent availability are reported separately

### Requirement: Agent gateway reference pages identify the source materials they reflect
The agent gateway reference documentation SHALL identify the implementation files or tests that each detailed page reflects.

This source mapping SHALL help keep the repo-level gateway reference aligned with the implementation and behavior-defining tests without forcing readers to use the source files as the only long-form documentation.

#### Scenario: Detailed gateway pages point to implementation sources
- **WHEN** a reader opens a detailed agent gateway reference page
- **THEN** that page identifies the relevant source files or tests that define the documented behavior
- **AND THEN** future gateway changes have a clear trace from implementation surfaces to repo-level reference docs

### Requirement: Agent gateway reference pages introduce terminology clearly
The agent gateway reference documentation SHALL introduce important subsystem terms clearly instead of assuming prior knowledge.

At minimum, the documentation SHALL define or explain recurring terms such as gateway-capable session, live gateway bindings, attach contract, request admission, managed-agent epoch, reconciliation, and not-attached state before relying on them heavily.

#### Scenario: Reader encounters gateway terms with enough context
- **WHEN** a new user or developer encounters gateway-specific terminology in the reference subtree
- **THEN** the page or subtree entrypoint explains that terminology in accessible language
- **AND THEN** the documentation does not rely on unexplained gateway jargon as the only way to understand gateway behavior

### Requirement: Gateway reference pages link to the centralized system-files reference when discussing broader session-root storage
Gateway docs SHALL explain gateway contracts, queueing, lifecycle, and artifacts such as `attach.json`, `state.json`, queue state, and event logs. They SHALL link to the centralized system-files reference for nesting under runtime-managed session roots, relationships to other Houmao-owned roots, and filesystem preparation that extends beyond the gateway.

#### Scenario: Gateway docs explain local gateway artifacts and link out for the broader runtime tree
- **WHEN** a reader opens the gateway reference to understand attach metadata, state files, or queue artifacts
- **THEN** the gateway docs explain those gateway-specific files directly
- **AND THEN** they point to the centralized system-files reference for the broader runtime-root and session-root filesystem map

#### Scenario: Gateway docs stay focused on gateway behavior instead of duplicating the full filesystem reference
- **WHEN** a maintainer uses the gateway reference to understand queueing, attachability, or recovery behavior
- **THEN** the gateway docs remain focused on gateway semantics
- **AND THEN** they do not need to duplicate the full Houmao-owned filesystem model to explain those gateway behaviors

### Requirement: Gateway reference documentation covers the shared mailbox facade
The gateway reference SHALL make the `/v1/mail/*` facade discoverable from its entrypoint. It SHALL introduce the shared mailbox surface on an operator or maintainer page in the gateway subtree before or alongside the route contract.

#### Scenario: Reader finds mailbox facade guidance from the gateway subtree
- **WHEN** a reader opens the gateway reference to understand current gateway capabilities
- **THEN** the gateway docs make the mailbox facade discoverable from the gateway entry path
- **AND THEN** the reader can reach a page that explains why `/v1/mail/*` exists and how it relates to manifest-backed adapter resolution

#### Scenario: Gateway docs explain transport-backed mailbox adaptation
- **WHEN** a maintainer uses the gateway reference to understand mailbox behavior for attached sessions
- **THEN** the gateway docs explain that the shared mailbox routes are backed by transport-specific adapters resolved from the attached session metadata
- **AND THEN** the docs do not describe the shared gateway contract as if it were hard-wired to the filesystem transport alone

#### Scenario: Reader Can Trace Mailbox Capability and Transport
- **WHEN** a reader needs to establish how a mailbox operation reaches a session
- **THEN** the docs present `/v1/mail/*` as the shared contract for supported mailbox operations and trace capability from `attach.json` to the runtime-managed session manifest
- **AND THEN** the docs explain that the facade constructs an adapter for the filesystem or Stalwart transport and that direct transport-specific behavior may be available without a live attached gateway

### Requirement: Gateway reference documentation explains current mailbox facade boundaries

The gateway reference SHALL explain the v1 mailbox facade's caller authority, live availability, and role in notifier polling. It SHALL link to the mailbox reference for mailbox semantics and to the system-files reference for file placement.

#### Scenario: Reader can distinguish gateway capability from live mailbox-facade availability

- **WHEN** a reader needs to understand why a session is gateway-capable but does not currently expose mailbox routes
- **THEN** the gateway docs explain the difference between stable attachability metadata and a live gateway endpoint
- **AND THEN** the reader can identify the binding and caller requirements for `/v1/mail/*` in the current deployment

#### Scenario: Gateway docs explain notifier behavior through the shared mailbox facade

- **WHEN** a maintainer reads the gateway docs to understand mailbox notifier behavior
- **THEN** the docs explain that notifier unread checks use the same shared mailbox facade used for mailbox reads
- **AND THEN** the docs describe transport-specific state through the mailbox reference

#### Scenario: Reader Can Determine Mailbox Caller Authority
- **WHEN** a reader checks which authorization a mailbox operation requires
- **THEN** the reference explains that enrolled administrators and callers under a valid empty roster can use every supported mailbox action on the selected binding
- **AND THEN** it documents distinct grants for keyed non-admins, including operator-origin post, binding controls, and owner-local attachment paths, along with the path validation that applies to every caller

### Requirement: Gateway operational docs explain outside-tmux tmux-session targeting
Gateway operations docs SHALL distinguish the local registry alias from verified self and explicit agent selectors. They SHALL explain the fresh registry lookup and how to disambiguate it.

#### Scenario: Reader can choose between current-session and tmux-session targeting

- **WHEN** a reader wants to attach a gateway outside the owning tmux session
- **THEN** the docs show `agents single --target-tmux-session <session> gateway attach`
- **AND THEN** the docs show `agents self gateway attach` for current-session authority

#### Scenario: Reader understands tmux-session targeting authority and limits

- **WHEN** multiple fresh local records share one tmux session alias
- **THEN** the docs direct the reader to the candidate agent IDs
- **AND THEN** the docs explain that aliases apply to the local registry

#### Scenario: Reader can distinguish pair-authority port selection from gateway listener port selection

- **WHEN** a reader needs a different pair authority or listener
- **THEN** the docs distinguish `--pair-port` with explicit agent selectors from the lower-level gateway listener port

### Requirement: Gateway reminder reference documentation explains prompt and send-keys delivery
The gateway reference SHALL explain semantic `prompt` and raw `send_keys` reminder delivery through a page reachable from `docs/reference/gateway/index.md`. It SHALL document raw input grammar, Enter handling, backend support, and how the CLI, managed proxy, and direct API expose the live reminder model.

#### Scenario: Reader can distinguish prompt reminders from send-keys reminders
- **WHEN** a reader opens the gateway reminder reference documentation
- **THEN** the page explains that reminders may deliver either semantic prompt text or raw control input
- **AND THEN** the page does not present send-keys reminders as ordinary prompt text with special characters in it

#### Scenario: Reader learns ensure-enter default and exact-key opt-out
- **WHEN** a reader opens the gateway reminder reference documentation
- **THEN** the page explains that `ensure_enter` defaults to `true`
- **AND THEN** it also explains that exact special-key reminders such as `<[Escape]>` should set `ensure_enter=false`

#### Scenario: Reader sees backend and CLI boundaries clearly
- **WHEN** a reader opens the gateway reminder reference documentation
- **THEN** the page explains that send-keys reminders depend on backend raw-control support while the CLI, pair-managed proxy, and direct `/v1/reminders` routes all project the same live reminder behavior
- **AND THEN** it keeps the direct live route family positioned as the lower-level contract rather than the only documented operator surface

#### Scenario: Reader Constructs a Raw Control Reminder
- **WHEN** a reader checks how to send raw control input as a reminder
- **THEN** the reference explains its purpose and defines `send_keys.sequence` using the exact `<[key-name]>` grammar
- **AND THEN** the reference limits submitted input to that sequence and the optional Enter action, with `send_keys.ensure_enter` defaulting to `true`
- **AND THEN** it states that the reminder `title` and semantic `prompt` stay outside the raw delivery
- **AND THEN** it identifies `houmao-mgr agents gateway reminders ...` and `/houmao/agents/{agent_ref}/gateway/reminders...` as higher-level access to the same model and direct `/v1/reminders` as the route for exact payload inspection and debugging

### Requirement: Gateway reminder reference docs cover CLI, proxy, and direct reminder surfaces together
The gateway reminder docs SHALL explain when to use the operator CLI, pair-managed proxy, or direct live API for the same reminder model. They SHALL explain how CLI placement flags map to numeric ranking.

#### Scenario: Reader learns the CLI-first reminder workflow from the gateway reference
- **WHEN** a reader opens the gateway reminder operations page to learn how to create or inspect reminders
- **THEN** the page introduces `houmao-mgr agents gateway reminders ...` as the preferred operator surface
- **AND THEN** the page does not present direct `/v1/reminders` HTTP as the only supported way to work with reminders

#### Scenario: Maintainer can still find the underlying direct reminder contract
- **WHEN** a maintainer opens the gateway reminder operations page to inspect payload and route semantics
- **THEN** the page still points them to the exact `/v1/reminders` contract and representative payloads
- **AND THEN** the page explains how the higher-level CLI and pair-managed proxy surfaces map onto that lower-level contract

#### Scenario: Reader Uses Managed Reminder Access or CLI Placement
- **WHEN** a reader needs to operate on reminders through pair authority
- **THEN** the docs identify `/houmao/agents/{agent_ref}/gateway/reminders...` as the proxy and explain how to use it without discovering the live listener
- **AND THEN** the docs describe `--before-all` and `--after-all` as CLI conveniences that keep the underlying ranking numeric

### Requirement: Gateway reference documents diagnostic logging
The gateway reference SHALL explain opt-in diagnostic logging, its role alongside human-oriented `gateway.log`, file placement, retention, event coverage, default redaction, and deduplication of consecutive warnings and errors. It SHALL explain how diagnostic logs relate to durable gateway artifacts and how cleanup treats diagnostic files.

#### Scenario: Operator can find and interpret diagnostic logs
- **WHEN** an operator opens the gateway reference after enabling gateway diagnostic logging
- **THEN** the documentation identifies the diagnostic log location and file rotation behavior
- **AND THEN** the documentation explains how to interpret request, validation, mailbox, and dedup summary entries at the level needed for postmortem debugging

#### Scenario: Documentation states the redaction boundary
- **WHEN** a maintainer reads the gateway diagnostic logging documentation
- **THEN** the documentation states that diagnostic logs do not include mailbox bodies, raw prompts, attachment contents, authorization headers, cookies, bearer tokens, credential material, or environment secrets by default
- **AND THEN** the documentation points readers to durable gateway artifacts when queue or notifier state, rather than diagnostic logs, is the authoritative source of truth

#### Scenario: Operator Finds Diagnostic Storage and Cleanup Rules
- **WHEN** an operator needs to locate or clean up diagnostic files
- **THEN** the reference identifies the gateway-owned log directory and explains how rotation and retained backups bound disk use
- **AND THEN** it explains cleanup behavior and the role of `queue.sqlite`, `events.jsonl`, `state.json`, and manifests alongside diagnostic logs

### Requirement: Gateway reference explains pending-input state and prompt admission decisions

Gateway contracts and operations SHALL distinguish provider-native pending input, composer drafts, durable gateway requests, and Houmao prompt-submission notes. The reference SHALL describe `surface.pending_input`, supported admission policies, and conservative handling of unknown observations. Internals SHALL explain that each admission decision uses the latest tracked snapshot and how several calls can dispatch before provider repaint.

#### Scenario: Contract page distinguishes the three queue-like concepts

- **WHEN** a reader opens the gateway prompt-control contract documentation
- **THEN** the page distinguishes provider-native pending input, gateway-durable work, and user-authored composer draft text
- **AND THEN** it does not describe any one of them as authoritative for the others

#### Scenario: Operations page presents the admission decision table

- **WHEN** an operator needs to choose a direct prompt admission policy
- **THEN** the gateway operations reference shows when each policy dispatches or refuses for ready, busy-no-pending, busy-pending, and unknown observations
- **AND THEN** it explains which availability and compatibility failures remain enforceable

#### Scenario: Internals page rejects an atomic-reservation interpretation

- **WHEN** a maintainer studies closely spaced if-no-pending submissions
- **THEN** the gateway internals reference explains observation-to-repaint behavior and the absence of a pending-slot reservation
- **AND THEN** it identifies the provider TUI observation as the authority for later decisions

#### Scenario: Operator Checks Supported Prompt Policies
- **WHEN** an operator checks which direct prompt policy applies
- **THEN** the reference presents `ready_only`, `if_no_pending`, and `always` in a policy table with conservative unknown handling
- **AND THEN** it documents the structural checks all policies enforce, the TUI-only scope of non-default policies, and the removal of binary force behavior

### Requirement: Gateway reference documents access classes and public handoff

The gateway reference SHALL explain policy decisions for verified callers, target domains, resources, and actions. It SHALL describe endpoint-bound signing and verified remote transport. It SHALL document public notifications and prompts, policy labeling, handoff-only responses, and permitted reply channels.

#### Scenario: Caller wants to use a public prompt

- **WHEN** a reader follows the public prompt example
- **THEN** the example identifies the expected HTTP handoff result and shows how to request a separate policy-permitted reply

#### Scenario: Operator deploys with private certificate trust

- **WHEN** a reader configures a gateway across hosts using deployment-provisioned trust
- **THEN** the reference explains the bind, connect, and advertised addresses, endpoint certificate verification, and independent caller credential selection

#### Scenario: Managed agent needs to use its private gateway

- **WHEN** a reader follows the agent's private mailbox example
- **THEN** it uses a scoped `houmao-mgr agents self ...` command that handles the signed challenge internally
- **AND** the example keeps the key and proof out of agent-visible instructions

#### Scenario: Operator reads endpoint access metadata

- **WHEN** a reader inspects the live gateway descriptor
- **THEN** the reference explains `admin_mode`, supported proof and challenge information, enabled public actions, and the limits of cached discovery

#### Scenario: Operator grants one operation to an enrolled caller

- **WHEN** a reader wants to authorize a caller for one operation on a selected agent
- **THEN** the reference shows how to select the principal, target domain, resource, and action
- **AND THEN** it explains the distinct authority for local execution, scoped peer actions, and configured service identities

#### Scenario: Operator enrolls a peer under a different account

- **WHEN** the source agent is stopped or runs under another OS account
- **THEN** the reference shows how the target owner enrolls its approved logical identity and public key
- **AND THEN** the example explains that source placement and relaunch do not change the grant, while key revocation or replacement changes usable proof

### Requirement: Gateway reference documents admin enrollment and live membership

The gateway reference SHALL document initial owner provisioning, first-key registration, the SSHSIG challenge, and per-key admin enrollment and removal. It SHALL explain that a valid empty roster opens the full target-domain gateway-admin role and that unavailable policy fails closed.

#### Scenario: Admin enrolls after a keyless launch

- **WHEN** a reader follows post-start enrollment guidance for a gateway initialized with no keys
- **THEN** the example signs the first-key challenge and shows how enrolled callers prove their identity for allowed operations

#### Scenario: Admin considers removing the last key

- **WHEN** a reader follows the removal workflow
- **THEN** the documented outcome explains that every supported client-facing action in the target domain reopens, including owner-file mail attachments and installed plugin actions
- **AND THEN** it explains that owner-local policy administration, OS ownership, internal service identities, and each operation's ordinary guards retain their own requirements

#### Scenario: An operator rotates the only administrator key

- **WHEN** a reader wants to replace the final administrator key while the target stays keyed
- **THEN** the reference shows enrolling the replacement as admin before removing the old admin entry
- **AND THEN** it explains that ordinary keys do not keep a target keyed and distinguishes admin removal from credential revocation

#### Scenario: Operator compares open and keyed access

- **WHEN** a reader evaluates the effect of enrolling the first administrator
- **THEN** the reference explains that the enrolled administrator retains the same target-domain permissions that every caller had under the valid empty roster
- **AND THEN** it shows that a keyed non-admin can use its scoped grants and receives a refusal for actions outside its effective permissions

#### Scenario: Operator upgrades a gateway with an empty roster

- **WHEN** a reader checks the effect of upgrading a keyless gateway
- **THEN** the reference explains how to manually initialize current owner policy with the intended administrators or a deliberately empty roster
- **AND THEN** it explains that older authorization formats fail closed and require operator reprovisioning and updates to clients and plugins

### Requirement: Gateway reference documents owner-local Web browser entry

The gateway reference SHALL document immediate open-mode entry, keyed terminal login, and open or signed ticket issuance through the API and scoped CLI. It SHALL explain selection of an enrolled signer with `web.enter` permission, bearer handling, expiry, owner-loopback reachability, and the native provider's responsibility for authenticated browser sessions.

#### Scenario: An operator follows the Web entry instructions

- **WHEN** a reader needs to open a live managed Web agent in keyed mode
- **THEN** the reference shows how to open the bare entry URL, optionally select a local key file, and run the generated command with `ssh-keygen` and `curl`
- **AND THEN** it describes trusted endpoint review, blank-path SSH agent selection, automatic browser continuation, and starting again after expiry
- **AND THEN** it explains trimming of surrounding whitespace and SSH-agent selection when trimming leaves the field empty

#### Scenario: A script requests a Web entry ticket

- **WHEN** a reader follows the API or scoped CLI workflow
- **THEN** the reference shows how to obtain a one-time link unsigned in open mode and with proof from an enrolled signer authorized for `web.enter` in keyed mode
- **AND THEN** it tells the operator to keep the link private and explains native session selection after redemption

#### Scenario: The browser runs outside the execution context

- **WHEN** a reader configures access from another machine or network namespace
- **THEN** the reference explains the required gateway and native loopback forwards with exact addresses and ports, including the terminal callback's gateway address
- **AND THEN** it distinguishes this workflow from the advertised HTTPS gateway and explains that native session lifetime follows provider policy

#### Scenario: An operator opens a gateway with no keys

- **WHEN** a reader follows the bare owner-local entry URL for a live Web agent with a valid empty roster
- **THEN** the reference describes immediate entry into the native UI without an interactive sign-in step

### Requirement: Gateway reference documents the operator dashboard

The gateway reference SHALL show how to find the live gateway address and open its dashboard at the base URL. It SHALL explain the displayed summary, when the Web action appears, and how to reach an owner-local gateway from another execution context.

#### Scenario: An operator looks for a live Web agent

- **WHEN** a reader follows the dashboard instructions
- **THEN** the reference gives an owner-local URL example and explains immediate entry in verified open mode and sign-in with an enrolled signer authorized for Web entry in keyed mode

#### Scenario: An operator opens the dashboard through the advertised address

- **WHEN** a reader needs Web entry from an advertised proxy deployment
- **THEN** the reference explains the owner-local connection or private TCP forwards needed for browser entry

### Requirement: Gateway Reference Documents Web and Headless Prompt Readiness

The gateway reference SHALL document how an authorized driver uses `GET /v1/status` to observe prompt readiness for Web and headless agents. The procedure SHALL distinguish gateway health, managed prompt readiness, and plugin connection, and SHALL describe the readiness snapshot as preflight evidence for a later admission decision.

#### Scenario: Driver Checks Either Surface Before a Prompt

- **WHEN** a driver reads the readiness procedure for an attached managed Web or headless agent
- **THEN** it learns to check for a healthy gateway and a current `observation` with `can_accept_prompt_now: true`
- **AND THEN** it can find Web details under `web` and headless diagnostics at `GET /v1/control/headless/state` by selecting the known surface

#### Scenario: Readiness Evidence Is Missing or Changes

- **WHEN** the driver has missing, stale, or unknown readiness evidence, or the body becomes busy after a ready observation
- **THEN** the procedure treats missing or stale evidence as unconfirmed and explains that each prompt or ordinary event is subject to live admission at handoff

#### Scenario: CCCC Driver Checks Its Setup

- **WHEN** a CCCC driver checks readiness for an ordinary chat exercise
- **THEN** the CCCC guide links to the gateway procedure and explains how to verify the selected CCCC binding and its connection independently

### Requirement: Gateway Plugin Guides Report Declared Compatibility

The CCCC integration and gateway plugin author references SHALL report gateway SDK compatibility and Houmao dependency constraints consistent with the distributions they document. The CCCC reference SHALL identify the CCCC external-receiver protocol version separately from the gateway SDK version.

#### Scenario: Operator Checks CCCC Installation Requirements

- **WHEN** an operator consults either reference to install the current optional CCCC package or the example plugin
- **THEN** the reference reflects the corresponding SDK and Houmao dependency declarations and identifies their source
- **AND THEN** the CCCC reference identifies the separate provider protocol required for receiver qualification
