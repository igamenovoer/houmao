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
Each detailed agent gateway reference page SHALL be understandable to first-time readers while still preserving the exact technical details needed for implementation, debugging, or maintenance.

At minimum, each detailed gateway reference page SHALL include:

- a short explanation of what the page covers,
- plain-language framing or mental-model guidance before dense technical detail,
- the relevant exact technical specifics, constraints, or contracts,
- at least one concrete example, representative payload, or artifact shape where it materially helps understanding.

#### Scenario: New reader can orient before reading exact gateway contracts
- **WHEN** a first-time reader opens a detailed agent gateway reference page
- **THEN** the page first explains the purpose of the topic in accessible language
- **AND THEN** the reader can build an intuitive mental model before encountering the full technical detail

#### Scenario: Developer can still find exact gateway specifics
- **WHEN** a developer opens a detailed agent gateway reference page to answer an implementation or debugging question
- **THEN** the page includes the exact gateway constraints, contracts, or artifact details relevant to that topic
- **AND THEN** the page is not limited to high-level explanatory prose alone

### Requirement: Important gateway procedures include embedded Mermaid sequence diagrams
When an agent gateway reference page introduces an important procedure involving multiple participants or steps, the page SHALL include an embedded Mermaid `sequenceDiagram` block directly in the Markdown page.

These diagrams SHALL accompany the prose explanation rather than replace it.

Important gateway procedures include at minimum:

- launch-time auto-attach or attach-later flows,
- request acceptance and queued execution flows,
- detach, restart, or stale-live-binding cleanup flows,
- recovery or reconciliation flows where managed-agent continuity changes the result.

#### Scenario: Procedure page includes an embedded sequence diagram
- **WHEN** a gateway reference page introduces an important gateway procedure
- **THEN** that page includes an embedded Mermaid `sequenceDiagram` block in the Markdown content
- **AND THEN** the diagram appears alongside the written explanation of the procedure

#### Scenario: Diagram supplements rather than replaces the written procedure
- **WHEN** a reader uses the documentation to understand an important gateway procedure
- **THEN** the page provides both prose explanation and a Mermaid sequence diagram
- **AND THEN** the reader is not required to infer the full procedure from the diagram alone

### Requirement: Gateway contract documentation covers the implemented v1 gateway surfaces
The agent gateway contract documentation SHALL describe the implemented v1 gateway surfaces that readers must follow.

At minimum, that contract coverage SHALL include:

- the distinction between gateway-capable and currently gateway-attached sessions,
- stable attachability metadata versus live gateway bindings,
- the strict attach contract and tmux-published environment pointers,
- desired listener versus live listener concepts,
- the implemented HTTP routes and request kinds,
- the versioned status model and current status axes,
- durable gateway state artifacts and their responsibilities,
- current validation and error semantics that are observable in the implemented v1 flow.

The gateway contract documentation SHALL reflect current implemented behavior and SHALL NOT imply unsupported live-adapter coverage or unimplemented request behavior as though it were already available.

#### Scenario: Contract documentation covers attach, status, and request surfaces
- **WHEN** a reader needs the normative gateway reference for current v1 behavior
- **THEN** the gateway contract pages describe attach metadata, live env bindings, the HTTP surface, request kinds, and the status model
- **AND THEN** the reader does not need to reconstruct those contracts only from scattered source files

#### Scenario: Contract documentation stays within implemented v1 scope
- **WHEN** a reader uses the gateway reference docs to understand supported behavior
- **THEN** the documentation makes clear the currently implemented v1 scope and boundaries
- **AND THEN** the docs do not describe future extensibility as if it were already implemented behavior

### Requirement: Gateway operational documentation covers lifecycle and operator-facing workflows
The agent gateway operational documentation SHALL explain how to work with the gateway safely in the implemented v1 flow, including the current managed-agent operator surfaces and the strict current-session attach discovery model.

At minimum, that operational guidance SHALL cover:

