## 1. Skill Asset

- [x] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-agent-loop-lite/` with a top-level `SKILL.md` that defines manual-only activation, supported lite operations, and no auto-routing from generic loop requests.
- [x] 1.2 Add lite authoring guidance for `init`, `clarify`, `generate-skills`, and `validate` that preserves the `intention/`, `execplan/`, and `runs/` spine while omitting `execplan/harness/` and `execplan/docs/`.
- [x] 1.3 Add lite execution guidance for `prepare-agents`, `launch-agents`, `start`, `status`, `pause`, `resume`, `stop`, and `recover`, routing platform mechanics through existing Houmao system skills.
- [x] 1.4 Add lite reference guidance for required Markdown templates, `Loop-Template-Type` dispatch, `<placeholder ...>` replacement, Houmao mail envelope boundaries, direct SQLite usage, and bounded-turn behavior.
- [x] 1.5 Ensure the lite skill does not mention JSON schemas, Jinja2 renderers, generated harness commands, or generated docs as normal lite outputs.

## 2. Lite Generated Package Contract

- [x] 2.1 Define the default lite package shape in skill guidance with required files only: intention README/overview, execplan README/manifest, Markdown specs, required templates, state README/schema, generated skills README/content, agent bindings, and `runs/`.
- [x] 2.2 Define optional lite material rules so workspace docs, run-artifact rules, seed SQL, query recipes, notifier prompts, profile definitions, tick skills, and operator-control skills appear only when selected by the generated loop.
- [x] 2.3 Define required communication template rules: plain Markdown, body-local `Loop-Template-Type` and `Loop-Template-Version`, first-blank-line prologue termination, and no duplicated Houmao envelope fields.
- [x] 2.4 Define generated-skill validity rules requiring a shared lite guidance skill and at least one generated receiver skill for every required `Loop-Template-Type`.
- [x] 2.5 Define direct SQLite state rules requiring `execplan/specs/state/schema.sql`, `execplan/specs/state/README.md`, per-run SQLite databases under `runs/<run-id>/`, compact state facts, transaction discipline, and audit/event rows where needed.
- [x] 2.6 Define lite validation guidance that checks required files, template type uniqueness, generated receiver-skill coverage, forbidden harness/docs directories, unresolved placeholders where applicable, and SQLite schema parseability.

## 3. Catalog And Projections

- [x] 3.1 Add `houmao-agent-loop-lite` to `src/houmao/agents/assets/system_skills/catalog.toml` with `asset_subpath = "houmao-agent-loop-lite"`.
- [x] 3.2 Add `houmao-agent-loop-lite` to both `core` and `all` install sets while keeping retired loop package names absent.
- [x] 3.3 Update project-scope Codex, Claude, and Copilot skill projections or symlinks so current loop discovery includes lite alongside pro where those projections mirror current core skills.
- [x] 3.4 Update catalog/schema or loader tests if needed so lite is treated as a current skill and not as a retired cleanup target.

## 4. Existing Skill Guidance

- [x] 4.1 Update `houmao-agent-loop-pro` guidance so it no longer claims to be the sole maintained loop skill and clearly remains the schema-rich generated-execplan path.
- [x] 4.2 Update `houmao-touring` guidance to branch between lite for Markdown/direct-SQL/no-harness loops and pro for schema/harness/topology-heavy generated execplans.
- [x] 4.3 Update `houmao-adv-usage-pattern` guidance to recognize lite as the lightweight generated-skill loop path while keeping pro as the topology-rich execplan route.
- [x] 4.4 Update terminology references so current docs distinguish pro loops from lite loops without reviving retired pairwise or generic package names.

## 5. Documentation

- [x] 5.1 Update README loop-skill inventory and narrative to list both `houmao-agent-loop-pro` and `houmao-agent-loop-lite`.
- [x] 5.2 Update `docs/getting-started/loop-authoring.md` with the pro-vs-lite choice and the lite default shape.
- [x] 5.3 Update `docs/getting-started/system-skills-overview.md` so the packaged skills table and install-set explanation include lite.
- [x] 5.4 Update `docs/reference/cli/system-skills.md` so current inventory, set examples, status, install, and uninstall guidance include lite as a current skill.
- [x] 5.5 Update any docs guard fixtures or expected lists that enumerate current packaged system skills.

## 6. Tests And Verification

- [x] 6.1 Add or update system-skill catalog tests to assert `houmao-agent-loop-lite` is current, installable, included in `core` and `all`, and absent from retired cleanup names.
- [x] 6.2 Add or update system-skill install/status/uninstall tests to cover lite projection and removal.
- [x] 6.3 Add lite skill-content tests for manual-only activation, no harness/docs output, required templates, generated-skill coverage, direct SQLite guidance, and no duplicated Houmao envelope fields in template examples.
- [x] 6.4 Add docs tests or guard updates for README, loop authoring, system-skills overview, CLI reference, touring, and advanced-usage references.
- [x] 6.5 Run focused unit tests for system skills and docs guards.
- [x] 6.6 Run `pixi run lint` if Python code or tests change.
- [x] 6.7 Run a final `rg` check outside archived changes and legacy references to confirm current loop guidance presents pro and lite as the only maintained loop skills.
