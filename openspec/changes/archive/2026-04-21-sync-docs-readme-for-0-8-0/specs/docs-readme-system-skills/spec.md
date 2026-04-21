## MODIFIED Requirements

### Requirement: README §4 introduces all loop skill options

The README `§4 Agent Loop` section SHALL mention all four packaged loop skills before or alongside the detailed pairwise walkthrough. That mention SHALL use a compact table or a brief list with one-line descriptions, and SHALL link to `docs/getting-started/loop-authoring.md` for the skill-selection guide.

The existing pairwise worked example SHALL be retained as the canonical entry-level walkthrough.

The four skills identified SHALL be `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-pairwise-v3`, and `houmao-agent-loop-generic`. Any narrative sentence in §4 that states how many loop skills ship SHALL state four rather than three.

#### Scenario: Reader in the README loop section discovers the loop authoring guide

- **WHEN** a reader reads the README §4 Agent Loop section
- **THEN** they see all four loop skill options identified
- **AND THEN** they find a link to `docs/getting-started/loop-authoring.md` for guidance on which skill to use

#### Scenario: Existing README pairwise example is preserved

- **WHEN** a reader follows the README §4 Agent Loop section step by step
- **THEN** the pairwise loop walkthrough (specialists, plan template, Mermaid control graph, operate the run) is still present as the detailed worked example

#### Scenario: README §4 narrative count matches catalog loop-skill count

- **WHEN** a reader reads any sentence in §4 that enumerates the number of packaged loop skills
- **THEN** that sentence says four, not three
- **AND THEN** the table or list shows `houmao-agent-loop-pairwise-v3` alongside the other three loop skills

### Requirement: README system-skills table enumerates every catalog entry
The README "System Skills: Agent Self-Management" subsection SHALL document every system skill listed under `[skills.*]` in `src/houmao/agents/assets/system_skills/catalog.toml`.

At minimum the table SHALL include one row for each of the following skills currently shipped by the catalog:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-adv-usage-pattern`
- `houmao-utils-llm-wiki`
- `houmao-utils-workspace-mgr`
- `houmao-touring`
- `houmao-mailbox-mgr`
- `houmao-memory-mgr`
- `houmao-project-mgr`
- `houmao-specialist-mgr`
- `houmao-credential-mgr`
- `houmao-agent-definition`
- `houmao-agent-loop-pairwise`
- `houmao-agent-loop-pairwise-v2`
- `houmao-agent-loop-pairwise-v3`
- `houmao-agent-loop-generic`
- `houmao-agent-instance`
- `houmao-agent-inspect`
- `houmao-agent-messaging`
- `houmao-agent-gateway`

The "What it enables" column SHALL describe each skill in operator-facing language and SHALL avoid claiming a skill exists when it is not present in the catalog.

The row for `houmao-agent-loop-pairwise-v3` SHALL describe it as the workspace-aware pairwise loop authoring and run-control skill, consistent with the canonical one-line description in `docs/getting-started/system-skills-overview.md`.

#### Scenario: README row count matches catalog size
- **WHEN** a reader compares the README system-skills table to `src/houmao/agents/assets/system_skills/catalog.toml`
- **THEN** every `[skills.<name>]` block in the catalog has exactly one corresponding row in the README table
- **AND THEN** the README table contains no row for a skill that is not declared in the catalog

#### Scenario: Workspace manager is surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains `houmao-utils-workspace-mgr`
- **AND THEN** the row describes the skill as a utility for planning and executing multi-agent workspace layouts before launch

#### Scenario: Pairwise-v3 is surfaced in the README catalog
- **WHEN** a reader opens the README "System Skills" subsection
- **THEN** the table contains `houmao-agent-loop-pairwise-v3`
- **AND THEN** the row describes the skill as the workspace-aware pairwise loop authoring and run-control skill
- **AND THEN** the row is placed immediately adjacent to `houmao-agent-loop-pairwise-v2` so the v1 / v2 / v3 progression is visually obvious

### Requirement: README auto-install wording includes all pairwise variants when `core` includes them
When the README describes the managed-home or CLI-default system-skill expansions, that wording SHALL include every pairwise loop-skill variant currently packaged in the `core` set of `src/houmao/agents/assets/system_skills/catalog.toml`.

Until the catalog is revised, that wording SHALL explicitly include `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-pairwise-v3`, and SHALL NOT imply that only one or two pairwise variants are auto-installed through `core` or `user-control`.

#### Scenario: README auto-install wording tracks all pairwise variants currently in `core`
- **WHEN** a reader reads the README paragraph describing which skills `agents launch` and `agents join` auto-install
- **THEN** the described `core` (or `user-control`) expansion includes `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-pairwise-v3` when the catalog includes all three
- **AND THEN** the paragraph does not imply that only one or two pairwise variants are auto-installed
