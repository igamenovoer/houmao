## MODIFIED Requirements

### Requirement: `houmao-server` compatibility is defined within the supported Houmao pair
The compatibility contract for `houmao-server` SHALL be defined as part of the supported `houmao-server + houmao-mgr` replacement pair for `cao-server + cao`.

This capability SHALL NOT require `houmao-server` to support arbitrary external `cao` clients as a public compatibility contract.

Mixed-pair usage such as `houmao-server + cao` SHALL be treated as unsupported in this capability.

#### Scenario: Mixed server-plus-raw-CAO usage is not part of the compatibility promise
- **WHEN** an operator points a raw `cao` client at `houmao-server`
- **THEN** that combination is outside the supported compatibility contract for this capability
- **AND THEN** parity verification for the capability does not need to claim that mixed pair works
