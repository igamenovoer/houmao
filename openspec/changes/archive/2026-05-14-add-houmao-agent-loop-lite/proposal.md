## Why

`houmao-agent-loop-pro` is the right path for robust generated execplans, schemas, harnesses, and validation-heavy loop operation, but that surface is intentionally heavy for small agent loops where the operator wants a readable Markdown-first definition and direct SQLite bookkeeping. Houmao needs a current lightweight loop skill that keeps the familiar pro directory spine while removing JSON schemas, Jinja rendering, generated harnesses, and generated docs.

## What Changes

- Add a new manual-invocation-only packaged system skill named `houmao-agent-loop-lite`.
- Keep the same broad loop directory spine as pro: `<loop-dir>/intention/`, `<loop-dir>/execplan/`, and `<loop-dir>/runs/`.
- Define lite execplans as generated operational material under `execplan/`, but make Markdown the contract format for objective, organization, process, communication, manifest, agent bindings, and generated skill guidance.
- Require communication templates in lite execplans. Templates are plain Markdown files with simple `<placeholder ...>` replacement and a body-local `Loop-Template-Type` / `Loop-Template-Version` prologue for generated receiver-skill dispatch.
- Forbid lite templates from duplicating Houmao mail envelope fields such as sender, receiver, subject, message id, thread id, timestamps, reply refs, or system headers; generated skills read those from Houmao mailbox metadata.
- Require generated lite skills. A lite execplan is valid only when generated skills exist and each required communication template has at least one generated receiver skill that names its `Loop-Template-Type`.
- Make SQLite the lite runtime state contract through `execplan/specs/state/schema.sql` and `execplan/specs/state/README.md`; participant agents manipulate per-run SQLite databases directly using the generated skill guidance.
- Remove the pro harness and docs layers from the lite default shape. Lite SHALL NOT generate `execplan/harness/` or `execplan/docs/`.
- Use as-simple-as-possible defaults: optional files, directories, roles, control skills, workspace material, notifier prompts, seed SQL, and query recipes do not appear unless the loop actually needs them.
- Add `houmao-agent-loop-lite` to the current packaged skill catalog and install sets alongside `houmao-agent-loop-pro`.
- Update current docs, touring, and advanced-usage routing so users can choose lite for Markdown/direct-SQL loops and pro for schema/harness/validation-heavy generated execplans.

## Capabilities

### New Capabilities

- `houmao-agent-loop-lite-skill`: Defines the packaged lite loop skill, its directory contract, required Markdown templates, generated-skill requirements, direct SQLite state model, and manual operation surface.

### Modified Capabilities

- `houmao-system-skill-installation`: Current packaged catalog and install sets include both `houmao-agent-loop-pro` and `houmao-agent-loop-lite` as maintained loop skills.
- `houmao-agent-loop-pro-skill`: Pro is no longer the sole maintained loop system skill; it remains the heavyweight generated-execplan path while lite owns Markdown/direct-SQL loops.
- `docs-loop-authoring-guide`: Loop authoring docs present the pro-vs-lite choice and describe when to choose each.
- `docs-system-skills-overview-guide`: System-skills overview lists lite as a packaged skill and distinguishes it from pro.
- `docs-readme-system-skills`: README system-skill inventory and loop narrative mention both current loop skills.
- `docs-cli-reference`: System-skills CLI reference current inventory includes lite.
- `houmao-touring-skill`: Touring routes lightweight Markdown/direct-SQL loop requests to lite and schema/harness/complex topology requests to pro.
- `houmao-adv-usage-pattern-skill`: Advanced-usage guidance recognizes lite as the lightweight generated-skill loop path while keeping pro as the topology-rich execplan path.
- `houmao-loop-terminology`: Current terminology distinguishes pro execplans from lite Markdown/direct-SQL loop packages without reviving retired pairwise or generic package names.

## Impact

- Affected skill catalog: `src/houmao/agents/assets/system_skills/catalog.toml`.
- New packaged skill asset: `src/houmao/agents/assets/system_skills/houmao-agent-loop-lite/`.
- Affected project-scope skill links for Codex, Claude, and Copilot if maintained project projections are expected to expose all current core skills.
- Affected docs: README, loop authoring guide, system-skills overview/reference, CLI reference, touring guidance, and advanced-usage guidance.
- Affected tests: system-skill catalog/install tests, auto-install tests, skill-content tests, docs guard tests, and new lite skill content tests.
- No runtime migration is required. Lite creates new loop-local files and per-run SQLite databases only when a lite loop is authored or started.
