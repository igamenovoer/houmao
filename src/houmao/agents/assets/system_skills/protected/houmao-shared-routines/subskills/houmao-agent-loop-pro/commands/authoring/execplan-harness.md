# Execplan Harness

## Read First

- `../reference/generated-contract-defaults.md`
- `../reference/topology-modes.md`
- `../reference/cycle-normalization.md`
- `../reference/predecessor-context.md`
- `../reference/mail-schema-events.md`
- `../reference/result-routing.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- Process and contract specs are current.
- The loop needs validation, dynamic lookup, rendering, query, completion, explanation, or controlled record application.

## Inputs

Require:
- `<loop-dir>`;
- generated process specs;
- generated contract specs that harness commands will read.

## Outputs

Generate or update `execplan/harness/` for loop-local:
- validation, lookup, rendering, query, completion checks, and explanation;
- topology validation and route/context lookup when topology contracts exist;
- communication schema/render/lifecycle helpers;
- record schema/validate/apply/query helpers;
- control status, mode lookup, mode changes, and manual participant context when the loop is controllable;
- structured command output for agent use.

Use this package shape when a harness is generated:

```text
<loop-dir>/execplan/harness/
  README.md
  commands.toml
  dependency-posture.toml        # only when non-stdlib imports exist
  requirements.txt               # optional standalone/custom execution
  schemas/
    command-envelope.schema.json
  refs/
    <relative symlinks to package artifacts>
  bin/
    <command-wrapper>
  src/
    <implementation files>
  vendor/                        # optional pip --target support
