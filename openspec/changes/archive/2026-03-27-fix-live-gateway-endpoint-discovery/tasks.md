## 1. Runtime Discovery Contract

- [x] 1.1 Extend `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` to return optional validated live gateway endpoint data and to follow the current-session discovery order of process env first, tmux session env second, validation last.
- [x] 1.2 Reuse existing gateway validation and health checks so stale process-env, tmux-env, or registry-discovered gateway bindings resolve as unavailable instead of guessed endpoints.
- [x] 1.3 Document that the manifest remains stable authority, the shared registry is the cross-session locator layer, and `<session-root>/gateway/run/current-instance.json` is the authoritative local live-gateway record.

## 2. Prompt And Skill Adoption

- [x] 2.1 Update projected mailbox system-skill guidance to obtain attached `/v1/mail/*` endpoint data from the runtime-owned live resolver.
- [x] 2.2 Update gateway notifier prompt generation to remain actionable through the same runtime-owned endpoint discovery contract.
- [x] 2.3 Audit other runtime-owned gateway-first mailbox prompts or helpers for instructions that still imply localhost default guessing or a discovery order that conflicts with current-session env and tmux fallback rules.

## 3. Regression Coverage

- [x] 3.1 Add unit coverage for the live-session mismatch where tmux session env has gateway bindings and the provider process env snapshot does not.
- [x] 3.2 Add notifier-prompt coverage asserting the prompt exposes an actionable runtime-owned path to the exact live gateway endpoint.
- [x] 3.3 Add coverage for cross-session gateway recovery through shared-registry `runtime.manifest_path` plus the session-owned live gateway record.
- [x] 3.4 Add integration or demo regression coverage proving attached shared-mailbox work does not depend on ad hoc gateway endpoint rediscovery.