- launch-time auto-attach and attach-later behavior,
- attach targeting through explicit selectors and current-session resolution,
- current-session discovery through `HOUMAO_MANIFEST_PATH` with `HOUMAO_AGENT_ID` plus fresh shared-registry fallback,
- the pair-managed registration precondition for current-session attach,
- detach behavior and stop-session interaction,
- status inspection and the difference between offline, unavailable, and live states,
- stale live-binding invalidation or cleanup behavior where relevant to operator workflows,
- operator-facing gateway command families for prompt, interrupt, send-keys, TUI inspection, and mail-notifier control,
- `gateway/run/current-instance.json` as the authoritative same-session live execution record when the gateway is hosted in an auxiliary tmux window,
- the difference between direct runtime control and gateway-routed queued control at the level needed to operate the system correctly.

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

### Requirement: Gateway internal documentation explains queueing, epochs, and recovery boundaries
The agent gateway internal documentation SHALL explain how the gateway sidecar persists state, serializes work, and behaves when managed-agent continuity changes.

At minimum, that internal coverage SHALL include:

- the durable queue and event-log model,
- current-instance state and epoch tracking,
- queue admission and single active execution behavior,
- restart recovery for previously accepted work,
- replay blocking or reconciliation behavior when the managed-agent instance changes,
- the separation between gateway-local health and managed-agent availability,
- the current live-adapter boundary in v1.

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
The agent gateway reference documentation SHALL keep gateway-specific contracts, queue semantics, and lifecycle behavior in the gateway subtree while pointing readers to the centralized system-files reference for the broader Houmao filesystem map.

Gateway pages SHALL continue to document gateway-specific artifacts such as `attach.json`, `state.json`, queue state, and event logs, but they SHALL defer the broader relationship between those files and the surrounding runtime-managed session root to the centralized system-files reference when that broader filesystem map is the main topic.

At minimum, the gateway reference SHALL link to the centralized system-files reference when discussing:

- how gateway files are nested under runtime-managed session roots,
- how gateway artifact paths relate to other Houmao-owned root families,
- filesystem-preparation guidance that extends beyond gateway-specific behavior.

#### Scenario: Gateway docs explain local gateway artifacts and link out for the broader runtime tree
- **WHEN** a reader opens the gateway reference to understand attach metadata, state files, or queue artifacts
- **THEN** the gateway docs explain those gateway-specific files directly
- **AND THEN** they point to the centralized system-files reference for the broader runtime-root and session-root filesystem map

#### Scenario: Gateway docs stay focused on gateway behavior instead of duplicating the full filesystem reference
- **WHEN** a maintainer uses the gateway reference to understand queueing, attachability, or recovery behavior
- **THEN** the gateway docs remain focused on gateway semantics
- **AND THEN** they do not need to duplicate the full Houmao-owned filesystem model to explain those gateway behaviors

### Requirement: Gateway reference documentation covers the shared mailbox facade
The agent gateway reference documentation SHALL document the gateway mailbox facade as a first-class gateway surface rather than leaving mailbox-gateway interaction implicit inside low-level contract pages alone.

At minimum, the gateway reference SHALL explain:

- that `/v1/mail/*` is the shared mailbox surface for supported mailbox operations,
- how the gateway resolves mailbox capability from `attach.json` to the runtime-managed session manifest,
- that the gateway constructs a transport-specific mailbox adapter behind one shared gateway-facing contract,
- that the facade may serve either filesystem-backed or Stalwart-backed sessions,
- that direct transport-specific mailbox behavior may still exist when no live gateway is attached.

The gateway reference SHALL provide an operator-facing or maintainer-facing page under the gateway subtree that introduces this mailbox facade before or alongside the exact route contract page.

#### Scenario: Reader finds mailbox facade guidance from the gateway subtree
- **WHEN** a reader opens the gateway reference to understand current gateway capabilities
- **THEN** the gateway docs make the mailbox facade discoverable from the gateway entry path
- **AND THEN** the reader can reach a page that explains why `/v1/mail/*` exists and how it relates to manifest-backed adapter resolution

#### Scenario: Gateway docs explain transport-backed mailbox adaptation
- **WHEN** a maintainer uses the gateway reference to understand mailbox behavior for attached sessions
- **THEN** the gateway docs explain that the shared mailbox routes are backed by transport-specific adapters resolved from the attached session metadata
- **AND THEN** the docs do not describe the shared gateway contract as if it were hard-wired to the filesystem transport alone

### Requirement: Gateway reference documentation explains current mailbox facade boundaries
The agent gateway reference documentation SHALL explain the current scope and boundaries of the mailbox facade in implemented v1 behavior.

