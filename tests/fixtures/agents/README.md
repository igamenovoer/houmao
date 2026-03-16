# Agents Directory

This directory follows a brain-first + role-first composition model.

## Canonical Layout

```text
agents/
  brains/                           # Reusable brain components
    tool-adapters/                  # Per-tool home layout and launch rules
    cli-configs/<tool>/<profile>/   # Secret-free tool config profiles
    skills/<skill>/SKILL.md         # Agent Skills format
    brain-recipes/<tool>/*.yaml     # Secret-free recipe presets
    api-creds/<tool>/<profile>/...  # Local-only credentials (gitignored)
  roles/
    <role>/system-prompt.md         # Brain-agnostic role packages
  blueprints/
    <agent>.yaml                    # Optional {brain recipe + role} bindings
```

## How To Use Each Part

### `agents/brains/tool-adapters/`

Defines per-tool home layout and launch contracts.

Use this when:

- adding a new CLI tool
- changing where config/skills/credentials are projected
- changing which env vars are allowlisted for launch

### `agents/brains/cli-configs/<tool>/<profile>/`

Stores secret-free config profiles for a specific tool.

Use this when:

- you want different defaults for different workloads (for example `default`, `research`, `strict`)
- you need to update non-secret tool config files

### `agents/brains/skills/<skill>/SKILL.md`

Stores reusable skills in Agent Skills format.

Use this when:

- adding/editing reusable task instructions that can be installed into runtime homes

### `agents/brains/brain-recipes/<tool>/*.yaml`

Stores declarative, secret-free brain presets.

Use this when:

- you want a reusable preset for `{tool, skills, config profile, credential profile-name}`

### `agents/brains/api-creds/<tool>/<profile>/`

Local-only credential profiles (gitignored).

Use this when:

- setting up account credentials and env files locally
- rotating account usage by creating a new profile directory name

Never commit credential material.

### `agents/roles/<role>/system-prompt.md`

Stores brain-agnostic role packages.

Use this when:

- defining behavior/policy for an agent independent of tool/runtime layout

### `agents/blueprints/<agent>.yaml`

Optional binding between a brain recipe and a role.

Use this when:

- you want one named, shareable agent definition without embedding secrets
- you want CLI entrypoints such as `build-brain --blueprint ...` or `start-session --blueprint ...` to resolve the role and the recipe-selected tool/config/credential inputs together

## Runtime Outputs (Generated)

The builder writes generated runtime state outside source-of-truth components:

- `<runtime_root>/homes/<tool>/<home-id>/`
- `<runtime_root>/manifests/<tool>/<home-id>.yaml`

Default runtime root is `tmp/agents-runtime/`.

## Brain-First Workflow

1. Select tool + skill set + config profile + credential profile.
2. Build a fresh runtime home from a recipe:
   - `pixi run python scripts/agents/build_brain_home.py --recipe agents/brains/brain-recipes/codex/gpu-kernel-coder-default.yaml`
3. Or build from explicit inputs:
   - `pixi run python scripts/agents/build_brain_home.py --tool codex --skill openspec-apply-change --config-profile default --cred-profile personal-a-default`
4. Launch the tool via the generated helper:
   - `<runtime_root>/homes/<tool>/<home-id>/launch.sh`
5. Apply a role from `agents/roles/<role>/system-prompt.md`.

## Source-Of-Truth Rules

- Commit: adapters, config profiles, skills, recipes, roles, blueprints.
- Do not commit: `agents/brains/api-creds/**` contents or secret values anywhere.
- Let recipes own credential-profile selection; blueprints stay secret-free and inherit that selection through their bound recipe.
- Concurrent active sessions may reuse the same provider credentials when the provider/tool allows it. If you hit provider-side rate or session limits, rotate one recipe or blueprint to a different credential profile.
- Keep adapter definitions authoritative for per-tool projection and launch behavior.

## Migration Status

Legacy profile folders under `agents/gpu_*` have been removed after migration to the brain-first flow.

Reference notes are documented in `agents/MIGRATION.md`.
