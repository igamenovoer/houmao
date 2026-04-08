# Issue 007: Shadow Mail Result Observer Was Gated Behind Generic Completion

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P0 — Valid live mailbox results can still time out instead of returning success.

## Status
Fixed on `devel` as of 2026-03-18. Originally fixed in the HTT worktree, now applied to the main workspace.

## Summary

The shadow-only mailbox path had a second completion bug beyond the prompt-echo false positive tracked in issue-001.

Even after tightening sentinel extraction, the mailbox completion observer still only ran after the generic shadow lifecycle decided the turn was complete. In real sender runs, that assumption was too strong: the sender could already have emitted a valid sentinel-delimited mailbox result while the generic Claude shadow parser still classified the surface as `working+freeform`.

That meant the runtime could miss a real mailbox result block entirely and still time out with:

```text
Mailbox command failed: Timed out waiting for shadow turn completion (... shadow_status=working+freeform)
```

## What Failed

Observed during real-agent HTT on 2026-03-18:

1. The sender accepted the runtime-owned mailbox prompt.
2. A saved live Claude trace showed a valid `AGENTSYS_MAIL_RESULT_BEGIN` / `AGENTSYS_MAIL_RESULT_END` block later in the turn.
3. The runtime still timed out in `_wait_for_shadow_completion()` instead of returning the mailbox result.

The issue was not mailbox parsing itself. The observer that collects mailbox result surfaces was simply never given a chance to examine those later snapshots unless generic shadow completion had already fired.

## Root Cause

`_wait_for_shadow_completion()` coupled mailbox-result observation to the generic shadow lifecycle state machine:

- generic shadow lifecycle said when the turn was "complete"
- mailbox observer only ran inside the `runtime_state == "completed"` branch

That coupling is wrong for mailbox turns because the mailbox correctness boundary is the sentinel-delimited result contract, not the generic shadow parser's completion label.

When the parser remained in `working` despite a visible result block, the observer never ran and the command timed out.

## Affected Code

- `src/houmao/agents/realm_controller/backends/cao_rest.py`
  - `_TurnMonitor`
  - `_wait_for_shadow_completion()`

## Fix Applied

The fix keeps generic non-mail shadow behavior unchanged but decouples mailbox-result observation from generic completion:

1. Added `_TurnMonitor.saw_post_submit_activity()` to expose whether the turn has shown real post-submit movement.
2. Updated `_wait_for_shadow_completion()` so that mailbox `completion_observer` runs on every post-submit shadow poll after activity is observed, not only after `runtime_state == "completed"`.
3. If the observer finds a valid mailbox-result surface payload, the turn returns immediately with that payload.
4. Existing blocked-operator, unsupported-surface, disconnect, stall, and timeout behavior remains intact when no mailbox result is visible.

This makes mailbox completion depend on the mailbox contract itself rather than on the generic shadow parser finishing first.

## Verification

- Added focused coverage in `tests/unit/agents/realm_controller/test_cao_client_and_profile.py`:
  - `test_cao_codex_shadow_mail_prompt_waits_for_post_submit_sentinel`
  - `test_cao_codex_shadow_mail_prompt_detects_result_while_shadow_stays_working`
- Verified with:

```bash
pixi run pytest tests/unit/agents/realm_controller/test_cao_client_and_profile.py -k 'shadow_mail_prompt'
```

Those tests pass in the HTT worktree after the fix.

## Residual Note

This fix does not make the full real-agent autotest pass by itself.

Later reruns exposed a separate sender-side problem where Claude spent the turn searching for mailbox skill and env context, never delivered mail, and therefore never emitted any result block at all. That is a different issue from this observer-gating bug.

## Connections

- Companion fix to issue-001 (now fixed on `devel`). Together these two close the mailbox shadow completion reliability gap:
  - issue-001 fixed the false positive (observer too loose — prompt-echo sentinel mentions)
  - issue-007 fixed the false negative (observer gated behind generic completion)
- Together they resolve HTT cascade layer 3 and the HTT issue's "Desired Direction" point 5 ("Tighten the mailbox control contract")
- Exposed during the HTT work tracked in `context/issues/known/issue-real-agent-htt-worktree-runs-mix-snapshot-and-host-state.md`
- Adds mutable state to `_TurnMonitor`, expanding the scope of the Rx rewrite in issue-002
