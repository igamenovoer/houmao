# Spec Delta

## ADDED Requirements

### Requirement: Plugin route authority is declared and enforced by the host

Plugin HTTP routes SHALL use private or admin access through the supported SDK. Omitted declarations SHALL use the admin class. Invalid declarations, including public access, SHALL fail the instance before resource activation. The host SHALL apply the matched access class and current admin state before invoking plugin code.

#### Scenario: Private plugin route admits self and admin

- **WHEN** the agent's current self or an admin invokes a plugin route classified as private
- **THEN** the host permits normal instance and operation admission under the existing owner binding

#### Scenario: Undeclared route is called by self

- **WHEN** a self caller invokes a plugin route without an access declaration while the admin list has entries
- **THEN** the host returns HTTP 403 before the plugin handler runs

#### Scenario: Admin plugin route follows open access

- **WHEN** an anonymous caller invokes an admin plugin route while the initialized list is empty
- **THEN** the route may admit it with anonymous provenance
- **AND** a private plugin operation still requires verified proof

#### Scenario: Plugin declares an unsupported authority

- **WHEN** staged plugin routes contain an unknown or public access value
- **THEN** the affected instance fails registration before credentials, connections, or workers activate
- **AND** unrelated valid instances and classified core routes remain available

### Requirement: Authenticated plugin routes preserve owner and caller separation

Admitted plugin calls SHALL retain the configured owner, service binding, provider credential, and ordinary-event dispatch contract. The initiating HTTP principal and the plugin sender SHALL have distinct provenance. The host SHALL keep caller credentials out of plugin contexts.

#### Scenario: Remote CCCC caller sends ordinary chat or Mail

- **WHEN** current self or an admin invokes a private CCCC chat or Mail route
- **THEN** the configured gateway owner's Group and Actor remain authoritative
- **AND** backend-specific delivery, consumption, cursor, and uncertain-outcome semantics remain unchanged

#### Scenario: Self calls plugin connection management

- **WHEN** a self caller requests connect, disconnect, reconnect, or credential refresh on a key-required admin plugin route
- **THEN** HTTP 403 is returned before changing connection state or refreshing a source

#### Scenario: Remote request claims another plugin owner

- **WHEN** a caller provides an alternate sender, provider credential, or service binding through ordinary request content
- **THEN** the plugin rejects that override under the existing owner-bound contract

### Requirement: Plugin background resources share the secured deployment boundary

A selected plugin's activation and ordinary background dispatch SHALL use the validated gateway deployment policy. Broader listeners with valid settings SHALL support the same supervised resources as loopback listeners. Background workers SHALL use their configured service authority independently of HTTP caller admission.

#### Scenario: Broader listener receives a service event

- **WHEN** a running plugin on a validated broader listener receives an ordinary service event
- **THEN** existing readiness, current-body, and confirmed-handoff checks determine delivery
- **AND** the background worker uses its service authority

#### Scenario: Invalid deployment is rejected before plugin import

- **WHEN** a broader listener lacks validated access configuration
- **THEN** selected plugin code is not imported and service resources do not activate

### Requirement: Route admission precedes plugin lifecycle error handling

The gateway SHALL apply the route's current admission policy before exposing plugin lifecycle, registration, or connection failures. Sanitized host-owned plugin status SHALL remain available to admitted callers without invoking external service code.

#### Scenario: Unauthenticated caller probes a failed instance

- **WHEN** an uncredentialed caller requests a failed plugin's private or key-required admin route
- **THEN** the response is HTTP 401 without exposing its failure details

#### Scenario: Authorized caller inspects a failed instance

- **WHEN** an authorized caller requests the host-owned status of a failed plugin
- **THEN** it receives the existing sanitized failure snapshot independently of plugin health

