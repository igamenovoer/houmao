# gateway-recipient-mail-filtering Specification

## Purpose

Let a mailbox owner apply rules through the gateway while a trusted mail backend controls filing and keeps the recipient’s rules private.

## Requirements

### Requirement: Gateway Relays Independently Authorized Mail Rule Updates

The gateway SHALL relay `POST /v1/mail/{channel}/policy/apply` to the trusted backend or its connector. The backend SHALL verify current owner authority and a signature covering the operation, backend, binding or registration, expected revision, operation ID, and exact rules. It SHALL separately authenticate direct owner submissions and receipt verification. Owner credential management SHALL stay outside gateway authority.

#### Scenario: An owner applies rules through a keyed gateway

- **WHEN** an authorized gateway relay caller submits a valid owner-signed update for the selected binding and current rule revision
- **THEN** the backend applies the signed mail rules to that binding
- **AND THEN** the owner can verify the applied revision and outcome independently of the gateway

#### Scenario: A gateway admin lacks independent owner authority

- **WHEN** a caller presents only ordinary gateway administrator or mailbox credentials, or a signature from a revoked owner credential
- **THEN** the backend rejects the protected effect
- **AND THEN** the same independent authorization is required in open gateway mode

#### Scenario: An update is stale or targets a different operation

- **WHEN** a signed update names a stale revision, another backend or binding, or a different operation or payload
- **THEN** the backend leaves the current rule state intact
- **AND THEN** an authorized exact retry recovers the recorded outcome without applying the operation again

#### Scenario: A mailbox is reconnected or replaced

- **WHEN** the gateway reconnects to the same backend binding or the operator replaces that binding
- **THEN** the same binding uses its committed rules and revision
- **AND THEN** detaching or replacing the gateway binding leaves its previous backend policy and placements intact
- **AND THEN** a replacement backend binding starts without those rules and rejects operations signed for the previous binding

### Requirement: Recipient Rules and Placement Stay Within the Mail Authority

The gateway SHALL keep retained peer roles, grants, keys, and fallback settings in its local authorization authority. It SHALL relay only the mail rule payload for the selected binding. The backend SHALL limit rule and placement disclosure to independently authorized access for that mailbox and trusted backend administration. Ordinary receipts, status, and diagnostics SHALL omit rule contents, matches, and filing outcomes.

#### Scenario: The same address appears in a different policy context

- **WHEN** an owner applies an exact normalized sender address rule to one binding
- **THEN** the backend scopes it to that binding and transport
- **AND THEN** the address supplies no gateway principal identity or grant

#### Scenario: A submission reaches recipients with different rules

- **WHEN** the backend accepts a message for multiple recipients and their rules select different placements
- **THEN** the sender receives the normal transport acceptance for the accepted recipients
- **AND THEN** sender-facing replies, ordinary peer credentials, and runtime filesystem permissions do not expose another mailbox's rules, matches, or folders

### Requirement: Protected Filtering Requires Backend Placement Authority

A backend SHALL offer protected filtering only when it can enforce direct Archive delivery with rule and placement authority isolated from gateway runtime credentials. The filesystem backend SHALL route protected writes through an independently controlled writer with exclusive access to authoritative state. An online backend SHALL use provider-native rules under separately managed credentials.

#### Scenario: A gateway attempts to override a protected placement

- **WHEN** a gateway uses its runtime identity, ordinary provider or registry credentials, or direct CLI access to try to change rules or protected folder placement
- **THEN** the backend denies the unauthorized effect
- **AND THEN** the runtime identity lacks an alternate path through folder moves, archive, archived-state updates, or writable filesystem state

#### Scenario: A backend cannot enforce the requested behavior

- **WHEN** the filesystem store allows shared writes or the online provider lacks the required native behavior or credential isolation
- **THEN** the protected operation reports unsupported
- **AND THEN** the gateway leaves ordinary mailbox access subject to its existing binding and access checks

#### Scenario: The recipient gateway stops

- **WHEN** mail arrives under an independently applied policy while the recipient gateway is stopped
- **THEN** placement follows the committed backend rule and the transport’s supported sender match
- **AND THEN** the result remains authoritative after gateway restart

#### Scenario: The trusted filesystem writer is unavailable

- **WHEN** a protected filesystem operation cannot reach its trusted writer
- **THEN** it reports unavailability or an uncertain prior result as appropriate
- **AND THEN** no gateway or direct CLI path writes to the store as a fallback

### Requirement: Blocking Files New Mail Directly Into Archive

A qualified backend SHALL file new mail matching the committed block rule directly into the affected recipient’s Archive at delivery, without Inbox membership. The sender’s copy and other recipients’ placement SHALL remain independent. Rule changes SHALL apply to future delivery and leave existing mail in its current folders.

#### Scenario: New mail matches a committed block rule

- **WHEN** the backend accepts a new message that matches a recipient’s committed block rule
- **THEN** the backend commits the message directly into that recipient’s Archive with no Inbox membership
- **AND THEN** the separately authorized mailbox owner can review it through backend Archive access

#### Scenario: The owner blocks a sender with mail already in Inbox

- **WHEN** the backend applies a block rule for a sender whose messages are already in Inbox
- **THEN** existing Inbox mail remains in place
- **AND THEN** the rule applies to subsequent deliveries

#### Scenario: The owner unblocks a sender

- **WHEN** the backend applies a new rule revision that removes a block
- **THEN** later mail from that sender follows normal backend delivery
- **AND THEN** earlier archived mail stays in Archive

### Requirement: Agent Work Uses the Authoritative Inbox

Gateway work listing, work reads, and reminder eligibility SHALL use the current backend Inbox and the established mailbox permissions and reminder modes. The gateway SHALL relay protected policy updates. The backend SHALL enforce filing at delivery. Gateway reports of policy outcomes SHALL distinguish confirmed, refused, unsupported, and uncertain backend results.

#### Scenario: Filtered mail arrives in Archive

- **WHEN** the backend delivers a matching new message directly to Archive
- **THEN** ordinary Inbox work listings exclude that message
- **AND THEN** the message does not trigger reminders or compaction

#### Scenario: A queued reminder refers to mail now outside Inbox

- **WHEN** the gateway prepares to hand off a queued reminder or serves a work read for a previous Inbox reference
- **THEN** it uses current backend Inbox membership to determine eligibility
- **AND THEN** a stale work reference does not expose mail that has left Inbox

#### Scenario: The gateway loses the backend’s response

- **WHEN** the gateway cannot verify that a protected request committed
- **THEN** it reports an uncertain outcome
- **AND THEN** the owner can query the trusted backend independently for the operation record and applied revision
