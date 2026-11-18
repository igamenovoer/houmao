# Spec Delta

## ADDED Requirements

### Requirement: Plugin route authority is declared and enforced by the host

Plugin HTTP routes SHALL declare peer or operator access through the supported SDK contract. Omitted declarations SHALL require operator authority. Invalid declarations SHALL fail the affected instance before resource activation. The host SHALL enforce access on the matched route before invoking plugin code; plugin namespace membership and HTTP method SHALL NOT confer ordinary authority.

#### Scenario: Ordinary route admits a peer

- **WHEN** an authenticated peer invokes a valid plugin route explicitly classified for peers
- **THEN** the host permits normal instance and operation admission under the existing owner binding

#### Scenario: Undeclared route is called by a peer

- **WHEN** a peer invokes a plugin route without an access declaration
- **THEN** the host returns HTTP 403 before the plugin handler runs

#### Scenario: Plugin declares an unsupported authority

- **WHEN** staged plugin routes contain an unknown access value
- **THEN** the affected instance fails registration before credentials, connections, or workers activate
- **AND** unrelated valid instances and classified core routes remain available

### Requirement: Authenticated plugin routes preserve owner and caller separation

Authenticated remote plugin calls SHALL retain the configured owner, service binding, credential reference, and existing ordinary-event dispatch contract. Caller provenance SHALL remain separate from plugin sender identity. An HTTP credential SHALL NOT replace provider credentials or acquire privileged event-dispatch options.

#### Scenario: Remote CCCC caller sends ordinary chat or Mail

- **WHEN** a peer invokes an explicitly classified ordinary CCCC chat or Mail route
- **THEN** the configured gateway owner's Group and Actor remain authoritative
- **AND** backend-specific delivery, consumption, cursor, and uncertain-outcome semantics remain unchanged

#### Scenario: Peer calls plugin connection management

- **WHEN** a peer requests connect, disconnect, reconnect, or credential refresh on an operator-classified plugin route
- **THEN** HTTP 403 is returned before changing connection state or refreshing a source

#### Scenario: Remote request claims another plugin owner

- **WHEN** a caller provides an alternate sender, provider credential, or service binding through ordinary request content
- **THEN** the plugin rejects that override under the existing owner-bound contract

### Requirement: Plugin background resources share the secured deployment boundary

A selected plugin's activation and ordinary background dispatch SHALL use the gateway's trusted-local or authenticated deployment policy. Authenticated broader listeners SHALL support the same supervised resources as local listeners. Background workers SHALL retain their configured service authority independently of any HTTP caller and SHALL NOT obtain caller credentials through the plugin context.

#### Scenario: Authenticated listener receives a service event

- **WHEN** a running plugin on an authenticated broader listener receives an ordinary service event
- **THEN** existing readiness, current-body, and confirmed-handoff checks determine delivery
- **AND** there is no unconditional loopback rejection or HTTP-credential requirement for that background worker

#### Scenario: Invalid deployment is rejected before plugin import

- **WHEN** a broader listener lacks valid authenticated deployment
- **THEN** selected plugin code is not imported and service resources do not activate

### Requirement: Authentication precedes plugin lifecycle error handling

An authenticated gateway SHALL verify callers before exposing plugin lifecycle, registration, or connection failures through custom routes. Sanitized host-owned plugin status SHALL remain available to authorized callers without invoking external service code.

#### Scenario: Unauthenticated caller probes a failed instance

- **WHEN** a caller without valid credentials requests a failed plugin's status or custom route
- **THEN** the response is HTTP 401 without exposing its failure details

#### Scenario: Authorized caller inspects a failed instance

- **WHEN** an authorized caller requests the host-owned status of a failed plugin
- **THEN** it receives the existing sanitized failure snapshot independently of plugin health

