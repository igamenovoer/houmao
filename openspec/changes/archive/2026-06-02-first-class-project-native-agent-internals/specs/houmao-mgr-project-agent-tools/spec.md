## REMOVED Requirements

### Requirement: `houmao-mgr project agents tools` mirrors the project-local tool tree
**Reason**: Provider tool/setup trees are native-agent material, not ordinary Houmao project resources.
**Migration**: Use `houmao-mgr internals native-agent tools ... --native-agent-root <path>` for direct native tool/setup management. Use project specialist/profile commands for ordinary project setup selection.

#### Scenario: Tool tree management moves to native-agent internals
- **WHEN** an operator needs to inspect or mutate provider setup bundles directly
- **THEN** the supported internal path is `houmao-mgr internals native-agent tools ...`
- **AND THEN** ordinary project help does not present `project agents tools` as a project resource

### Requirement: `project agents tools <tool> get` and `setups` inspect and manage setup bundles
**Reason**: Direct setup-bundle management belongs to the native-agent internals surface.
**Migration**: Use `houmao-mgr internals native-agent tools <tool> get|setups ...`.

#### Scenario: Setup bundle commands use native-agent root
- **WHEN** an operator adds a native Claude setup bundle
- **THEN** the command targets an explicit native-agent root through `internals native-agent tools claude setups add`
- **AND THEN** it does not require a Houmao project catalog
