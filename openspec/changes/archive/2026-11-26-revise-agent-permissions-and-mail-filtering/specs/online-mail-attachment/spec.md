# Online Mail Attachment Delta

## MODIFIED Requirements

### Requirement: Existing agents can attach externally provisioned online mail

Supported CLI and API controls SHALL attach an online account using provider endpoint, address, login identity, and a protected credential reference. Attachment SHALL work with a keyed or open gateway. Stalwart attachment SHALL require mailbox-level access only and SHALL not provision domains/accounts, require management credentials, inspect provider delivery filters, or replace a password supplied by the account owner.

#### Scenario: Hub account attaches to a mailbox-disabled body

- **WHEN** an authorized caller supplies valid Stalwart mailbox credentials for a running agent
- **THEN** its online binding becomes usable for read and send
- **AND THEN** its agent ID, body process, and conversation remain unchanged

#### Scenario: Agent retains offline mail

- **WHEN** an offline member attaches online mail
- **THEN** its offline binding, address ownership, and messages remain unchanged
- **AND THEN** its canonical mail identity becomes the online address

#### Scenario: Stalwart is attached after first-key enrollment

- **WHEN** an authorized administrator attaches a ready Stalwart account to a keyed running agent
- **THEN** the binding becomes available with ordinary mailbox credentials
- **AND THEN** gateway and direct operations retain their individual caller and owner authorization checks

#### Scenario: First-key enrollment occurs after Stalwart attachment

- **WHEN** first-key enrollment succeeds for an open gateway with an online binding
- **THEN** it becomes keyed without retiring, replacing, or degrading that binding
- **AND THEN** authorized callers can continue to inspect, read, send, refresh, and reconnect under the keyed policy
- **AND THEN** enabled online notification uses the provider's current Inbox and ordinary admission

#### Scenario: A keyed gateway starts with an existing binding

- **WHEN** a keyed agent starts or reattaches its gateway with a ready configured online binding
- **THEN** the gateway can use that binding under its current owner, credential, origin, account, and revision checks

## ADDED Requirements

### Requirement: Online attachment keeps protected policy authority separate

Online attachment SHALL keep the mailbox binding and the optional protected mail-policy authority separate. Ordinary attachment SHALL use mailbox-level credentials. Protected operation SHALL require a qualified provider-native control path that files matching new arrivals directly in Archive for the exact bound account. That path SHALL stay isolated from the gateway runtime.

#### Scenario: An ordinary account lacks a protected control path

- **WHEN** an authorized operator attaches a ready provider account without an independent trusted management path
- **THEN** ordinary mailbox attachment and use remain available
- **AND THEN** a later request to apply protected policy reports unsupported operation

#### Scenario: A gateway uses a protected online binding

- **WHEN** a gateway attaches or reconnects its ordinary runtime client to a qualified protected binding
- **THEN** the runtime receives only its authorized mailbox capabilities
- **AND THEN** the independent control path retains the credentials and authority for protected rule and placement changes
