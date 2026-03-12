## MODIFIED Requirements

### Requirement: Optional agent blueprints bind brain and role
The system MAY support "agent blueprints" that bind a brain recipe and a role into a named agent definition. Blueprints MUST remain secret-free.

Blueprints MAY additionally include an optional secret-free `gateway` configuration section. In this change, that section MAY declare `gateway.host` and `gateway.port` as the default HTTP gateway listener address for sessions launched from that blueprint.

#### Scenario: Blueprint binds brain, role, and optional gateway listener defaults without secrets
- **WHEN** an agent blueprint is defined with `gateway.host: 127.0.0.1` and `gateway.port: 43123`
- **THEN** it SHALL reference a brain recipe and a role by identifier or path
- **AND THEN** it MAY provide `gateway.host` and `gateway.port` as default launch-time HTTP gateway listener values
- **AND THEN** it SHALL NOT include credential material inline

#### Scenario: Invalid blueprint gateway listener fields are rejected
- **WHEN** an agent blueprint declares an invalid `gateway.host` value or an invalid `gateway.port` value such as a non-integer or out-of-range port
- **THEN** the system fails blueprint validation with an explicit error
- **AND THEN** the runtime does not treat those invalid values as usable gateway-listener defaults
