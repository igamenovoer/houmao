## ADDED Requirements

### Requirement: Lite skill uses routed pro-shaped operation pages
The packaged `houmao-agent-loop-lite` skill SHALL use `SKILL.md` as an entrypoint and router rather than as the full operation manual.

The lite `SKILL.md` SHALL include activation rules, help text, required root vocabulary, operation names, routing guidance, and global constraints.

The lite package SHALL include operation-specific authoring pages under `subskills/authoring/`.

At minimum, the lite authoring pages SHALL cover:

- `init`
- `create-intention`
- `clarify-intent`
- `clarify-execplan`
- `execplan-fast-forward`
- `execplan-specs-process`
- `execplan-specs-contract`
- `execplan-skills`
- `execplan-agent-bindings`
- `execplan-finalize`
- `validate-execplan`
- `update-execplan`

The lite package SHALL include operation-specific execution pages under `subskills/execution/`.

At minimum, the lite execution pages SHALL cover:

- `prepare-agents`
- `prepare-workspace`
- `validate-loop`
- `launch-agents`
- `start`
- `status`
- `pause`
- `resume`
- `recover`
- `stop`

The lite package SHALL include shared reference pages under `subskills/reference/` for reusable Markdown contract defaults, Markdown template events, direct SQLite state, runtime mail model, platform boundaries, scaffold ownership, and required/optional system input question shape.

The lite package SHALL include scaffold support under `assets/scaffolds/` and `scripts/scaffold.py` for starter intention and Markdown/direct-SQL execplan shells.

Detailed workflow guidance SHALL live in routed pages or reference pages rather than in long sections inside `SKILL.md`.

#### Scenario: Installed lite skill exposes routed pages
- **WHEN** `houmao-agent-loop-lite` is installed into a supported skill home
- **THEN** the installed skill contains `SKILL.md`
- **AND THEN** it contains `subskills/authoring/init.md`
- **AND THEN** it contains `subskills/authoring/execplan-fast-forward.md`
- **AND THEN** it contains `subskills/execution/prepare-agents.md`
- **AND THEN** it contains `subskills/execution/validate-loop.md`
- **AND THEN** it contains `subskills/reference/direct-sqlite-state.md`

#### Scenario: Lite router points to one operation page
- **WHEN** an agent reads `houmao-agent-loop-lite/SKILL.md` for a concrete operation such as `prepare-agents`
- **THEN** the router tells the agent which `subskills/execution/prepare-agents.md` page to read
- **AND THEN** the detailed `prepare-agents` checklist is not duplicated as a long standalone section in `SKILL.md`

### Requirement: Lite generation pipeline mirrors pro without harness or schema-renderer stages
The lite generated execplan workflow SHALL remain stage-based like `houmao-agent-loop-pro`.

The lite `execplan-fast-forward` operation SHALL generate or refresh lite execplan artifacts in this dependency order:

```text
execplan-specs-process
  -> execplan-specs-contract
      -> execplan-skills
          -> execplan-agent-bindings
              -> execplan-finalize
```

The lite workflow SHALL NOT include an `execplan-harness` stage.

The lite process and contract stages SHALL use Markdown files as generated authorities for objective, organization, process, communication, state, workspace, run, participant, and agent-binding concerns when those concerns apply.

The lite communication contract SHALL use typed Markdown templates under `execplan/specs/templates/` instead of JSON schemas or Jinja2 renderers.

The lite state contract SHALL use `execplan/specs/state/schema.sql` plus Markdown direct-use guidance for SQLite initialization, reads, writes, validation, and recovery when durable state is needed.

Lite generated skills SHALL operate against Markdown contracts, typed Markdown templates, and SQLite directly, and SHALL NOT require generated harness commands.

Lite validation SHALL verify the routed lite package shape and the generated Markdown/direct-SQL execplan shape without requiring pro-only JSON schemas, Jinja2 renderers, generated harness commands, or generated docs.

#### Scenario: Lite fast-forward skips harness generation
- **WHEN** a user runs lite `execplan-fast-forward` for a loop with valid intention material
- **THEN** the generated stages include process specs, contract specs, skills, agent bindings, and final metadata
- **AND THEN** the generated stages do not include `execplan-harness`
- **AND THEN** the execplan does not create `execplan/harness/`

#### Scenario: Lite skills use direct SQLite state
- **WHEN** a generated lite skill needs durable state for a run
- **THEN** it follows `execplan/specs/state/README.md` and `execplan/specs/state/schema.sql`
- **AND THEN** it reads or writes the run SQLite database directly
- **AND THEN** it does not call a generated harness command for state access

#### Scenario: Lite validation checks Markdown templates instead of schemas
- **WHEN** lite validation checks generated communication contracts
- **THEN** it verifies the required typed Markdown template prologue and generated receiver-skill coverage
- **AND THEN** it does not require JSON Schema files or Jinja2 renderer files
