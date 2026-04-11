## ADDED Requirements

### Requirement: docs site includes internals graph CLI reference page

The docs site SHALL include a reference page at `docs/reference/cli/internals.md` that documents the `houmao-mgr internals graph` command family.

The page SHALL document the `graph high` subgroup with one entry per command: `analyze`, `packet-expectations`, `validate-packets`, `slice`, and `render-mermaid`. For each command the page SHALL include a description, the full option table, and at least one usage example.

The page SHALL document the `graph low` subgroup with one entry per command: `create`, `mutate`, `relabel`, `compose`, `subgraph`, `reverse`, and `ego`. For each command the page SHALL include a description and the key options.

The page SHALL document the `graph low alg` subgroup with a shared option schema table followed by a summary table of all supported algorithm subcommands: `ancestors`, `descendants`, `descendants-at-distance`, `topological-sort`, `is-dag`, `cycles`, `weak-components`, `strong-components`, `condensation`, `transitive-reduction`, `dag-longest-path`, `shortest-path`, and `all-simple-paths`.

The page SHALL state that all graph commands accept NetworkX node-link JSON as input via `--input` and emit NetworkX node-link JSON or structured result payloads, and that `-` may be used to read from stdin.

The page SHALL include context explaining when agents and operators would use `graph high` commands (loop plan authoring and validation) versus `graph low` commands (low-level graph construction and NetworkX algorithm access).

#### Scenario: Reader finds graph high analyze documentation

- **WHEN** a reader navigates to `docs/reference/cli/internals.md`
- **THEN** they find the `graph high analyze` command with its `--input`, `--root`, `--mode`, `--include-unreachable`, and `--format` options described
- **AND THEN** they find at least one usage example showing how to run `analyze` against a node-link JSON file

#### Scenario: Reader finds graph high packet-expectations and validate-packets

- **WHEN** a reader looks up how to generate or validate pairwise-v2 routing packets using CLI tooling
- **THEN** the internals reference page documents `graph high packet-expectations` and `graph high validate-packets` with their required inputs and output shape

#### Scenario: Reader can identify graph low alg commands without reading source

- **WHEN** a reader consults `docs/reference/cli/internals.md` for low-level graph algorithm access
- **THEN** they find all 13 supported algorithm subcommands listed in the summary table
- **AND THEN** they find the shared option schema described once rather than duplicated per subcommand

### Requirement: docs/index.md links to internals reference page

The docs site index at `docs/index.md` SHALL include a link to `docs/reference/cli/internals.md` in the CLI surfaces reference section alongside the existing `houmao-mgr`, `houmao-server`, and related entries.

#### Scenario: Reader discovers internals from the docs index

- **WHEN** a reader scans the CLI surfaces section of `docs/index.md`
- **THEN** they find an entry for `houmao-mgr internals` with a link to `reference/cli/internals.md`

### Requirement: houmao-mgr.md includes an internals section

`docs/reference/cli/houmao-mgr.md` SHALL include a `### internals` section in its command-groups listing that describes the top-level `internals` group purpose and links to the dedicated `internals.md` reference page.

#### Scenario: Reader navigating houmao-mgr.md discovers internals group

- **WHEN** a reader browses the command groups section of `docs/reference/cli/houmao-mgr.md`
- **THEN** they find an `### internals` section that names the group and provides a link to `internals.md`
- **AND THEN** they do not need to discover the internals group by running `houmao-mgr --help`

### Requirement: system-skills-overview notes graph tooling for loop skills

`docs/getting-started/system-skills-overview.md` SHALL include a note in or near the loop-skills section that `houmao-mgr internals graph high` commands (`analyze`, `packet-expectations`, `validate-packets`, `slice`, `render-mermaid`) are available as deterministic structural helpers for `houmao-agent-loop-pairwise-v2` and `houmao-agent-loop-generic` authoring.

The note SHALL link to `docs/reference/cli/internals.md` for the full reference.

#### Scenario: Agent reading system-skills-overview discovers graph tooling

- **WHEN** an agent reads the loop-skills section of `docs/getting-started/system-skills-overview.md`
- **THEN** it finds a reference to `houmao-mgr internals graph high` as an available authoring aid
- **AND THEN** it finds a link to the full internals reference page
