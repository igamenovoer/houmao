# agent-gateway Delta

## MODIFIED Requirements

### Requirement: Shared gateway mailbox facade exposes lifecycle routes
The shared mailbox facade SHALL expose private `GET /v1/mail/status` as a summary of both optional bindings and the derived canonical mail identity. Mailbox-disabled agents SHALL receive a normal empty-binding summary.

The gateway SHALL expose channel-selected lifecycle routes under `/v1/mail/{channel}/` for `list`, `peek`, `read`, `send`, `post`, `reply`, `mark`, `move`, and `archive`, where `channel` is `offline` or `online`. The former unqualified lifecycle routes SHALL NOT infer a channel from the canonical mail identity.

List SHALL return triage metadata without marking read. Peek SHALL return selected content without changing read state. Read SHALL return content and mark read. Mark SHALL support recipient-local read/answered state. Move SHALL update supported boxes. Archive SHALL close inbox work through the selected backend.

All lifecycle requests SHALL identify their expected binding ID, obtained from status or current round context, and use runtime-owned authority and scoped references. A replaced binding SHALL fail explicitly even for send/post requests without a message reference. Unsupported operations, absent bindings, and backend failures SHALL be explicit. Callers SHALL NOT need filesystem indexes, mailbox scripts, or provider-native objects. Ordinary mail operations SHALL use private route admission under the live roster. Operator-origin post and mailbox binding controls SHALL use the admin route class.

#### Scenario: Peek does not mutate read state through the gateway
- **WHEN** a caller peeks through the selected channel using a matching scoped reference
- **THEN** it receives that message's content without changing recipient read state

#### Scenario: Read mutates read state through the gateway
- **WHEN** a caller reads through the selected channel using a matching scoped reference
- **THEN** it receives that message's content and read state becomes true for that mailbox owner

#### Scenario: Archive shortcut remains available
- **WHEN** a caller archives selected references through their matching channel
- **THEN** the selected backend reports them archived and no longer open inbox work

#### Scenario: Channel omission does not use canonical precedence
- **WHEN** a caller uses an unqualified lifecycle operation without selecting a channel
- **THEN** the request fails explicitly instead of selecting the preferred online address

#### Scenario: Empty status remains readable
- **WHEN** an agent has no offline or online binding
- **THEN** summary status reports both slots absent and no canonical mail identity
- **AND THEN** ordinary core status and control remain available

#### Scenario: A new send pins its intended mailbox
- **WHEN** an account is replaced after a caller observes its binding ID but before a send begins
- **THEN** the send fails with a binding conflict
- **AND THEN** it is not submitted from the replacement account

#### Scenario: Authenticated remote admin uses both mail channels

- **WHEN** an authenticated admin uses the explicit offline or online lifecycle route with a current expected binding ID
- **THEN** supported ordinary operations follow the same channel, reference, pagination, and mailbox-state semantics as local access
- **AND** the client needs no shared runtime filesystem

#### Scenario: Remote mailbox binding changes before delivery

- **WHEN** a remote request's expected binding no longer identifies the selected owner mailbox
- **THEN** the operation reports the existing scope conflict without delivery from the replacement binding

#### Scenario: Anonymous caller uses ordinary mail with an empty roster

- **WHEN** an unsigned caller accesses an enabled mailbox operation with a current binding ID while the roster is valid and empty
- **THEN** the gateway applies normal channel, reference, and delivery checks with anonymous caller provenance

### Requirement: Public endpoint discovery reports a minimal descriptor

GET /v1/endpoint SHALL return a secret-free descriptor with target and presence identity, protocol, open or key-required admin access, private access requirements, enabled public operations, and the configured advertised URL if present. It SHALL report `private_proof` as `none` when open, `self_or_admin` when keyed, and `unavailable` when the policy is unavailable. Detailed status SHALL require private access.

#### Scenario: Anonymous caller discovers a protected gateway

- **WHEN** a caller reads the endpoint descriptor without credentials
- **THEN** it receives the current access requirements and enabled public operations
- **AND** detailed status, owner-local paths, and roster contents are absent

#### Scenario: The first key is registered after advertisement

- **WHEN** a caller reads the endpoint descriptor after the first-key registration commits
- **THEN** it reports key-required admin access and `private_proof: self_or_admin`

#### Scenario: The roster is valid and empty

- **WHEN** a caller reads the endpoint descriptor with a valid empty roster
- **THEN** it reports open admin access and `private_proof: none`

#### Scenario: Policy is unavailable

- **WHEN** the live gateway cannot read its required access state
- **THEN** it reports unavailable access for both route classes

### Requirement: Owner-file inputs on private mail routes follow current elevated access

Private send and reply forms with an owner-local attachment path SHALL require current anonymous open access or verified admin proof. A current self caller can use ordinary forms that omit these inputs. The gateway SHALL check path-form authority before filesystem or provider access. Admin-class post SHALL apply its own route admission and attachment validation.

#### Scenario: Self supplies an owner-local file path

- **WHEN** a self caller supplies an owner-local attachment path in send or reply while the roster has keys
- **THEN** the gateway returns HTTP 403 before opening the path or invoking a provider

#### Scenario: Self sends mail without owner-file inputs

- **WHEN** a self caller supplies a valid ordinary send or reply with no owner-local attachment paths
- **THEN** the operation uses the configured mailbox owner and its normal delivery semantics

#### Scenario: Admitted caller attaches an owner-local file

- **WHEN** an admitted caller uses an existing supported local-path attachment form
- **THEN** the path is interpreted in the recorded owner context under existing attachment validation

#### Scenario: An anonymous caller uses an owner-file attachment

- **WHEN** an unsigned caller uses a supported attachment form under a valid empty roster
- **THEN** the gateway rechecks the open grant before applying the existing attachment validation
- **AND THEN** delivery uses the configured mailbox binding and records anonymous caller provenance

## RENAMED Requirements

- FROM: `### Requirement: Owner-file inputs on private mail routes require verified admin proof`
- TO: `### Requirement: Owner-file inputs on private mail routes follow current elevated access`
