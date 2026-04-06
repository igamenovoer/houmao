## ADDED Requirements

### Requirement: CLI reference documents the top-level project agents presets surface

The `houmao-mgr` CLI reference SHALL document `project agents presets` as the supported low-level preset management surface.

At minimum, that coverage SHALL:

- list `project agents presets list|get|add|set|remove`,
- describe preset files as living under `agents/presets/<name>.yaml`,
- explain that `project agents roles` is prompt-only role management,
- state that `project agents roles scaffold` is not part of the supported low-level CLI.

#### Scenario: Reader sees named presets in the project agents reference
- **WHEN** a reader looks up `houmao-mgr project agents` in the CLI reference
- **THEN** the page documents `project agents presets list|get|add|set|remove`
- **AND THEN** it describes those commands as operations on `agents/presets/<name>.yaml`
- **AND THEN** it does not present `roles presets ...` or `roles scaffold` as the supported surface