At minimum, that boundary guidance SHALL explain:

- that `/v1/mail/*` remains available only for loopback-bound live gateway listeners,
- that mailbox-facade availability is separate from the existence of stable gateway-capability metadata,
- that mailbox notifier polling reads unread state through the same mailbox facade instead of a transport-local side channel,
- where the gateway reference should defer to the mailbox reference for mailbox semantics and to the system-files reference for broader filesystem placement.

#### Scenario: Reader can distinguish gateway capability from live mailbox-facade availability
- **WHEN** a reader needs to understand why a session is gateway-capable but does not currently expose mailbox routes
- **THEN** the gateway docs explain the difference between stable attachability metadata and a live loopback-bound gateway listener
- **AND THEN** the reader can tell when `/v1/mail/*` is actually available

#### Scenario: Gateway docs explain notifier behavior through the shared mailbox facade
- **WHEN** a maintainer reads the gateway docs to understand mailbox notifier behavior
- **THEN** the docs explain that notifier unread checks use the same shared mailbox facade used for mailbox reads
- **AND THEN** the docs do not present filesystem mailbox-local SQLite polling as the universal notifier contract

### Requirement: Gateway operational docs explain outside-tmux tmux-session targeting
The gateway operational documentation SHALL explain when operators should use `--target-tmux-session` instead of `--current-session` or explicit managed-agent selectors.

That guidance SHALL explain that tmux-session targeting is resolved locally from the addressed tmux session's manifest-backed authority, with fresh shared-registry `terminal.session_name` fallback when the tmux-published manifest pointer is missing or stale.

The operational docs SHALL also explain that tmux-session targeting is a local host workflow and does not make tmux session names part of the remote managed-agent API contract.

When the docs describe explicit pair-managed targeting, they SHALL use the name `--pair-port` for the Houmao pair-authority override and SHALL distinguish that selector from gateway listener port overrides such as lower-level `--gateway-port`.

#### Scenario: Reader can choose between current-session and tmux-session targeting
- **WHEN** a reader needs to attach a gateway from a normal shell outside the owning tmux session
- **THEN** the gateway operations docs explain that `--target-tmux-session` is the correct selector for that workflow
- **AND THEN** the docs explain that `--current-session` remains the inside-tmux same-session path

#### Scenario: Reader understands tmux-session targeting authority and limits
- **WHEN** a reader needs to understand how `--target-tmux-session` finds the target session
- **THEN** the gateway operations docs explain the manifest-first resolution path with shared-registry tmux-alias fallback
- **AND THEN** the docs explain that tmux session names stay local CLI authority hints rather than remote API identifiers

#### Scenario: Reader can distinguish pair-authority port selection from gateway listener port selection
- **WHEN** a reader needs to target an explicit pair-managed authority while using gateway commands
- **THEN** the gateway operations docs explain that `--pair-port` selects the Houmao pair authority
- **AND THEN** the docs explain that gateway listener port overrides belong to lower-level gateway attach surfaces rather than `houmao-mgr agents gateway ...`

### Requirement: Gateway reminder reference documentation explains prompt and send-keys delivery
The agent gateway reference documentation SHALL explain gateway reminders as supporting two different delivery kinds:

- semantic `prompt`
- raw `send_keys`

That reminder documentation SHALL explain:

- the purpose of `send_keys` reminders,
- that `send_keys.sequence` uses the exact `<[key-name]>` raw control-input grammar,
- that `send_keys` reminders do not submit reminder `title` or semantic `prompt` text,
- that `send_keys.ensure_enter` defaults to `true`,
- that `ensure_enter=false` is required for exact special-key-only reminders such as `<[Escape]>`,
- that send-keys reminder support is limited by the current gateway backend's raw-control capability,
- that reminders remain direct live gateway HTTP and do not introduce a new `houmao-mgr agents gateway reminders ...` CLI family.

The documentation SHALL present that explanation in a gateway reminder reference page or equivalent gateway-reference entry path that is discoverable from `docs/reference/gateway/index.md`.

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
- **THEN** the page explains that send-keys reminders depend on backend raw-control support and remain on the direct live `/v1/reminders` surface
- **AND THEN** it does not imply that a new reminder CLI family already exists