```

File rules:
- `README.md` uses only `Purpose` and `Contents`.
- `commands.toml` is the command registry.
- `dependency-posture.toml` records non-stdlib dependency posture.
- `requirements.txt` and `vendor/` are only for standalone/custom execution outside the Houmao environment.
- `bin/` and `src/` may be omitted only for an explicit no-code or external harness.
- Do not leave command definitions only as loose prose in `execplan/docs/`.
- Add `README.md` files to emitted child directories such as `bin/`, `src/`, `refs/`, and `schemas/`.

## Package References

- Treat `<loop-dir>/execplan/` as the generated loop-definition package.
- Refer to package artifacts by relative path from `execplan/harness/`.
- Use direct paths by default:
  - `../specs/comms/templates.toml`
  - `../specs/comms/schemas/<message-family>.schema.json`
  - `../specs/collab/topology/topology.toml`
  - `../specs/collab/topology/context-posture.toml`
  - `../specs/collab/records/<record-family>.schema.json`
  - `../specs/state/state-overview.md`
  - `../specs/state/schema.sql`
  - `../specs/workspace/workspace.toml`
  - `../agents/bindings.toml`
- If stable local names help, create relative symlinks under `harness/refs/`.
- If symlinks are blocked, use direct relative paths. Do not copy authoritative artifacts.
- Use `harness/schemas/` only for schemas owned by the harness itself, such as the command envelope schema.
- Avoid absolute paths unless a generated contract defines an external runtime path.

Example:

```text
harness/refs/comms-templates.toml -> ../../specs/comms/templates.toml
```

## State Commands

For stateful loops, make the harness the normal participant access path for bookkeeping:

- `state init`: create runtime state from `../specs/state/` contracts and seed data.
- `state validate`: check schema availability, referential integrity, allowed states, transition invariants, active ownership invariants, mail/artifact refs, and policy-derived gates when those concepts exist.
- `state query`: expose read-only summary and scheduler-posture views.
- `record validate`: validate TOML or JSON record payloads against generated schemas.
- `record apply`: apply schema-valid records to sqlite or append JSONL records while preserving transition rules.
- `state export`: optionally render compact human-readable recovery or operator views.

Rules:
- follow the backend defaults in `generated-contract-defaults.md`;
- support JSONL plus schemas only when selected by generated contracts;
- participant agents use harness commands, not raw SQL or ad hoc state-file edits;
- direct state edits are operator repair only, require the loop to be paused, and must be followed by `state validate`;
- read-only query output should be enough for agents to know busy participants, idle participants, active handoffs, assignable work, blockers, and completion posture.
- for generic-loop loops, state validation should cover compact lineage, visited node or edge facts, cycle iterations, active ownership, and message refs when those contracts exist.

## Topology And Context Commands

Generate these surfaces when topology or selected-context contracts exist:

- `topology validate`: validate selected topology mode, route graph shape, cycle posture, local-close tree-loop rules, generic cycle-control requirements, and legacy mode aliases.
- `topology query`: expose mode, participants, routes, cycle facts, result routing, and terminal or operator exceptions.
- `context validate`: validate selected predecessor-context payload fields for generic routes.
- `context query`: return route-specific context requirements, explicit omission notes, and readable source paths.

Rules:
- reject direct `tree-loop` participant cycles unless the topology contract records an accepted normalization that produces a tree or forest;
- reject `generic-loop` cycles without explicit termination, dedupe, and repeat-visit posture;
- accept legacy topology values as aliases when reading existing generated material: `pairwise-tree`, `pairwise-loop`, `pairwise`, `generic-graph`, and `generic graph`;
- validate only the predecessor-context fields selected by generated contracts;
- accept explicit no-context-needed omissions when they are recorded;
- keep full mail bodies out of topology and context state unless an accepted contract defines a durable artifact ref.

## Communication Commands

Generate these surfaces when templated mail families exist:

- `email schema`: resolve a template name or `schema_id` to schema and renderer paths.
- `email validate`: validate a TOML or JSON payload against the generated JSON Schema.
- `email render`: render a validated payload through the generated Markdown renderer.
- `email apply`: record payload lifecycle or bookkeeping facts when generated contracts need them.
- `email query`: expose payload refs, reply expectations, and schema-id dispatch facts.

Rules:
- implement the flow `TOML payload -> JSON Schema validation -> Markdown rendering -> Houmao mail delivery`;
- treat `schema_id` as the loop-local mail type;
- ensure rendered output includes the parseable `houmao-email-metadata` block;
- route actual mail send/reply through maintained Houmao mail support, not harness internals;
- make `email apply` a state/bookkeeping operation only, not mailbox delivery.

## Control Commands

For controllable loops, make the harness the loop-local source for run state and execution mode:

- `control status`: report run state, execution mode, notifier posture, active participants, pending handoffs, blockers, and next operator action.
- `control get-mode`: return the current execution mode and source evidence, defaulting to `auto` when no explicit mode record exists.
- `control set-mode`: record a requested mode change to `auto` or `manual`.
- `control pause`: record pause intent and paused run posture.
- `control resume`: record resume intent and continuation posture.
- `control stop`: record stop intent and stop posture.
- `control manual-context`: return participant-specific context for one manual-mode pass.

Rules:
- separate `run_state` from `execution_mode`;
- default missing initial `execution_mode` to `auto`;
- never treat `manual` as equivalent to `paused`;
- include operator intent events for mode switches, pause, resume, stop, override, and recovery when those controls exist;
- include observed notifier posture when available, but route actual notifier enable/disable through `<public-entrypoint>->houmao-shared-routines->agent-gateway`;
- route operator prompts through `<public-entrypoint>->houmao-shared-routines->agent-messaging` and ordinary mail through `<public-entrypoint>->houmao-shared-routines->agent-email-comms`;
- make participant context output structured enough for generated skills to decide one bounded pass.

Manual context should include:
- run id and plan revision;
- run state and execution mode;
- participant id;
- relevant pending mail refs or active handoff refs;
- allowed actions;
- `stop_after_one_pass = true` or an equivalent field.

## Explain Commands

Harness commands that expose generated contracts should support `--explain` when structured explanations exist.

Sources:
- TOML-backed contracts: read `description` fields from records, sections, or non-obvious fields.
- JSON-schema-backed contracts: read JSON Schema `description` fields.
- Emit stable source keys or paths so agents can map each explanation to the source contract.

Rules:
- do not parse TOML comments for explain output;
- comments in TOML are only for direct human readers;
- if the command uses a common JSON envelope, require `--print-json` with `--explain`.

## Python Dependencies

Use only the libraries needed by generated features:

| Feature | Library |
| --- | --- |
| CLI command groups | `click` |
| `.md.j2` rendering | `jinja2` |
| JSON Schema validation | `jsonschema` |

Defaults:
- Treat these as normal Houmao runtime dependencies.
- Do not ask whether they are allowed when a feature needs them.
- Ask only for stricter version, platform, or deployment constraints.

Dependency posture values:
- `houmao-env`: use the Houmao uv-installed environment.
- `environment-provided`: intended interpreter imports required libraries.
- `local-pip-target`: optional standalone `vendor/` support.
- `pending-local-install`: standalone target is documented but not installed.
- `unavailable`: no usable interpreter or install path is available.

Record posture in `dependency-posture.toml`, `README.md`, `manifest.toml`, or an equivalent indexed artifact.

### Import Check

Check the intended harness interpreter first:

```bash
<python> -c "import click, jinja2, jsonschema"
```

If the intended interpreter is unknown:
- check the current interpreter as weak evidence;
- inspect project dependency declarations as evidence only;
- record that the target interpreter is unresolved.

### Import Failure

Generated entrypoints that import non-stdlib libraries must fail with a short guide:
- name the missing package;
- suggest installing it into the active harness Python environment;
- suggest running or retesting with the Houmao uv-installed environment;
- never hardcode uv tool environment paths.

Useful commands to include:

```bash
uv tool list --show-paths --show-python
uv tool install --force houmao
uv tool install --force --editable .
```

Example helper:

```python
def _missing_harness_dependency(package: str) -> SystemExit:
    message = f"""
Missing generated harness dependency: {package}

Options:
- install it into the Python environment running this harness
- run or retest with the Python environment associated with the installed Houmao uv tool

Helpful checks:
- uv tool list --show-paths --show-python
- uv tool install --force houmao
"""
    raise SystemExit(message.strip())
