## 1. Test Harness Setup

- [x] 1.1 Add a focused test helper that creates a fake `codex` executable early on `PATH` and records selected environment variables from the provider process.
- [x] 1.2 Ensure the fake Codex process remains observable long enough for the local interactive tmux readiness path or provide a controlled readiness substitute consistent with existing runtime tests.
- [x] 1.3 Add tmux cleanup and skip behavior so the regression is deterministic on hosts without tmux.

## 2. Easy Profile Launch Regression

- [x] 2.1 Create a test project and Codex-backed easy specialist using existing fixture-style credential inputs without requiring live OpenAI access.
- [x] 2.2 Create an easy profile through `houmao-mgr project easy profile create --env-set http_proxy=http://127.0.0.1:7990 --env-set https_proxy=http://127.0.0.1:7990 --env-set FEATURE_FLAG_X=profile-env`.
- [x] 2.3 Launch the managed agent through `houmao-mgr project easy instance launch --profile <profile>` in the local interactive Codex lane.
- [x] 2.4 Assert the launched tmux session environment contains the profile env records.
- [x] 2.5 Assert the fake Codex provider process observes the same profile env records in its inherited process environment.

## 3. Diagnostics And Guardrails

- [x] 3.1 Make the regression failure output identify which hop failed: profile inspection, manifest/launch-plan env, tmux session env, or provider process env.
- [x] 3.2 Confirm the regression uses profile-created durable env records rather than one-off `project easy instance launch --env-set` overrides.
- [x] 3.3 Confirm the regression does not depend on projected launch-profile YAML edits as the source of truth.

## 4. Verification

- [x] 4.1 Run the new focused test module or test case with `pixi run pytest <path-to-test>`.
- [x] 4.2 Run the relevant existing project-easy and local-interactive runtime tests with `pixi run pytest`.
- [x] 4.3 Run `openspec validate test-launch-profile-env-to-codex-tui --strict` and fix any artifact issues.
