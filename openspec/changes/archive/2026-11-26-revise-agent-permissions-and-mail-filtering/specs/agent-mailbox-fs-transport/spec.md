# Filesystem Mailbox Transport Delta

## MODIFIED Requirements

### Requirement: Filesystem transport stores canonical messages as Markdown and projects them into mailbox folders

The filesystem mailbox transport SHALL store one Markdown file per logical message at `messages/<YYYY-MM-DD>/<message-id>.md` and project it into mailbox folders through symlinks. The sender SHALL receive a `sent` projection. Each recipient SHALL receive an `inbox` projection or, for a match under its effective blocklist, an `archive` projection.

#### Scenario: Delivery creates canonical message and recipient inbox projection

- **WHEN** a sender delivers a mailbox message through the filesystem transport and the recipient is eligible for Inbox placement
- **THEN** the system writes one canonical Markdown message file for that logical message
- **AND THEN** it materializes a symlink to that file in the recipient Inbox and the sender Sent folder

#### Scenario: Multi-recipient delivery preserves one logical message id

- **WHEN** a mailbox message is delivered to multiple recipients through the filesystem transport
- **THEN** the system uses one canonical message ID for that delivered message
- **AND THEN** each recipient mailbox projection resolves to the same canonical message file
- **AND THEN** each protected recipient's effective policy independently determines its placement

### Requirement: Filesystem transport is daemon-free and synchronizes writes with lock files

Ordinary shared-filesystem deployments SHALL support delivery and mailbox-state updates without a background process. Protected deployments SHALL route placement writes through the trusted backend. Filesystem writers SHALL combine multi-file updates with transactional SQLite index updates and acquire deterministic locks for all affected addresses in ascending lexicographic full-address order before acquiring `locks/index.lock`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Ordinary agent-facing filesystem mailbox workflows SHALL reach those writes through gateway HTTP or `houmao-mgr agents mail ...` rather than through mailbox-owned scripts. A caller receiving `authoritative: false` SHALL verify the outcome through manager-owned or transport-owned state.

#### Scenario: Sender delivers mail without a helper daemon

- **WHEN** a sender process writes a mailbox message in an ordinary shared-filesystem deployment
- **THEN** the sender performs delivery directly through filesystem and SQLite operations
- **AND THEN** delivery proceeds without a persistent helper daemon

#### Scenario: Ordinary filesystem mailbox workflow uses Houmao-owned surfaces

- **WHEN** an agent sender interacts with a shared filesystem mailbox through the supported ordinary mailbox workflow
- **THEN** that workflow uses the shared gateway facade when present or `houmao-mgr agents mail ...` when it is absent
- **AND THEN** the caller can complete the operation without invoking a mailbox-owned script under `rules/scripts/`

#### Scenario: Submission-only manager fallback does not replace filesystem verification

- **WHEN** an ordinary filesystem mailbox action reaches `houmao-mgr agents mail ...`
- **AND WHEN** the command returns `authoritative: false`
- **THEN** the caller treats the result as request submission
- **AND THEN** the caller verifies the outcome through authoritative mailbox state or a follow-up manager-owned list

#### Scenario: Concurrent writers serialize conflicting mailbox updates

- **WHEN** two sender processes request conflicting updates to the same mailbox address
- **THEN** the transport serializes writes using deterministic lock files
- **AND THEN** every committed delivery exposes complete mailbox projections

#### Scenario: Lock acquisition order avoids deadlock

- **WHEN** a standardized filesystem mailbox write affects multiple mailbox addresses
- **THEN** the Houmao-owned write flow acquires the corresponding address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`
- **AND THEN** failure to obtain the required lock set within its bounded timeout returns an explicit failure before committing delivery

#### Scenario: Missing symlink target causes explicit delivery failure

- **WHEN** a sender attempts delivery to a mailbox address whose `mailboxes/<address>` symlink target is missing or invalid
- **THEN** the filesystem mailbox transport fails that delivery explicitly
- **AND THEN** the original mailbox registration and the other filesystem paths remain intact

## ADDED Requirements

### Requirement: A trusted filesystem publisher enforces protected recipient placement

The filesystem transport SHALL offer protected placement only when the trusted backend has exclusive write authority over policy and placement state and controls peer access to that state. At publication, it SHALL match the authenticated sender against each protected recipient's effective owner-signed blocklist. It SHALL commit matching arrivals directly to Archive and other arrivals to Inbox.

#### Scenario: A message is committed for an offline protected recipient

- **WHEN** a registered sender submits a message to a protected recipient whose gateway is absent
- **THEN** the backend verifies the sender's registered identity and applies the recipient's effective policy before projecting the message
- **AND THEN** the sender receives a transport-level result that omits the recipient policy and individual placement
- **AND THEN** only the committed Inbox placement is eligible for normal Inbox visibility and notification

#### Scenario: A blocked sender's message is filed directly in Archive

- **WHEN** the sender's authenticated address matches the recipient's blocklist at publication
- **THEN** the backend commits the recipient's Archive projection and archived lifecycle state with its index changes
- **AND THEN** the recipient never sees an Inbox projection for that delivery
- **AND THEN** the sender's Sent projection and all recipient projections retain the same canonical message ID

#### Scenario: Shared write access prevents protected operation

- **WHEN** an agent or gateway can directly write authoritative mailbox state or read another mailbox's rules or private placement from the filesystem
- **THEN** the deployment reports protected enforcement as unsupported
- **AND THEN** it makes no protected enforcement claim for legacy shared write access

#### Scenario: A gateway submits a placement change using a runtime credential

- **WHEN** a gateway uses its normal mailbox credential to move, archive, or mark a message as archived in a protected mailbox
- **THEN** the backend rejects the placement change
- **AND THEN** operations authorized solely by that runtime credential remain limited to normal submission, reads, and non-placement mailbox updates

### Requirement: Filesystem blocklist changes apply to subsequent delivery

The trusted filesystem backend SHALL apply each committed blocklist revision to subsequent publication. Applying a revision SHALL preserve the folder placement of every existing message. Ordinary archive or move operations SHALL remain subject to independent backend placement authorization.

#### Scenario: An owner applies a new delivery rule to a sender with existing Inbox mail

- **WHEN** the trusted backend applies an owner-signed rule that blocks a sender with messages already in Inbox
- **THEN** the new delivery rule governs subsequent publication
- **AND THEN** messages already in Inbox retain their placement

#### Scenario: An owner unblocks a sender with archived mail

- **WHEN** the trusted backend applies an owner-signed change that unblocks a sender
- **THEN** subsequent deliveries from that sender can enter Inbox under the effective blocklist
- **AND THEN** previously archived mail retains its placement and canonical message identity

#### Scenario: A repaired mailbox preserves protected placement

- **WHEN** the trusted backend repairs projections or rebuilds mailbox state for protected mail
- **THEN** it preserves recorded Inbox and Archive placement
- **AND THEN** it exposes only the recorded Inbox messages as normal Inbox work
