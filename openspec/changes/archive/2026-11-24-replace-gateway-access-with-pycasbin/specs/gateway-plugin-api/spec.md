# Gateway Plugin API Delta

## MODIFIED Requirements

### Requirement: Plugin route authority is declared and enforced by the host

Each plugin HTTP route SHALL declare a namespaced action through the SDK. The host SHALL authorize it on the selected instance resource before invoking the handler. Missing or invalid declarations SHALL fail the instance before resource activation. The host SHALL include every supported action of installed plugins in the target domain's gateway-admin role, including under a valid empty roster. It SHALL administer the self role separately.

#### Scenario: Private plugin route admits self and admin

- **WHEN** owner policy grants an enrolled caller the action declared for the selected plugin instance
- **THEN** the host permits normal instance and operation admission under the existing owner binding

#### Scenario: Undeclared route is called by self

- **WHEN** a plugin registers an HTTP route without a namespaced action declaration
- **THEN** the host rejects the affected instance before the route can be called

#### Scenario: Admin plugin route follows open access

- **WHEN** an anonymous caller invokes a custom plugin action under a valid empty administrator roster
- **THEN** the host authorizes it through the open gateway-admin role and applies the normal instance and operation checks
- **AND THEN** the call retains anonymous provenance and the plugin continues to use its configured service identity

#### Scenario: Enrolled admin uses an installed plugin action

- **WHEN** an enrolled administrator proves its identity and invokes a supported custom action of an installed plugin in the target domain
- **THEN** the host authorizes the action through the gateway-admin role with the same instance and operation checks as in open mode

#### Scenario: Plugin declares an unsupported authority

- **WHEN** staged plugin routes use an invalid namespace or a resource outside the selected instance
- **THEN** the affected instance fails registration before credentials, connections, or workers activate
- **AND** unrelated valid instances and permitted core operations remain available

#### Scenario: A plugin action grant is specific to one instance

- **WHEN** owner policy grants a non-admin caller in keyed mode a plugin action for one instance and the caller requests it on a different instance without a corresponding grant
- **THEN** the host returns HTTP 403 before invoking plugin code

#### Scenario: A plugin documents a required permission

- **WHEN** a plugin developer declares an action needed by a client
- **THEN** the host authorizes installed actions through the current gateway-admin role and the owner can grant the action to scoped non-admin callers for the intended instance
- **AND THEN** the declaration gives the plugin no authority to administer principals, grants, or internal service identities

### Requirement: Authenticated plugin routes preserve owner and caller separation

Admitted plugin calls SHALL retain the configured owner, service binding, provider credential, and ordinary-event dispatch contract. The initiating HTTP principal and the plugin sender SHALL have distinct provenance. The host SHALL keep caller credentials out of plugin contexts.

#### Scenario: Remote CCCC caller sends ordinary chat or Mail

- **WHEN** an authorized caller invokes a CCCC chat or Mail action for the selected instance
- **THEN** the configured gateway owner's Group and Actor remain authoritative
- **AND** backend-specific delivery, consumption, cursor, and uncertain-outcome semantics remain unchanged

#### Scenario: Self calls plugin connection management

- **WHEN** a self caller requests connect, disconnect, reconnect, or credential refresh without the corresponding instance action grant
- **THEN** HTTP 403 is returned before changing connection state or refreshing a source

#### Scenario: Remote request claims another plugin owner

- **WHEN** a caller provides an alternate sender, provider credential, or service binding through ordinary request content
- **THEN** the plugin rejects that override under the existing owner-bound contract

### Requirement: Route admission precedes plugin lifecycle error handling

The gateway SHALL apply current policy for the requested action and instance before exposing plugin lifecycle, registration, or connection failures. Sanitized host-owned plugin status SHALL remain available to admitted callers without invoking external service code.

#### Scenario: Unauthenticated caller probes a failed instance

- **WHEN** an uncredentialed caller requests a failed plugin operation that requires proof
- **THEN** the response is HTTP 401 without exposing its failure details

#### Scenario: Authorized caller inspects a failed instance

- **WHEN** an authorized caller requests the host-owned status of a failed plugin
- **THEN** it receives the existing sanitized failure snapshot independently of plugin health

#### Scenario: Anonymous caller inspects a failed instance

- **WHEN** an unsigned caller with open gateway-admin permission for host-owned plugin status requests a failed instance
- **THEN** it receives the existing sanitized failure snapshot
