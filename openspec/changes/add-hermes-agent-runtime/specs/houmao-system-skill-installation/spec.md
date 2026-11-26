# Spec Delta

## MODIFIED Requirements

### Requirement: Shared installer projects complete public skills into supported tool homes
The shared installer SHALL project complete standalone public skill directories at the tool-native top-level skill root for Claude, Codex, Copilot, Kimi, and the universal Agent Skills target. Managed Hermes homes SHALL use the same pack projection under the private Hermes skill root.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Shared routines and both loop skills SHALL remain top-level siblings of the selected actor entrypoint. The complete manifest-declared child inventory SHALL remain parent-scoped below `houmao-shared-routines/subskills/`. Copy SHALL remain the default mode, managed homes SHALL use copy, and explicit symlink mode SHALL link each complete standalone source directory.

#### Scenario: Codex admin pack uses static top-level paths
- **WHEN** the admin pack is installed into a Codex home
- **THEN** all five admin-pack members appear as top-level siblings under `skills/`
- **AND THEN** no entrypoint-local composition tree is created

#### Scenario: Kimi managed home receives the static agent pack
- **WHEN** Houmao installs the managed default into a Kimi Code CLI home
- **THEN** all four agent-pack members appear as top-level siblings under `skills/`
- **AND THEN** the full shared child inventory remains below the shared-routines sibling

#### Scenario: Hermes Managed Home Receives the Selected Packs

- **WHEN** managed launch resolves a system-skill pack for a Hermes agent
- **THEN** the private native skill root contains the complete selected top-level skill directories
- **AND THEN** shared child skills remain parent-scoped and the agent can discover the selected skills through its native loader
