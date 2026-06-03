## 1. Native Brain Build Behavior

- [x] 1.1 Update preset resolution so `internals native-agent brain build --preset` accepts bare names, absolute paths, and existing cwd-relative paths.
- [x] 1.2 Update direct brain-build input validation so an explicitly selected preset with `skills: []` is treated as intentional no-user-skill selection.
- [x] 1.3 Add or update unit/CLI tests for cwd-relative preset paths, bare preset names, explicit empty preset skills, and missing skill input without preset skills.

## 2. Plain Fixture Guidance

- [x] 2.1 Refresh `tests/fixtures/plain-agent-def/README.md` and `MIGRATION.md` to describe native-root seed usage, project-backed public launch, and scoped selected-agent follow-up.
- [x] 2.2 Refresh fixture role and skill READMEs to use `roles/` and `skills/` paths instead of stale `agents/...` paths.
- [x] 2.3 Refresh `server-api-smoke` role wording to describe maintained managed-agent API or passive-server smoke validation instead of retired standalone `houmao-server`.
- [x] 2.4 Add or update tests that scan fixture guidance for retired root `agents launch|stop|cleanup` examples and stale path vocabulary.

## 3. Official Login Smoke Flow

- [x] 3.1 Rework `tests/manual/manual_claude_official_login_smoke.py` to create a temporary project overlay and register the official-login credential/smoke specialist from fixture seed material.
- [x] 3.2 Change the smoke launch command to use `houmao-mgr project agents launch --specialist ... --headless` from the temporary project.
- [x] 3.3 Change smoke stop and cleanup calls to use `houmao-mgr agents single --agent-id <id> stop` and `houmao-mgr agents single --agent-id <id> cleanup session`.
- [x] 3.4 Add or update unit coverage for the manual smoke command construction without requiring plaintext local credentials.

## 4. Validation

- [x] 4.1 Run `openspec validate refresh-plain-agent-def-cli-fixture --strict`.
- [x] 4.2 Run focused tests covering native brain-build selector behavior and fixture guidance checks.
- [x] 4.3 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test` if the implementation touches runtime code or shared test helpers.
