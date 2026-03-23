## ADDED Requirements

### Requirement: Repository SHALL provide a Stalwart and Cypht interactive gateway demo pack under `scripts/demo/`
The repository SHALL include a self-contained interactive demo-pack directory under `scripts/demo/` for Stalwart-backed gateway mail flows with Cypht-based operator inspection.

For this version, the demo-pack SHALL cover only Stalwart-backed sessions and SHALL NOT include a filesystem-mailbox variant.

The demo pack SHALL include, at minimum:

- `README.md`
- `run_demo.sh`
- tracked demo parameters describing the two demo identities and mailbox bindings
- helper scripts needed to start, inspect, and stop the demo
- pack-owned output artifacts or state files that let follow-up commands target the same live sessions and gateways

#### Scenario: Demo-pack layout exists
- **WHEN** a developer inspects the interactive demo-pack directory under `scripts/demo/`
- **THEN** the required runner, documentation, tracked inputs, and helper-script files are present

### Requirement: Demo-pack start flow SHALL bring up the local email stack and ensure at least two real mailbox accounts
The demo-pack start flow SHALL bring up the repository-owned local email stack under `dockers/email-system/` before attempting gateway-backed mail interaction.

The start flow SHALL ensure at least two mailbox accounts exist for the interactive demo, including one Alice account and one Bob account, using the repository-owned Stalwart provisioning helper rather than undocumented manual mailbox creation.

Those ensured accounts SHALL be usable as real mailbox logins for Cypht inspection during the demo.

#### Scenario: Start flow provisions demo accounts against the running local stack
- **WHEN** a developer starts the interactive demo with the default tracked parameters
- **THEN** the runner starts or verifies the local Stalwart, Postgres, and Cypht stack
- **AND THEN** it ensures the tracked Alice and Bob mailbox accounts exist before session startup continues
- **AND THEN** those accounts are usable for subsequent Cypht login and mailbox inspection

### Requirement: Demo-pack SHALL start two Stalwart-backed sessions and attach one loopback gateway to each
The interactive demo-pack SHALL start two live mailbox-enabled sessions, one for Alice and one for Bob, using the `stalwart` mailbox transport.

This change SHALL NOT introduce filesystem-mailbox transport branching into the interactive demo flow.

Each started session SHALL use explicit mailbox binding inputs for:

- mailbox address,
- mailbox login identity,
- mailbox principal identity or equivalent runtime binding identity.

The demo-pack SHALL attach one live loopback gateway to each session so both sides expose the shared gateway mailbox facade during the demo.

#### Scenario: Alice and Bob sessions start with distinct Stalwart mailbox bindings
- **WHEN** a developer starts the interactive demo
- **THEN** the runner starts one Alice session and one Bob session with distinct Stalwart-backed mailbox bindings
- **AND THEN** each session has its own attached loopback gateway
- **AND THEN** both gateways expose the shared `/v1/mail/*` surface for their respective mailbox-backed sessions

### Requirement: Demo-pack command surface SHALL support multi-turn gateway mail exchange across the same live sessions
The demo-pack runner SHALL preserve enough demo-owned state to let the operator reuse the same live Alice and Bob sessions and gateways across multiple follow-up commands.

At minimum, the runner SHALL support commands equivalent to:

- starting the environment,
- sending mail from one side to the other through the sender's gateway mailbox facade,
- checking unread mail for either side through that side's gateway mailbox facade,
- inspecting current gateway or demo state,
- stopping the environment cleanly.

The operator SHALL be able to run that send and check flow for multiple turns without recreating the environment between turns.

#### Scenario: Multi-turn interactive exchange reuses the same live sessions
- **WHEN** a developer sends mail from Alice to Bob, checks Bob's unread mail, then sends mail from Bob back to Alice
- **THEN** the demo-pack reuses the same previously started Alice and Bob sessions and gateways
- **AND THEN** the exchange can continue for additional turns until the operator stops the demo

### Requirement: Receiver-side unread checks SHALL print normalized unread message content through the gateway mailbox facade
The interactive demo-pack SHALL provide a receiver-side check flow that prints unread message content in a stable demo-visible format by calling the receiver gateway's shared mailbox facade.

That printed output SHALL be based on normalized gateway mailbox results rather than on direct Stalwart-native object inspection and rather than on requiring the managed agent model to summarize the message in its own terminal.

At minimum, the printed unread output SHALL include enough information for the operator to identify:

- sender,
- subject,
- message reference,
- message body content or body preview.

#### Scenario: Receiver unread check prints message content from gateway-normalized results
- **WHEN** Bob has unread mail delivered from Alice and the operator runs the receiver-side unread check
- **THEN** the demo-pack queries Bob's gateway mailbox facade for unread mail
- **AND THEN** it prints normalized unread message content for the operator without requiring direct Stalwart API inspection

### Requirement: Interactive demo behavior SHALL keep unread-only notifier semantics explicit
The interactive demo-pack SHALL teach and preserve the existing unread-only gateway notifier contract in this real-email workflow.

For the demo, that means:

- notifier behavior is driven by unread mail,
- unchanged unread sets may deduplicate across poll cycles,
- notifier bookkeeping does not itself mark mail as read,
- operator or client actions that read mail through the actual mail system may change later unread results.

The demo-pack SHALL NOT treat “one delivered message” as equivalent to “one required notifier event.”

#### Scenario: Unchanged unread mail does not require repeated notification
- **WHEN** unread mail remains present for a receiver session and the unread set does not change between notifier polls
- **THEN** the demo-pack treats notifier deduplication as valid behavior
- **AND THEN** it does not require the gateway to emit a fresh notification for every poll interval

#### Scenario: Reading mail through the real mail system changes later unread behavior
- **WHEN** the operator reads the unread message in Cypht for one of the demo accounts
- **THEN** later gateway unread checks reflect the changed unread state from the real mail system
- **AND THEN** the demo-pack does not treat gateway notifier bookkeeping as a substitute for mailbox read truth

### Requirement: Demo-pack README SHALL document the two-account Stalwart and Cypht workflow explicitly
The demo-pack README SHALL document:

- the purpose of the demo,
- that this version of the demo is Stalwart-only and does not cover filesystem mailboxes,
- prerequisites for Docker, Pixi, tmux, and credentials,
- how the local email stack is started,
- which demo accounts are used and how they are logged into through Cypht,
- how Alice and Bob sessions and gateways are started,
- how to send mail and check unread content through the gateway surfaces,
- how Cypht fits into the manual inspection and read-state story,
- how unread-only notifier behavior should be interpreted during the demo,
- how to stop and clean up the environment.

#### Scenario: Reader can follow the documented Stalwart and Cypht workflow without hidden assumptions
- **WHEN** a developer follows the README for the interactive demo-pack
- **THEN** they can start the local email stack, log into Cypht for Alice and Bob, start the two gateway-backed sessions, exchange messages, inspect unread content, and stop the environment without relying on undocumented setup steps
