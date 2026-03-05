## 1. Scaffolding and hygiene

- [x] 1.1 Create `agents/brains/` + `agents/roles/` (+ optional `agents/blueprints/`) directory scaffolds with minimal READMEs
- [x] 1.2 Update repo `.gitignore` to ignore `agents/brains/api-creds/` (local-only creds)
- [x] 1.3 Update `agents/README.md` to document the new brain-first workflow (construct brain → start tool with home → apply role)

## 2. Tool adapters and component repos

- [x] 2.1 Define a tool-adapter schema and add `agents/brains/tool-adapters/codex.yaml` (config/skills/creds projection + env var allowlist/injection + home selection mechanism)
- [x] 2.2 Add `agents/brains/tool-adapters/claude.yaml` with equivalent projection rules
- [x] 2.3 Add `agents/brains/tool-adapters/gemini.yaml` with equivalent projection rules
- [x] 2.4 Add initial `agents/brains/cli-configs/<tool>/<profile>/...` profiles for codex/claude/gemini (minimal working defaults)
- [x] 2.5 Seed `agents/brains/skills/` with an initial set of skills (e.g., link/copy existing OpenSpec skills) and document how to add more

## 3. Brain recipes and optional blueprints

- [x] 3.1 Define a brain-recipe file format and add at least one example under `agents/brains/brain-recipes/<tool>/...`
- [x] 3.2 Define a secret-free agent-blueprint file format that binds `{brain recipe, role}` and add an example under `agents/blueprints/`
- [x] 3.3 Document credential profile naming and rotation guidance (how to balance usage across accounts without sharing the same cred profile concurrently)

## 4. Brain builder implementation

- [x] 4.1 Implement a single brain builder CLI (e.g., `scripts/agents/build_brain_home.py`) that constructs a fresh runtime home from `{tool, skills, cli-config, cred profile}` using the tool adapter
- [x] 4.2 Ensure builder writes a resolved, secret-free runtime manifest per constructed home under `<runtime_root>/manifests/` (runtime root is configurable; default may be `tmp/agents-runtime/`)
- [x] 4.3 Ensure builder is fresh-by-default (refuse to build into an existing home unless explicitly asked to reuse)
- [x] 4.4 Add basic validation/errors (missing adapter, unknown skill, missing config profile, missing cred profile)
- [x] 4.5 Add credential env-var support: read `agents/brains/api-creds/<tool>/<cred-profile>/env/vars.env` (or tool-adapter-defined location) and include only env var names + local paths in the resolved manifest
- [x] 4.6 Add a launch helper (script or printed command) that starts the tool with (a) the tool home selector env var/flag and (b) credential env vars applied per the tool adapter

## 5. Role packaging and migration

- [x] 5.1 Create `agents/roles/<role>/system-prompt.md` structure and migrate (or duplicate) existing `agents/gpu_*/system-prompt.md` into role packages
- [x] 5.2 Update legacy `agents/gpu_*/README.md` files to point to roles + brain construction (and mark `bootstrap.sh` as deprecated or wrap it around the new builder)
- [x] 5.3 Add a short migration note describing how existing `agents/<agent>/homes/...` users should transition to `<runtime_root>/homes/...` (default `tmp/agents-runtime/homes/...`)

## 6. Tests

- [x] 6.1 Add unit tests for the brain builder covering: fresh home creation, selected-skill installation, config projection, credential file projection, credential env-var injection contract, and manifest output
