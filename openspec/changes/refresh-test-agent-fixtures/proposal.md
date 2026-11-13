# Proposal

## Why

Test-agent creation still depends on host-specific auth bundle names, fixed provider routing, and launch assumptions that differ from the recently qualified CLI clients. Developers need reusable self-hosted and cloud API cases, with DeepSeek as the initial cloud configuration and local credential discovery that keeps auth files outside the checkout.

## What Changes

- Add secret-free `self-hosted` and `cloud-api` launch descriptors for Claude Code, Codex, and Kimi Code. Resolve the selected model, protocol endpoint, optional model capabilities, and credential source explicitly rather than inheriting Qwen/H20 settings.
- Use the existing `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL_ANTHROPIC`, and `DEEPSEEK_BASE_URL_OPENAI` variables for the cloud case. Parse an explicitly selected local `.env` as data; tracked files contain references and examples without real keys.
- Add a development helper under `scripts/agents/test-fixtures/` for bounded auth discovery, selected credential import, isolated preparation, and raw or managed test launches. Reuse current project credential, specialist, launch, and cleanup behavior.
- Keep native login state independent of endpoint-case selection. Discover supported Claude, Codex, and Kimi files from tool homes or explicit search roots, then copy selected files into a private host-local store without modifying the source.
- **BREAKING:** Replace repository-local live auth fixtures and account-specific defaults with an external credential root and external credential-bearing run roots. Stop resolving maintained workflows through `tests/fixtures/auth-bundles/`, `personal-a-default`, `kimi-coding`, or the fixed Yunwu setup.
- Refresh plain fixture setups and presets, repair maintained fixture consumers to use current scoped CLI surfaces, and update contributor guidance, manual smokes, demos, and their contract tests together.
- Add hermetic coverage for both cases, all three clients, and headless/unattended TUI preparation. Qualify DeepSeek with live runs and report self-hosted qualification against an explicitly configured non-Qwen3.8 model when available.
- Preserve sanitized historical usage captures and completed change-local launch aids as evidence. Future maintained launches do not depend on OpenSpec change directories or Qwen-specific wrappers.

## Capabilities

### New Capabilities

- `test-agent-launch-fixtures`: Generic endpoint cases, explicit client protocol mapping, local auth discovery/import, isolated test-agent preparation, maintained launch paths, and qualification evidence.

### Modified Capabilities

- `agent-fixture-contracts`: Separate tracked seed/launch fixtures from external live credentials and credential-bearing run state.
- `codex-openai-compatible-brain-profile`: Replace the fixed Yunwu setup/auth contract with a generic Responses-compatible setup and launch-resolved routing.
- `claude-official-login-fixture-smoke-validation`: Import the optional vendor-login bundle from the external local store into an isolated smoke run.
- `component-agent-construction`: Replace the required Yunwu preset variant with a generic API-compatible variant while retaining current preset and auth projection contracts.
- `minimal-agent-launch-demo`: Resolve selected fixture inputs and private run roots through the shared helper and use maintained project/scoped commands.
- `shared-tui-tracking-demo-pack`: Materialize selected credentials into external run-local state rather than linking repository-local auth fixtures.
- `deprecated-agents-fixture-removal`: Point credential guidance at the external local store while preserving removal of the deprecated broad fixture root.
- `ag-ui-workbench-app`: Update Kimi live-validation guidance to use the generic fixture preparation flow without changing GUI lifecycle ownership.

## Impact

- **Utility:** new test-fixture helper and reusable helper modules under `scripts/agents/test-fixtures/`; existing maintained qualification, exploration, demo, and manual entrypoints that create fixture-backed agents.
- **CI fixtures and tests:** `tests/fixtures/agent-launch/`, refreshed `tests/fixtures/plain-agent-def/`, synthetic auth-discovery fixtures, and unit/integration coverage. No live auth JSON becomes a tracked fixture.
- **Runtime integration:** current project credential and launch machinery remains authoritative. Adjust shared adapter/setup projection only where required to express the qualified launch configuration; do not add a second launcher or a general-purpose credential discovery service.
- **Local state and guidance:** XDG-based private credential/run directories, `AGENTS.md`, fixture documentation, managed qualification instructions, vendor-login documentation, and affected demo/app guides. Existing local credentials are not deleted or automatically moved.
- **Dependencies:** use the managed Python environment, existing YAML/configuration support, and standard-library filesystem/process facilities. No protocol proxy, model server, or cloud SDK dependency is introduced.