```

### Authoring Test

- Run a basic harness test or self-check when generated commands provide one.
- If the test fails due to missing libraries, wrong interpreter, or unclear dependency posture, retry through the Houmao uv-installed environment before rewriting harness logic.
- If it still fails there, inspect harness code, command registry, paths, schemas, and inputs.

### Optional Standalone Target

Use this only when the loop intentionally supports running the harness outside the Houmao-installed environment.

`requirements.txt`:

```text
click>=8.1,<9
jinja2>=3.1,<4
jsonschema>=4.0,<5
```

Install:

```bash
python -m pip install --target execplan/harness/vendor -r execplan/harness/requirements.txt
```

Bootstrap before local-package imports:

```python
from pathlib import Path
import sys

_VENDOR = Path(__file__).resolve().parents[1] / "vendor"
if _VENDOR.exists():
    sys.path.insert(0, str(_VENDOR))
```

Rules:
- Include only required libraries.
- Keep `vendor/` local to the generated harness.
- Do not install into system Python, user site-packages, or the surrounding project environment.
- Adjust `_VENDOR` if the entrypoint is not under `execplan/harness/bin/`.

## Actions

1. Generate harness surfaces from generated contracts only.
2. Keep output intended for agents machine-readable where practical.
3. Use a common envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings, or document an equivalent.
4. Make command definitions declare the artifact paths they read, validate, render, query, or apply, including whether each path is a harness-local relative symlink or a direct relative path to another package artifact.
5. Keep apply commands narrow and schema-validated.
6. Generate state init, validation, query, record-validation, and record-application commands when runtime bookkeeping exists.
7. Generate control status, mode lookup, controlled mode or lifecycle updates, and manual-context commands when the loop has lifecycle or manual operation needs.
8. Generate topology and selected-context validation/query commands when generated contracts define topology or generic predecessor context.
9. Generate email schema, validate, render, apply, and query commands when generated communication contracts define templated mail.
10. Generate `--explain` support for contract-exposing commands when TOML `description` fields or JSON Schema descriptions are available.
11. Document any harness commands generated skills are expected to call.
12. Document the harness dependency posture and recovery guidance whenever generated harness code imports non-stdlib libraries.

## Downstream Effects

- Changes here invalidate generated skills, agent bindings that install harness helper skills, final docs, and final manifest.

## Constraints

- Do not make the harness own mailbox delivery, gateway discovery, managed-agent lifecycle, memory management, or workspace creation.
- Do not make the harness directly enable or disable mail notifiers; record loop-local mode intent and route platform posture through maintained gateway surfaces.
- Do not invent process or contract semantics that are absent from upstream specs.
- Do not rely on ad hoc undeclared imports for `click`, `jinja2`, `jsonschema`, or their dependencies.
- Do not claim a packaged offline wheel bundle exists for generated harness dependencies.
