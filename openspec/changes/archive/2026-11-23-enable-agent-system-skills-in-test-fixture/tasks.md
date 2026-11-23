# Tasks

## 1. Fixture Configuration And Specialist Policy

- [x] 1.1 Add a `system_skill_policy: Literal["default", "none"] = "default"` field to `ResolvedConfig`, pass it through both API and native-login `resolve_config`/`selected_configuration` paths, and verify a focused unit test shows the default value and its `summary()` output.
- [x] 1.2 Add `--no-system-skills` to the fixture `prepare` CLI, map it to `system_skill_policy="none"`, reject it for `--surface raw`, and verify `fixture.py prepare --surface raw --no-system-skills` fails while `check` resolves the opt-out without launching.
- [x] 1.3 In `_prepare_project`, append `--no-system-skills` only when the resolved policy is `none`; verify a default prepared run's specialist preset has no `launch.system_skills` entry and an opt-out run records `mode: none`.
- [x] 1.4 Update `scripts/agents/test-fixtures/README.md` to state that manager-surface runs use the managed `agent` pack by default, how to opt out, and where `run.json` records the choice; verify the documented commands match the implemented flags.

## 2. Runtime Home And Integration Coverage

- [x] 2.1 Add a manager-surface fixture integration test that launches a harmless client with the default policy and verifies `discover_installed_system_skills()` reports `houmao-agent-entrypoint` and `houmao-shared-routines` in the runtime home.
- [x] 2.2 Add the matching opt-out integration test that prepares with `--no-system-skills`, launches, and verifies the runtime home has no installed system skills while `run.json.configuration.system_skill_policy` is `none`.
- [x] 2.3 Run the focused fixture and system-skill suites (`tests/integration/agents/test_agent_fixture_launches.py`, `tests/unit/agents/test_system_skills.py`, and any new focused test module) and confirm they pass.

## 3. Verification And Review

- [x] 3.1 Run `pixi run lint` and `pixi run typecheck` and confirm no new failures.
- [x] 3.2 Run `pixi run test` and confirm no new failures.
- [x] 3.3 Re-read the delta spec scenarios against the implemented tests and confirm each scenario has observable coverage.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
