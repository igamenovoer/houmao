## Why

Launch-profile memo seeds currently expose `initialize`, `replace`, and `fail-if-nonempty` policies even though the practical workflow is reusable profile launches that refresh known memo/page content. The extra policy dimension makes the CLI, docs, skills, runtime status, and stored model harder to understand, and the default `initialize` behavior can silently skip the seed that users expected a profile to apply.

## What Changes

- **BREAKING** Remove `--memo-seed-policy` from easy-profile and explicit launch-profile authoring commands.
- **BREAKING** Remove memo-seed policy from launch-profile inspection payloads, compatibility projection YAML, launch-profile provenance, and launch completion payloads.
- **BREAKING** Stop storing memo-seed policy as part of the authoritative launch-profile model; stored memo seeds are represented only by source kind and managed content reference.
- Apply every stored memo seed with the current scoped replacement behavior:
  - text/file seeds replace only `houmao-memo.md`;
  - directory seeds replace `houmao-memo.md` only when the seed contains `houmao-memo.md`;
  - directory seeds clear and rewrite `pages/` only when the seed contains `pages/`;
  - omitted seed components remain unchanged.
- Preserve `--clear-memo-seed` as the explicit way to remove stored seed configuration.
- Update docs and packaged system-skill guidance to describe the single replace-only memo-seed behavior.
- Update tests to focus on source-scoped replacement, removal of policy-only mutation, and the new payload/projection shape.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-launch-profiles`: Remove memo-seed policy from the shared launch-profile object contract and inspection requirements.
- `brain-launch-runtime`: Replace policy-gated memo-seed application with unconditional scoped replacement for profile-backed launches.
- `houmao-mgr-agents-launch`: Update explicit launch-profile-backed launch behavior and completion reporting to the simplified memo-seed result model.
- `houmao-mgr-project-agents-launch-profiles`: Remove `--memo-seed-policy` and policy-only patching from explicit launch-profile authoring.
- `houmao-mgr-project-easy-cli`: Remove `--memo-seed-policy` and policy-only patching from easy-profile authoring and keep profile-backed launch behavior aligned with runtime scoped replacement.
- `agent-memory-freeform-memo`: Replace stored-policy language with the new explicit memo-only replacement contract.
- `agent-memory-pages`: Replace policy-specific pages behavior with the new directory-seed page replacement contract.
- `houmao-memory-mgr-skill`: Update launch-profile memo-seed guidance so agents no longer suggest or require memo-seed policies.
- `docs-launch-profiles-guide`: Document memo seeds as replace-only scoped launch-profile content.
- `docs-cli-reference`: Remove memo-seed policy documentation and describe the remaining source and clear flags.
- `docs-easy-specialist-guide`: Keep easy-profile memo-seed guidance aligned with the simplified source-only CLI.

## Impact

- Affected runtime code: launch-profile memo-seed application helpers and local managed launch completion payload construction.
- Affected catalog code: launch-profile memo-seed dataclasses, SQLite schema/migration, compatibility projection rendering, and profile payload builders.
- Affected CLI code: shared launch-profile storage parsing plus `project agents launch-profiles add|set` and `project easy profile create|set` option surfaces.
- Affected docs and skills: launch-profile guide, easy-specialists guide, CLI reference, `houmao-memory-mgr`, `houmao-project-mgr`, and `houmao-specialist-mgr` packaged guidance.
- Affected tests: catalog, project command, runtime launch, memo-seed application, docs guard, and system-skill guard tests.
