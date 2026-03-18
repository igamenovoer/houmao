## Why

The current `shadow_only` completion gate can declare a prompt turn complete as soon as the TUI looks submit-ready again after any post-submit change. That is too weak for runtime-owned mailbox commands, where the correctness boundary is the sentinel-delimited JSON result rather than a generic "the surface looks idle again" snapshot.

Recent live investigation showed the failure mode clearly: `mail send` returned a sentinel parse error, but the Claude sender kept working in tmux, eventually delivered the message, and later printed a valid sentinel block. We need the runtime to wait for the explicit mailbox end contract instead of parsing too early.

## What Changes

- Tighten `shadow_only` completion behavior for runtime-owned mailbox commands so the runtime does not treat prompt reappearance plus coarse post-submit change as sufficient success evidence by itself.
- Add a command-aware completion path for mailbox operations that keeps polling available shadow text surfaces until the required sentinel-delimited mailbox result is actually visible or the bounded turn timeout/stall policy fires.
- Preserve the two-layer parser model: `business_state` still answers whether the TUI is changing, and `input_mode` still answers what kind of input is allowed, but command-owned completion may require stronger terminal evidence than `submit_ready`.
- Make the runtime treat generic shadow lifecycle completion as provisional for machine-critical sentinel-driven mailbox flows rather than as the final correctness boundary.
- Add coverage for the live-delayed-sentinel case so the runtime does not report mailbox failure when the agent is still actively completing the request.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `brain-launch-runtime`: `shadow_only` mailbox turns will use command-aware completion gating and SHALL not report mailbox success or mailbox parse failure until the sentinel-delimited mailbox result contract has either been observed or the command truly times out/fails.

## Impact

- Affected code: `src/houmao/agents/realm_controller/backends/cao_rest.py`, `src/houmao/agents/realm_controller/mail_commands.py`, and likely supporting runtime helpers around shadow completion/result extraction.
- Affected tests: runtime mailbox command tests plus live/demo coverage around the mailbox roundtrip sender path.
- Affected behavior: `shadow_only` prompt-turn completion for mailbox commands, especially real Claude sender flows that briefly re-expose a prompt before the final sentinel result is emitted.
- Risk area: completion gating and timeout behavior for machine-critical mailbox turns; generic prompt-turn behavior should remain unchanged unless explicitly covered by the new contract.
