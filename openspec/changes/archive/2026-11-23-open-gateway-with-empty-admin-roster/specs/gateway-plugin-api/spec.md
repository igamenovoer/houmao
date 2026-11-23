# gateway-plugin-api Delta

## MODIFIED Requirements

### Requirement: Plugin route authority is declared and enforced by the host

Plugin HTTP routes SHALL use private or admin access through the supported SDK. Omitted declarations SHALL use the admin class. Invalid declarations, including public access, SHALL fail the instance before resource activation. The host SHALL apply the matched access class and current roster before invoking plugin code. A valid empty roster permits unsigned calls to both classes.

#### Scenario: Private plugin route admits self and admin

- **WHEN** the agent's current self or an admin invokes a plugin route classified as private
- **THEN** the host permits normal instance and operation admission under the existing owner binding

#### Scenario: Undeclared route is called by self

- **WHEN** a self caller invokes a plugin route without an access declaration while the admin list has entries
- **THEN** the host returns HTTP 403 before the plugin handler runs

#### Scenario: Admin plugin route follows open access

- **WHEN** an anonymous caller invokes an admin plugin route while the initialized list is empty
- **THEN** the host admits it with anonymous provenance
- **AND** an unsigned private plugin operation also receives anonymous admission

#### Scenario: Plugin declares an unsupported authority

- **WHEN** staged plugin routes contain an unknown or public access value
- **THEN** the affected instance fails registration before credentials, connections, or workers activate
- **AND** unrelated valid instances and classified core routes remain available

### Requirement: Route admission precedes plugin lifecycle error handling

The gateway SHALL apply the route's current admission policy before exposing plugin lifecycle, registration, or connection failures. Sanitized host-owned plugin status SHALL remain available to admitted callers without invoking external service code.

#### Scenario: Unauthenticated caller probes a failed instance

- **WHEN** an uncredentialed caller requests a failed plugin's private or admin route while the roster has keys
- **THEN** the response is HTTP 401 without exposing its failure details

#### Scenario: Authorized caller inspects a failed instance

- **WHEN** an authorized caller requests the host-owned status of a failed plugin
- **THEN** it receives the existing sanitized failure snapshot independently of plugin health

#### Scenario: Anonymous caller inspects a failed instance

- **WHEN** an unsigned caller requests the host-owned status of a failed plugin while the roster is valid and empty
- **THEN** it receives the existing sanitized failure snapshot
