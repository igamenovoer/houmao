## Why

Houmao currently supports managed headless launches for Claude, Codex, and Gemini, but not Kimi Code CLI. Kimi Code now exposes a working non-interactive `kimi -p ... --output-format stream-json` path on this host, so Houmao can add first-class headless support without waiting for interactive TUI or ACP integration.

## What Changes

- Add `kimi_headless` as a maintained tmux-backed managed headless backend.
- Add `kimi` as a canonical headless output provider that parses Kimi assistant, tool, and session-resume JSONL events.
- Add Kimi launch policy registry coverage for unattended prompt-mode startup against Kimi Code CLI 0.10.x.
- Add Kimi tool adapter and starter-agent content using `KIMI_CODE_HOME`, projected skills, and OAuth/env-model credential support.
- Add Kimi model-name projection through Kimi's native `--model <alias>` prompt-mode flag.
- Allow passive-server managed headless launch and turn submission paths to accept Kimi headless agents.
- Keep Kimi ACP and interactive TUI support out of scope for this first change.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `brain-launch-runtime`: Add the Kimi headless backend, command construction, session persistence, resume behavior, and role bootstrap behavior.
- `headless-output-rendering`: Normalize Kimi `stream-json` output into canonical assistant, action request, action result, and session events.
- `versioned-launch-policy-registry`: Add a version-scoped unattended launch policy strategy for Kimi headless prompt mode.
- `houmao-mgr-project-agent-tools`: Add Kimi to maintained project-local tool families and starter adapter/setup content.
- `agent-model-selection`: Project launch-owned Kimi model selection through Kimi's native model alias startup surface.
- `passive-server-headless-management`: Accept Kimi as a supported server-managed headless backend.

## Impact

- Runtime backend code under `src/houmao/agents/realm_controller/`, including backend kind validation, headless command construction, session state, gateway attach/relaunch allowlists, and schemas.
- Canonical headless output parsing and rendering under `src/houmao/agents/realm_controller/backends/headless_output.py`.
- Launch policy models, registry, provider hooks or validation actions under `src/houmao/agents/launch_policy/`.
- Agent-definition adapter assets under `src/houmao/project/assets/starter_agents/tools/` and matching test fixtures under `tests/fixtures/plain-agent-def/tools/`.
- Brain build and model mapping paths for `KIMI_CODE_HOME`, Kimi skills, OAuth credentials, env-model credentials, and `--model` arguments.
- Passive server and manager command allowlists for managed headless agents.
- Documentation and tests covering Kimi command order, parser behavior, adapter projection, launch policy selection, and live smoke behavior with a fake or installed `kimi` executable.
