## 1. Tutorial-Pack Parsing Policy

- [x] 1.1 Update the mailbox roundtrip tutorial-pack automation helpers so fresh automatic CAO-backed runs resolve `shadow_only` as the effective parsing mode for both participants and persist that value in `demo_state.json`.
- [x] 1.2 Ensure stepwise automatic `roundtrip` and `stop` reuse the persisted `shadow_only` mode for the same demo root instead of silently drifting to another parsing mode.
- [x] 1.3 Add an automatic-workflow guard that rejects `cao_only` requests or mixed-mode fallback attempts for this mailbox roundtrip coverage while keeping any broader debug-only override behavior explicit.

## 2. Live Coverage Updates

- [x] 2.1 Update `tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_live.py` so the live mailbox workflow starts both agents in `shadow_only` and treats Codex shadow parsing as the supported receiver path.
- [x] 2.2 Add regression coverage proving the automatic mailbox workflow fails clearly when invoked with `cao_only` instead of reporting a successful live roundtrip.
- [x] 2.3 Add regression coverage proving a `shadow_only` mailbox failure is surfaced directly and is not retried through `cao_only` for either participant.

## 3. Documentation And Verification

- [x] 3.1 Update the tutorial-pack README and any maintainer-facing automation docs to state that automatic mailbox roundtrip coverage uses `shadow_only` for both agents and that `cao_only` is debug-only for this workflow.
- [x] 3.2 Document in the same maintainer guidance that Codex shadow parsing is a supported part of the mailbox roundtrip automation contract, not an optional downgrade candidate.
- [x] 3.3 Run the targeted tutorial-pack live tests plus `pixi run openspec validate --type change --strict --no-interactive enforce-shadow-only-mailbox-roundtrip-automation` and record the results.
