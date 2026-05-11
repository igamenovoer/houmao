# Validate Execplan

Use this page to inspect a generated v5 execplan before execution or after regeneration.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/`

## Checks

Check:
- `execplan/manifest.toml` exists.
- `execplan/specs/` exists.
- `execplan/skills/` exists.
- `execplan/agents/` exists.
- `execplan/harness/` exists.
- `execplan/docs/` exists.
- generated skills under `execplan/skills/*/SKILL.md` have valid skill frontmatter.
- concrete agent bindings under `execplan/agents/` identify their intended participant or role.
- generated docs do not claim to be source authority.
- intention files remain under `intention/`, not inside generated `execplan/`.

If a generated harness provides a validation command, run that command and prefer its machine-readable output.

## Output

Report:
- validation pass or fail,
- missing required files or directories,
- stale or ambiguous generated-source markers,
- whether the plan appears ready for execution subskills.

## Boundaries

- Do not fix validation failures unless the user asked for repair or regeneration.
- Do not fail only because `<loop-dir>/adrs/` is absent.
- Do not validate domain-specific CUDA or Hopper fields unless the intention source introduced that domain.
