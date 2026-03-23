## Why

The mail ping-pong gateway demo is intended to run Claude and Codex as unattended managed headless agents, but the demo build path currently drops the recipe-owned `operator_prompt_mode` before writing the runtime brain manifest. As a result, live participants are launched in interactive posture, launch policy is not applied, and interactive-only prompts or approvals can block the kickoff path before mailbox behavior is even exercised.

That bug was discovered through a real live demo run, not through the existing pytest-only coverage. Preserving operator prompt mode is necessary, but the repository still lacks one pack-owned automatic path that can rerun the real unattended flow, fail fast on missing prerequisites, preserve artifacts, and surface the next blocker after launch posture is fixed. Without that path, maintainers still have to reproduce this class of regression through ad hoc shell work.

## What Changes

- Preserve the tracked recipe `launch_policy.operator_prompt_mode` when the demo pack builds participant brain homes.
- Require the demo-owned launch path to materialize brain manifests that keep the selected operator prompt mode instead of silently defaulting to `interactive`.
- Require the live managed-headless participants launched by this demo pack to expose machine-readable launch posture evidence that confirms the tracked recipe mode, the built brain manifest mode, the live launch request mode, and whether launch policy was applied.
- Add a pack-local automatic hack-through-testing harness for one canonical unattended full-run case, plus an operator-facing interactive companion guide, so the real Claude/Codex mailbox path can be exercised without ad hoc orchestration.
- Require the live tmux inspection surface for those headless participants to show rolling console output while a turn is active, so user-observed hack-through testing can watch real progress without treating tmux as the source of state truth.
- Keep deterministic pytest coverage for narrow contract drift, but stop treating pytest alone as sufficient verification for this live unattended demo path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `mail-ping-pong-gateway-demo-pack`: startup must preserve tracked recipe operator prompt mode through brain build and managed headless launch, and the pack must expose one canonical automatic hack-through-testing path that verifies that launch posture during a real unattended run.

## Impact

- Affected code: `src/houmao/demo/mail_ping_pong_gateway_demo_pack/agents.py`, headless launch or runner surfaces that control tmux-visible console behavior, demo inspect/report helpers, pack-local autotest scripts under `scripts/demo/mail-ping-pong-gateway-demo-pack/`, and related demo tests.
- Affected systems: runtime brain manifest generation for this demo pack, live managed-headless launch posture verification, and the pack-owned live-run artifact contract used for automatic hack-through testing.
- No new external services are introduced, but the automatic HTT path will depend on real local `claude`, `codex`, `tmux`, and tracked credential material, with fail-fast preflight when they are unavailable.
