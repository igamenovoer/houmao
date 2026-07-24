## Why

Houmao currently collapses a busy TUI with no queued follow-up and a busy TUI that already holds a provider-native queued prompt into the same public state. Callers therefore cannot choose whether to submit during a busy turn, back off only when a prompt is already pending, or submit regardless, which can block important prompts unnecessarily or add unwanted work to a provider queue.

## What Changes

- Add `surface.pending_input` with `yes | no | unknown` semantics to the public tracked-TUI state, transitions, history, managed-agent projections, terminal-record artifacts, and replay comparison surfaces. The field describes provider-native submitted input waiting behind the active turn; it does not describe draft text or the gateway's durable request queue.
- Extend the Codex TUI, Claude Code, and Kimi Code profiles to detect pending submitted input. Claude detection will use bounded queue/composer structure and profile-owned rendering semantics, never an exact match for prompt-area suggestion wording.
- Replace the direct gateway prompt-control `force` boolean with an explicit admission policy: `ready_only`, `if_no_pending`, or `always`.
- Apply the policy to TUI prompt control as an observational decision over the latest tracked snapshot. The change will not add a compare-and-submit reservation or promise atomic behavior across concurrent submissions; two submissions may both reach the CLI before its pending surface repaints.
- Keep provider-native pending detection authoritative. Gateway submission notes will continue to provide explicit turn provenance but will not manufacture `surface.pending_input=yes` from Houmao's own dispatch history.
- **BREAKING**: remove the `force` request field, `--force` CLI option, and boolean `forced` result/error contract from direct gateway prompt control. No compatibility alias or shim will remain.
- Validate the detectors and admission policies with the existing UC05 recordings, manually audited labels, multi-count queue captures, cadence variants, deterministic gateway policy tests, and new live gateway qualification runs.
- Update the gateway and CLI reference documentation plus the packaged messaging skill to explain the pending state and the three admission policies.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `official-tui-state-tracking`: Add the provider-native pending-input observable to the authoritative public state and all live state projections.
- `versioned-tui-signal-profiles`: Require Codex, Claude, and Kimi profiles to derive pending-input evidence conservatively, with structural and style-aware Claude matching.
- `passive-server-tui-observation`: Include pending input in compact, detailed, and history responses for observed TUI agents.
- `terminal-record-replay`: Record, label, replay, and compare the pending-input observable from persisted pane snapshots.
- `shared-tui-tracking-recorded-validation`: Add pending input to strict public-state validation and cadence-stress coverage.
- `agent-gateway`: Replace binary force behavior with three explicit prompt-admission policies driven by readiness and pending-input state.
- `passive-server-gateway-proxy`: Forward the new admission policy and its result or refusal contract unchanged through managed-agent proxy routes.
- `docs-cli-reference`: Document the new gateway prompt option and removal of `--force`.
- `agent-gateway-reference-docs`: Explain pending-input state, observational admission semantics, and the policy decision table.
- `houmao-agent-messaging-skill`: Teach agents how to select the policy that matches the caller's desired busy/pending behavior.

## Impact

- Shared tracking models, reducer/session state, public response models, transition/history serialization, stability signatures, and provider-specific TUI profiles under `src/houmao/shared_tui_tracking/`.
- Gateway request/result/error models, prompt admission, clients, passive-server proxy models, `houmao-mgr agents single|self ... gateway prompt`, and their tests.
- Terminal recording, replay, labeling, comparison, and review-video paths used by TUI qualification.
- Existing recorded datasets under `tmp/houmao-dev-testing/` are test inputs only; implementation must resolve the recorded Claude version-provenance discrepancy and human-audit pattern-generated labels before treating them as qualification evidence.
- Public gateway prompt-control schemas and CLI calls are intentionally breaking. Headless prompt control remains overlap-safe and does not gain provider-native pending-queue semantics.
