# Validate Execplan

Use this page to inspect a generated execplan before execution or after regeneration.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/`

## Checks

Check:
- `execplan/manifest.toml` exists.
- `execplan/manifest.toml` is parseable and, when it indexes artifact paths, every indexed path exists.
- `execplan/specs/` exists.
- `execplan/skills/` exists.
- `execplan/agents/` exists.
- `execplan/harness/` exists.
- `execplan/docs/` exists.
- generated skills under `execplan/skills/*/SKILL.md` have valid skill frontmatter.
- generated on-event and on-tick skills state their trigger, role owner, bounded procedure, and output or handoff posture.
- concrete agent bindings under `execplan/agents/` identify their intended participant or role.
- concrete agent bindings identify prompt source, installed generated skills, and workspace or launch policy when the execplan defines those concepts.
- workspace setup contracts route workspace planning or creation through `houmao-utils-workspace-mgr` when the requested layout is a supported Houmao workspace flavor.
- default workspace policy is `in-repo` plus any explicitly listed loop bookkeeping directories, unless intention source chooses a different supported flavor or a custom operator-owned workspace.
- generated communication registries under `execplan/specs/comms/` connect schema ids, payload formats, and renderers coherently when the loop is mail-driven.
- generated JSON schemas under `execplan/specs/comms/` or `execplan/specs/collab/records/` parse as JSON when present.
- generated record contracts exist for structured bookkeeping that the harness or skills claim to apply.
- generated harness commands or docs expose the loop's dynamic lookup and data-model mechanics when skills depend on harness lookup, schema validation, rendering, query, or controlled record application.
- generated docs do not claim to be source authority.
- intention files remain under `intention/`, not inside generated `execplan/`.

If a generated harness provides a validation command, run that command and prefer its machine-readable output.

## Output

Report:
- validation pass or fail,
- missing required files or directories,
- parse or link failures in manifest, TOML, JSON schemas, schema/render registries, or agent bindings,
- stale or ambiguous generated-source markers,
- whether the plan appears ready for execution subskills.

## Boundaries

- Do not fix validation failures unless the user asked for repair or regeneration.
- Do not fail only because `<loop-dir>/adrs/` is absent.
- Do not validate domain-specific CUDA or Hopper fields unless the intention source introduced that domain.
