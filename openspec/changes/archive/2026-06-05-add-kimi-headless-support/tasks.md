## 1. Runtime Type and Schema Plumbing

- [x] 1.1 Add `kimi_headless` to runtime backend kinds, launch surfaces, launch policy supported backend sets, server-managed backend allowlists, and headless output provider literals.
- [x] 1.2 Update launch-plan composition so tool `kimi` resolves to backend `kimi_headless`, uses `stream-json` headless output, and applies role content through bootstrap-message injection.
- [x] 1.3 Update runtime creation, resume, stopped-session relaunch, gateway attach, gateway state, and manifest preservation allowlists so Kimi follows the existing tmux-backed headless lifecycle.
- [x] 1.4 Update JSON schemas and boundary models that enumerate supported backends or headless providers.

## 2. Kimi Headless Backend and Output Parser

- [x] 2.1 Add `KimiHeadlessSession` with Kimi-specific command construction for new turns, exact resume via `--session <id>`, latest resume via `--continue`, and prompt placement immediately after `-p`.
- [x] 2.2 Ensure Kimi headless commands append `--output-format stream-json`, pass `--skills-dir <home>/skills`, and do not add `--auto`, `--yolo`, or `--plan`.
- [x] 2.3 Add Kimi canonical output parsing for assistant content, assistant tool calls, tool results, meta `session.resume_hint`, passthrough payloads, and diagnostics.
- [x] 2.4 Ensure Kimi session ids are extracted from canonical events and persisted in the headless session state for subsequent turns.

## 3. Kimi Tool Adapter, Home Projection, and Credentials

- [x] 3.1 Add starter Kimi tool content under `src/houmao/project/assets/starter_agents/tools/kimi/`, including `adapter.yaml` and a default setup bundle.
- [x] 3.2 Add matching plain-agent fixture Kimi tool content under `tests/fixtures/plain-agent-def/tools/kimi/`.
- [x] 3.3 Configure the Kimi adapter with `KIMI_CODE_HOME`, default executable `kimi`, setup destination `.`, skills destination `skills`, and `export_from_env_file` env injection.
- [x] 3.4 Add Kimi auth file mappings for `config.toml` and Kimi credential storage, and add allowlisted `KIMI_MODEL_*`, `KIMI_CODE_BASE_URL`, `KIMI_CODE_OAUTH_HOST`, and `KIMI_OAUTH_HOST` env variables.
- [x] 3.5 Add Kimi to managed system-skill destination mapping so Houmao-owned Kimi skills project under `<KIMI_CODE_HOME>/skills`.

## 4. Launch Policy, Launch Overrides, and Model Selection

- [x] 4.1 Add a Kimi launch policy registry file with a version-scoped unattended strategy for `kimi_headless` and Kimi Code CLI 0.10.x.
- [x] 4.2 Add launch policy validation or actions that reject or remove Kimi prompt-mode-incompatible flags such as `--auto`, `--yolo`, `--plan`, and bare `--session`.
- [x] 4.3 Add Kimi launch override backend metadata and backend-owned argument validation for `-p`, `--prompt`, `--output-format`, `--session`, `--resume`, `--continue`, and `--skills-dir`.
- [x] 4.4 Add Kimi model projection for config-backed or OAuth-backed homes through final CLI args `--model <alias>`.
- [x] 4.5 Handle Kimi env-model model overrides explicitly by either mutating projected `KIMI_MODEL_NAME` or rejecting unsupported override combinations with a clear error.

## 5. Passive Server and Manager Surfaces

- [x] 5.1 Update passive-server managed headless launch validation to accept `kimi_headless` and reject only backends outside the maintained headless set.
- [x] 5.2 Update managed-agent records, service helpers, and `houmao-mgr` server-control commands that enumerate supported headless backends.
- [x] 5.3 Update project-local tool administration surfaces so `houmao-mgr internals native-agent tools kimi` exposes `get` and `setups`.

## 6. Tests, Validation, and Documentation

- [x] 6.1 Add unit tests for Kimi command construction covering new turn, exact resume, latest resume, prompt placement, `--skills-dir`, and output-format behavior.
- [x] 6.2 Add unit tests for Kimi canonical parser behavior covering assistant content, tool calls, tool results, resume hints, passthrough events, and session-id extraction.
- [x] 6.3 Add unit tests for Kimi launch policy selection, conflict rejection, absolute executable version probing, and unknown-version failure.
- [x] 6.4 Add unit tests for Kimi adapter parsing, brain-builder projection, Kimi auth env allowlisting, Kimi system-skill destination, and Kimi model projection.
- [x] 6.5 Add an integration test with a fake `kimi` executable that emits stream JSON and verifies first-turn session capture plus follow-up resume command order.
- [x] 6.6 Update reference documentation for supported headless backends, launch policy, run-phase behavior, project tool adapters, and passive-server managed headless support.
- [x] 6.7 Run `pixi run lint`, `pixi run typecheck`, and the relevant unit/runtime test suites for the changed surfaces.
