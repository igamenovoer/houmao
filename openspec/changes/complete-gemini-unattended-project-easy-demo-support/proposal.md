## Why

Houmao now has reliable Gemini headless runtime/auth support, but the maintained operator stack still stops one layer above that. Gemini is still excluded from the unattended launch-policy lane, `project easy specialist create` still persists Gemini as `launch.prompt_mode: as_is`, and the supported `single-agent-gateway-wakeup-headless` demo still only claims Claude and Codex.

## What Changes

- Add maintained Gemini unattended launch-policy support for the `gemini_headless` backend, including version-scoped registry coverage and runtime-owned startup preparation.
- Change `houmao-mgr project easy specialist create --tool gemini` so the maintained easy path persists unattended launch posture by default, with `--no-unattended` continuing to opt out to `as_is`.
- Keep Gemini headless-only on the `project easy` instance surface while making that headless lane a maintained unattended path rather than a best-effort passthrough.
- Expand `scripts/demo/single-agent-gateway-wakeup-headless/` from two maintained lanes to three maintained lanes by adding Gemini.
- Update the demo parameters, runtime/auth import flow, matrix coverage, and maintained demo docs so Gemini is treated as part of the supported pack rather than as an explicit exclusion.
- Add regression coverage for Gemini unattended specialist creation, Gemini-compatible launch-policy resolution, and the demo pack's Gemini lane assumptions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: Gemini headless unattended startup needs a maintained positive runtime contract instead of only the current fail-closed unsupported-backend path.
- `versioned-launch-policy-registry`: the registry needs a maintained Gemini unattended strategy family with declared version support, evidence, owned paths, and ordered actions.
- `houmao-mgr-project-easy-cli`: project-easy specialist creation needs to treat Gemini as a maintained unattended easy lane for headless use instead of forcing the default launch posture to `as_is`.
- `single-agent-gateway-wakeup-headless-demo`: the supported headless gateway wake-up demo needs to expand from Claude/Codex to Claude/Codex/Gemini and describe the Gemini lane's auth and launch expectations.

## Impact

- Affected code:
  - `src/houmao/agents/launch_policy/registry/`
  - `src/houmao/agents/launch_policy/engine.py`
  - `src/houmao/srv_ctrl/commands/project.py`
  - `src/houmao/demo/single_agent_gateway_wakeup_headless/`
  - `scripts/demo/single-agent-gateway-wakeup-headless/`
- Affected tests:
  - launch-policy coverage
  - `project easy` specialist/create coverage
  - headless gateway demo-pack coverage
- Affected docs:
  - supported demo docs and README surfaces
  - easy-specialist and CLI guidance for Gemini unattended launch posture
