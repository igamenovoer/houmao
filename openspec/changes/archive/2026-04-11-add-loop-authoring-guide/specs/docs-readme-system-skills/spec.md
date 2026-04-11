## ADDED Requirements

### Requirement: README surfaces internals graph as a discoverable command group

The `README.md` CLI Entry Points section SHALL include a discoverable reference to `houmao-mgr internals graph` — either as a note on the `houmao-mgr` row or as a separate line. The reference SHALL state that `internals graph` provides loop-plan graph analysis and packet validation tooling.

#### Scenario: Reader discovers internals graph from the README

- **WHEN** a reader scans the README CLI Entry Points section
- **THEN** they find a reference to `houmao-mgr internals graph` with a brief description of its purpose
- **AND THEN** they are not required to read source code or run `houmao-mgr --help` to discover this surface

### Requirement: README §4 introduces all three loop skill options

The README `§4 Agent Loop` section SHALL mention all three packaged loop skills before or alongside the detailed pairwise walkthrough. That mention SHALL use a compact table or a brief list with one-line descriptions, and SHALL link to `docs/getting-started/loop-authoring.md` for the skill-selection guide.

The existing pairwise worked example SHALL be retained as the canonical entry-level walkthrough.

#### Scenario: Reader in the README loop section discovers the loop authoring guide

- **WHEN** a reader reads the README §4 Agent Loop section
- **THEN** they see all three loop skill options identified
- **AND THEN** they find a link to `docs/getting-started/loop-authoring.md` for guidance on which skill to use

#### Scenario: Existing README pairwise example is preserved

- **WHEN** a reader follows the README §4 Agent Loop section step by step
- **THEN** the pairwise loop walkthrough (specialists, plan template, Mermaid control graph, operate the run) is still present as the detailed worked example
