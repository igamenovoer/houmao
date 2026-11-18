# Tasks

## 1. Native-Aligned `DshToolParams`, Reasoning Ladder, and Permission Presets

- [ ] 1.1 Upgrade `DshPartialToolParams` and `DshEffectiveToolParams` in `src/houmao/agents/tool_params/dsh.py` and `src/houmao/agents/dsh_configuration.py` to support `deepseek/messages`, the four configurable `pi-ai` protocols, protocol-gated route and model `compat`, native modality fields, and `retry_policy`. Accept `api_key_env: null` only for endpoint-only `pi-ai/openai-completions`. Preserve keyed model and MCP merging and verify with `pixi run pytest tests/unit/agents/test_tool_params.py tests/unit/agents/test_dsh_configuration.py -q` and `pixi run typecheck`.
- [ ] 1.2 Implement native reasoning projection in `src/houmao/agents/tool_params/dsh.py`, `src/houmao/agents/dsh_configuration.py`, `src/houmao/agents/model_mapping_policy.py`, and the ACP override path. Test rejection of an empty or `'off'`-only effective map, quoted YAML keys, `0` with and without a declared `'off'` slot, canonical ordering and saturation, and preservation of `null` and custom wire strings. Verify that a non-reasoning `pi-ai` model emits `reasoningEfforts: false` with no provider default or ACP effort selection and that a DeepSeek Messages launch default of `off` permits a positive effort for one turn.
- [ ] 1.3 Update unattended Cordis patch generation in `src/houmao/agents/dsh_configuration.py` to register `houmao-unattended` (`sandbox: "workspace-write"`, `approval: "never"`) alongside `read-only`, `workspace-write`, and `danger-full-access` with `defaultPreset: "houmao-unattended"` in `id: permission` (`@deepseek-ai/dsh-permission-presets`), remove the duplicate Web-only `permission` patch block in `src/houmao/agents/realm_controller/backends/dsh_web.py`, and verify both `unattended` and `as_is` modes in `tests/unit/agents/test_dsh_configuration.py`.
- [ ] 1.4 Update starter DSH `tool-params.yaml` setups, `plain-agent-def` fixtures, launch policy notes, and `docs/reference/run-phase/dsh-headless.md` for `compat`, `reasoning_efforts`, and endpoint-only OpenAI-compatible routes. Quote `'off'` in YAML keys and string values. Document the placeholder authorization header and verify with `pixi run pytest tests/unit/agents/test_dsh_launch_surfaces.py tests/unit/agents/test_dsh_current_home.py -q`.

## 2. Credential Roles and Endpoint-Only Launch

- [ ] 2.1 In `src/houmao/srv_ctrl/commands/credentials.py`, persist endpoint and API-key roles beside `vars.env`. Add the role name and clear flags, validate distinct non-reserved identifiers, and use saved role names for updates and clearing. Test endpoint-only bundles, custom API-key redaction for `SGLANG_AUTH`, and preservation of other bundle entries in `tests/unit/srv_ctrl/`.
- [ ] 2.2 Match DSH provider references to the selected bundle roles during launch preflight and project those values into the native environment. Reject missing or mismatched roles and collisions with persistent or one-shot launch environment overrides. For an explicit endpoint-only OpenAI-compatible route, project the reserved native `apiKeyEnv` reference and supply the public placeholder in the native process environment. Test ACP and Web projection, unsupported protocol rejection, and omission of the placeholder value from persisted configuration with the DSH launch-surface tests and `pixi run typecheck`.

## 3. Secret-Redacted ACP and Web Error Diagnostics

- [ ] 3.1 Implement shared `sanitize_dsh_diagnostic()` (longest-first exact and URL-encoded secret scrubbing, bearer/API-key/token/cookie pattern scrubbing, and bounded single-line truncation) and wire it into `src/houmao/agents/realm_controller/backends/{dsh_acp_connection.py,dsh_acp_driver.py,dsh_acp.py}` for `DshAcpRequestError` JSON-RPC details and `DshAcpProtocolError` worker-stderr summaries, and verify with hermetic unit tests covering upstream HTTP `400` errors, startup crashes, and secret redaction.
- [ ] 3.2 Wire `sanitize_dsh_diagnostic()` into `src/houmao/agents/realm_controller/backends/dsh_web.py` for supervisor startup failures and `DshWebError` control operations while redacting launch tokens, session cookies, and API keys, update `docs/reference/run-phase/dsh-web.md`, and verify with unit tests covering Web startup and control error formatting.

## 4. Test Launch Fixtures and Campaign Harness Alignment

- [ ] 4.1 Update `scripts/agents/test-fixtures/` (`fixture.py`, `fixturelib/config.py`, `fixturelib/prepare.py`, `fixturelib/web.py`, `README.md`) and `tests/fixtures/agent-launch/{self-hosted.yaml,cloud-api.yaml,README.md}` to emit native-aligned DSH `tool_params` with `reasoning_efforts`, optional `--dsh-compat` / `HOUMAO_TEST_*_DSH_COMPAT`, optional `--dsh-protocol`, and explicit endpoint-only `api_key_env: null` for self-hosted `pi-ai/openai-completions`. Verify with `pixi run pytest tests/unit/agents/test_dsh_fixture_tools.py -q`.
- [ ] 4.2 Update DSH `tool_params` payloads across `tests/integration/agents/dsh/**` and `scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py`. Pass Qwen 3.8 `compat: {supports_developer_role: false}` and `reasoning_efforts: {'off': none, low: low, medium: medium, high: high}` through `houmao-mgr --tool-params`. Verify with `pixi run lint` and `pixi run typecheck`.

## 5. End-to-End Integration and Live Qualification

- [ ] 5.1 Execute `pixi run test` and the DSH integration suite (`tests/integration/agents/dsh/`) against the installed qualified `dsh` binary with isolated tmux servers. Use a controlled endpoint to verify an endpoint-only prompt reaches settlement with the expected authorization header and no ambient credential. Check that `provider-stderr.log` contains zero permission preset-mismatch errors.
- [ ] 5.2 Run live qualification via `scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py` against self-hosted SGLang `Qwen/Qwen3.8-27B-FP8` using an endpoint-only bundle. Require completed prompts through ACP (`b1`, level `0` sends `"none"` and level `1` sends `"low"`) and Web (`b2`). Verify redacted error output on a forced bad model or request, and record outcomes in `context/campaigns/debug/2026-11-18-houmao-3-0-interactive-review/`.

## Workflow follow-up

- Ensure prerequisite change `refactor-per-tool-params-pipeline` is applied and verified before applying `align-dsh-native-configuration`.
- Run `/openspec-verify-change`, sync specs, and archive `align-dsh-native-configuration` after review sign-off, linking GitHub issue #85.
