## Why

Project-local skills currently pass through two live-looking trees, `.houmao/content/skills/` and `.houmao/agents/skills/`, which makes it unclear which path is canonical and forces copy-oriented specialist workflows even when the operator wants one repo-owned skill source to stay live. Existing users also already have older project structures such as legacy `.houmao/easy/specialists/*.toml` metadata or plain compatibility-tree-only overlays, and we do not want ordinary project commands to silently rewrite those structures through scattered upgrade code. This confusion now blocks both the operator-facing question in upstream issue `#34` and the requested repo-skill symlink workflow in upstream issue `#22`.

## What Changes

- Introduce a first-class project skill registry under the project overlay so skill source binding is owned by the project layer rather than by specialist creation.
- Support source-aware project skills with explicit storage modes such as `copy` and `symlink`, while keeping generated or project-owned content under the managed content roots.
- **BREAKING**: stop treating `.houmao/agents/skills/` as canonical project-owned skill storage; it becomes a derived compatibility or runtime projection surface only.
- Add an explicit `houmao-mgr project migrate` workflow that detects known legacy project layouts, shows an upgrade plan, and performs supported project-structure migrations only when the operator asks.
- **BREAKING**: ordinary `houmao-mgr project ...` and project-backed catalog flows stop silently absorbing or rewriting known legacy project structure; they fail with migration guidance when an explicit project migration is required.
- Update `project easy specialist` workflows so specialists bind project skill names instead of importing source directories as their primary storage model.
- Add launch and projection behavior that materializes selected project skills into managed homes from the canonical project skill registry instead of relying on duplicated live project trees.
- Update project and easy-specialist documentation to explain canonical versus derived skill state, including how repo-owned skills stay live when registered in symlink mode.

## Capabilities

### New Capabilities
- `houmao-mgr-project-skills-cli`: Manage canonical project-local skill registrations, including copy-backed and symlink-backed source bindings.
- `houmao-mgr-project-migrate-cli`: Detect and explicitly migrate known legacy project structures into the current `houmao-mgr project` layout.

### Modified Capabilities
- `project-config-catalog`: Extend the catalog-backed project model so project assets can preserve canonical source bindings, distinguish canonical content from derived projections, and reserve project-structure upgrades for the explicit migration workflow.
- `houmao-mgr-project-cli`: Expose project-local skill administration as a first-class `houmao-mgr project` command family and add an explicit migration command instead of silent project upgrades.
- `houmao-mgr-project-easy-cli`: Update easy-specialist authoring so specialists reference project skill registrations by name instead of treating imported directories as the canonical specialist-owned source, and route known legacy specialist metadata through explicit migration rather than opportunistic load-time upgrades.
- `docs-getting-started`: Document the canonical project skill registry, clarify that `.houmao/agents/skills/` is derived projection state rather than the source of truth, and direct existing users to `project migrate` for supported project-structure upgrades.
- `docs-easy-specialist-guide`: Update easy-specialist guidance to use project skill registration and specialist skill binding by name, including copy versus symlink operator intent.

## Impact

- Affected code: project catalog schema and projection materialization, legacy project-structure detection and migration planning, `houmao-mgr project` CLI wiring, `project easy specialist` flows, managed-home skill projection, and related project docs.
- Affected operator model: project-local skills gain a first-class registry surface; direct editing of `.houmao/agents/skills/` is no longer a supported source-management workflow; supported existing-project upgrades move behind `houmao-mgr project migrate` instead of happening implicitly inside ordinary commands.
- Upstream issues addressed: `#22` (repo-owned skill symlink workflow) and `#34` (canonical versus derived skill tree confusion).
