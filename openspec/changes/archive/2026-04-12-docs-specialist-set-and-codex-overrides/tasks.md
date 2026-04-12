## 1. Skill table verb updates

- [x] 1.1 In README.md, update the `houmao-specialist-mgr` row (line 383) to read "Create, **set**, list, inspect, remove, launch, and stop easy specialist/profile-backed project-local workflows".
- [x] 1.2 In `docs/getting-started/system-skills-overview.md`, update the `houmao-specialist-mgr` row (line 37) to include "set" in the verb list (e.g. "Create, set, list, inspect, remove easy specialists").

## 2. Launch policy hook table

- [x] 2.1 In `docs/reference/build-phase/launch-policy.md`, add a `codex.append_unattended_cli_overrides` row to the Codex hooks table (after `codex.ensure_model_migration_state`). Description: "Appends final Codex CLI `-c` override arguments for `approval_policy`, `sandbox_mode`, and `notice.hide_full_access_warning` so project-local `config.toml` cannot weaken unattended posture."
