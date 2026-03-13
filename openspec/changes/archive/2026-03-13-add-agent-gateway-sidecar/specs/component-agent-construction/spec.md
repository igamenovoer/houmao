## MODIFIED Requirements

### Requirement: Optional agent blueprints bind brain and role
The system MAY support "agent blueprints" that bind a brain recipe and a role into a named agent definition. Blueprints MUST remain secret-free.

Blueprints MAY additionally include an optional secret-free `gateway` configuration section. In this change, that section MAY declare `gateway.host` and `gateway.port` as the default HTTP gateway listener address for gateway attach actions affecting sessions launched from that blueprint.

In v1, `gateway.host` and `gateway.port` are the only supported gateway keys in that section.

Blueprint parsing for this change SHALL use a strict typed schema that rejects unknown top-level fields and unknown nested gateway fields rather than silently ignoring them.

Blueprint-declared gateway listener defaults SHALL NOT, by themselves, enable gateway behavior for sessions launched from that blueprint.

#### Scenario: Blueprint binds brain, role, and optional gateway listener defaults without secrets
- **WHEN** an agent blueprint is defined with `gateway.host: 127.0.0.1` and `gateway.port: 43123`
- **THEN** it SHALL reference a brain recipe and a role by identifier or path
- **AND THEN** it MAY provide `gateway.host` and `gateway.port` as default gateway-attach listener values
- **AND THEN** it SHALL NOT include credential material inline

#### Scenario: Blueprint gateway defaults do not imply gateway auto-attach
- **WHEN** an agent blueprint defines `gateway.host` or `gateway.port`
- **AND WHEN** a developer launches a session from that blueprint without explicitly requesting gateway attach
- **THEN** the runtime treats those values only as dormant defaults
- **AND THEN** the session does not gain a live gateway instance solely because the blueprint declared listener defaults

#### Scenario: Invalid blueprint gateway listener fields are rejected
- **WHEN** an agent blueprint declares an invalid `gateway.host` value or an invalid `gateway.port` value such as a non-integer or out-of-range port
- **THEN** the system fails blueprint validation with an explicit error
- **AND THEN** the runtime does not treat those invalid values as usable gateway-listener defaults

#### Scenario: Unknown top-level blueprint fields are rejected
- **WHEN** an agent blueprint declares an unsupported top-level field for this schema version
- **THEN** the system fails blueprint validation with an explicit error
- **AND THEN** the runtime does not silently ignore that field

#### Scenario: Unknown nested gateway fields are rejected
- **WHEN** an agent blueprint declares an unsupported nested field under `gateway` other than `host` or `port`
- **THEN** the system fails blueprint validation with an explicit error
- **AND THEN** the runtime does not silently ignore that nested gateway field
