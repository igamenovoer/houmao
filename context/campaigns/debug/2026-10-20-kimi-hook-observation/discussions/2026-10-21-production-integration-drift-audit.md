# Discussion: Production Integration Freeze and Drift Audit

Date: 2026-10-21. Campaign: [debug-intent.md](../debug-intent.md). Change: `openspec/changes/add-kimi-hook-observation/` (applied; 23/23 tasks).

## Freeze Audit

`scripts/explore/kimi-hook-observation/` has no commits since the campaign-resolution commit (`c1b83dee`); the harness remains frozen campaign evidence. The production implementation **ported** from it (never imported): `kimi_hooks.py` → `src/houmao/hook_observation/kimi_hooks_generator.py`; `replay_reduce.py` expectations → `tests/unit/hook_observation/fixtures/kimi/` (11 sanitized streams, 96 events) replayed in `test_kimi_fixtures.py`; collector/emitter semantics were already production infrastructure from the Claude/Codex adapters.

## Drift Audit

- **Version drift at the supported floor**: the wave-5 live smoke repeated the multi-turn leg against a side-by-side kimi **2.1.1** install (the `kimi.yaml` floor): PASS with all 20 `[[hooks]]` entries validated and accepted by the provider. No event-name or schema-key drift exists between 2.1.1 and 2.2.0 for the subscribed set. Evidence: `tmp/kimi-hook-smoke/floor-20261020T155415Z/` (gitignored).
- **Upstream pin caveat**: the campaign baseline `extern/orphan/kimi-code` @ `67325c1` carries an unreleased patch changeset (`hooks-session-cwd.md`) fixing hook cwd for server-started sessions. The TUI lane is unaffected (the process starts in the project dir; all captures showed `cwd` = workdir). No action; noted for the kap-server follow-up.
- **Silent-family status unchanged in production**: `StopFailure`, `TaskStarted`, `Notification`, and `PermissionResult(cancelled|error)` remain unexercised live; they are subscribed, normalized, and counted in diagnostics per the adapter's tolerated-silent-families requirement.

## Corrections Registered During Apply

- The campaign replay correction (S7 resume generation 2 starts at `turn_id=1`, not 0) is the reducer's implemented semantics; production fixtures replay it that way.
- Wave 3 found a latent integration crash the campaign did not cover: the launch-policy TOML writer cannot re-render a persisted `[[hooks]]` array-of-tables. The managed path strips the Houmao-owned marker block before policy synthesis and re-installs it after (fresh and relaunch orders both regression-tested). Operator-authored hooks outside the marker block in a policy-synthesized home would still hit the writer's limit; that is a pre-existing launch-policy constraint, not a regression.
