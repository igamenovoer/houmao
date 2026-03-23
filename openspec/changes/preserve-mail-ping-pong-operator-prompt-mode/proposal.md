## Why

The mail ping-pong gateway demo is intended to run Claude and Codex as unattended managed headless agents, but the demo build path currently drops the recipe-owned `operator_prompt_mode` before writing the runtime brain manifest. As a result, live participants are launched in interactive posture, launch policy is not applied, and interactive-only prompts or approvals can block the kickoff path before mailbox behavior is even exercised.

## What Changes

- Preserve the tracked recipe `launch_policy.operator_prompt_mode` when the demo pack builds participant brain homes.
- Require the demo-owned launch path to materialize brain manifests that keep the selected operator prompt mode instead of silently defaulting to `interactive`.
- Require the live managed-headless participants launched by this demo pack to expose launch-policy provenance consistent with the tracked recipe when unattended mode is requested.
- Add regression coverage so the demo pack detects future drift between tracked recipe launch intent and the actual live managed-headless launch posture.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mail-ping-pong-gateway-demo-pack`: startup requirements must preserve tracked recipe operator prompt mode through brain build and managed headless launch.

## Impact

- Affected code: `src/houmao/demo/mail_ping_pong_gateway_demo_pack/agents.py`, related demo tests, and demo README or artifact expectations if they surface launch posture.
- Affected systems: runtime brain manifest generation for this demo pack and live managed-headless launch posture verification.
- No new external dependencies or public API families are expected.
