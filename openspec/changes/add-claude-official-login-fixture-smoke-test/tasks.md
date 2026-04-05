## 1. Fixture Contract And Guidance

- [x] 1.1 Update the Claude fixture guidance under `tests/fixtures/agents/` to document the local-only `official-login` bundle, current dotfile names, and the rule that `claude_state.template.json` is not required for this lane.
- [x] 1.2 Add one repo-owned smoke-validation instruction surface for the `official-login` flow, using `server-api-smoke`, `HOUMAO_AGENT_DEF_DIR`, and a temp workdir under `tmp/`.

## 2. Runtime Behavior And Coverage

- [x] 2.1 Update the Claude startup/bootstrap path as needed so projected `.credentials.json` plus a minimized projected `.claude.json` is accepted without requiring `claude_state.template.json`.
- [x] 2.2 Add or update automated coverage that proves a minimized projected `.claude.json` such as `{}` remains a valid unattended startup seed alongside projected `.credentials.json`.

## 3. Local Fixture Provisioning And Validation

- [x] 3.1 Provision the local-only `tests/fixtures/agents/tools/claude/auth/official-login/` bundle with vendor `.credentials.json` and a minimized `.claude.json` using the current adapter filenames, without committing plaintext secret material.
- [x] 3.2 Run the supported smoke launch from `tmp/<subdir>` with `pixi run houmao-mgr agents launch --agents server-api-smoke --provider claude_code --auth official-login --headless --yolo` and record whether the launch succeeds.
