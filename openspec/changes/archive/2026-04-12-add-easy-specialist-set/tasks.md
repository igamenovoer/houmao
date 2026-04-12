## 1. Specialist Patch Command

- [x] 1.1 Add `project easy specialist set` Click command with patch flags for prompt, skills, setup, credential, prompt mode, model, reasoning level, and persistent env records.
- [x] 1.2 Implement specialist patch-state resolution that loads the existing catalog entry, preserves unspecified fields, rejects empty updates, and rejects unsupported tool-lane or rename mutation.
- [x] 1.3 Reuse existing validation helpers for prompt input, imported skill directories, existing skill names, setup lookup, credential display-name lookup, model merge behavior, prompt mode, and persistent env records.
- [x] 1.4 Persist the resolved specialist state through the catalog-backed specialist storage path and avoid snapshotting canonical content-store files onto themselves.
- [x] 1.5 Rematerialize the `.houmao/agents/` compatibility projection after successful mutation and remove the old specialist-owned projected preset when setup changes alter the canonical preset name.

## 2. Tests

- [x] 2.1 Add unit coverage showing `specialist set` updates prompt content while preserving existing skill bindings and other unspecified fields.
- [x] 2.2 Add unit coverage for `--with-skill`, `--add-skill`, `--remove-skill`, and `--clear-skills`, including preservation of shared skill content after removing one binding.
- [x] 2.3 Add unit coverage for launch-owned defaults: `--prompt-mode`, `--clear-prompt-mode`, `--model`, `--clear-model`, `--reasoning-level`, `--clear-reasoning-level`, `--env-set`, and `--clear-env`.
- [x] 2.4 Add unit coverage for validation failures: empty update, credential-owned env names, missing setup, missing credential, and unsupported tool-lane mutation.
- [x] 2.5 Add projection coverage showing updated role/preset output and stale old preset cleanup when a setup change changes the generated preset name.

## 3. Documentation And System Skill Assets

- [x] 3.1 Update the easy-specialists guide to document specialist patch editing, skill-edit examples, replacement semantics, and the future-launch boundary.
- [x] 3.2 Update CLI reference coverage for `project easy specialist set` and same-name specialist replacement with `create --yes`.
- [x] 3.3 Update packaged `houmao-specialist-mgr` routing and action guidance so agents use `specialist set` for existing-specialist edits and keep profile updates routed to `profile set`.
- [x] 3.4 Update system-skill asset tests or snapshots so the packaged skill inventory expects the new specialist update guidance.

## 4. Verification

- [x] 4.1 Run focused unit tests for project easy specialist commands and system skill assets.
- [x] 4.2 Run `pixi run lint`.
- [x] 4.3 Run `pixi run test` or document any reason the full unit suite could not be run.

Verification note: `pixi run test` was run and completed with 11 failures in unrelated baseline areas (fake headless session signature drift, existing system-skill/demo/client/gateway expectation mismatches, and the implementation worktree's missing embedded `extern/tracked/cli-agent-orchestrator` file). The focused `project_easy_specialist_set` tests and focused specialist system-skill asset test passed.
