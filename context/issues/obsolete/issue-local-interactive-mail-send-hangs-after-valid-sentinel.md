# Issue: Local Interactive `agents mail send` Can Hang After A Valid Sentinel Result

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P1 — Real mailbox delivery succeeds, but the operator-facing CLI can remain stuck and fail to return promptly.

## Status
Open as of 2026-03-29.

## Summary

During unattended Claude TUI mailbox testing, the local-interactive mail path reached all of the success conditions that should be sufficient to complete the command:

1. the agent accepted the runtime-owned mailbox prompt,
2. the filesystem delivery helper returned `ok: true`,
3. the agent emitted a valid `AGENTSYS_MAIL_RESULT_BEGIN` / `AGENTSYS_MAIL_RESULT_END` block for the active `request_id`,
4. the email was persisted and readable from the mailbox CLI.

Despite that, `pixi run houmao-mgr agents mail send ...` still did not return promptly. The client process remained live until the tmux session was interrupted or stopped.

## Reproduction

The issue was reproduced in the clean-start testcase recorded at:

- `context/tasks/testcases/20260329-150956-project-easy-claude-self-mailbox-roundtrip.md`

Operator flow used:

1. delete `.houmao/`
2. `pixi run houmao-mgr project init`
3. create a Claude specialist in unattended mode
4. initialize the project mailbox root
5. launch a local-interactive Claude instance with filesystem mailbox transport
6. register the agent mailbox binding
7. run:

```bash
pixi run houmao-mgr agents mail send \
  --agent-name claude-self-1551u \
  --to AGENTSYS-claude-self-1551u@agents.localhost \
  --subject 'Self mailbox smoke 2026-03-29 unattended 1551 final' \
  --body-content 'Roundtrip check from Claude to itself in unattended mode after request-aware shadow parsing.'
```

## Evidence

The delivered message exists and is readable:

- canonical message path:
  - `.houmao/mailbox/messages/2026-03-29/msg-20260329T160156Z-d0fab048358240dd91f159b5754ac1d5.md`
- sender:
  - `AGENTSYS-claude-self-1551u@agents.localhost`
- recipient:
  - `AGENTSYS-claude-self-1551u@agents.localhost`
- subject:
  - `Self mailbox smoke 2026-03-29 unattended 1551 final`

The tmux pane for the live Claude run also showed the valid machine result block for the active request:

```text
AGENTSYS_MAIL_RESULT_BEGIN
{
  "message_id": "msg-20260329T160156Z-d0fab048358240dd91f159b5754ac1d5",
  "ok": true,
  "operation": "send",
  "principal_id": "AGENTSYS-claude-self-1551u",
  "recipient_count": 1,
  "request_id": "mailreq-20260329T160141Z-1b7362a5e1",
  "transport": "filesystem"
}
AGENTSYS_MAIL_RESULT_END
```

But the corresponding `houmao-mgr agents mail send` process still did not exit normally during the observation window. After the instance was stopped, the stuck client finally failed with a backend error caused by the missing tmux session, which confirms the client was still waiting on the local-interactive control path rather than having already completed.

## Root Cause

Log injection on 2026-03-29 isolated the failure to the post-submit surface-diff logic inside the local-interactive shadow observer.

Observed from the injected debug log:

1. `baseline_output` stopped being a stable prefix immediately after the new turn started.
2. Every poll therefore reported `startswith_baseline=false`.
3. Because `_trim_post_submit_text(...)` only trims when `current_text.startswith(baseline_text)`, the observer fell back to using the full current surface instead of a true post-submit delta.
4. In that full-surface mode:
   - `shadow_post_submit.raw_text` contained zero standalone sentinel blocks,
   - `shadow_post_submit.normalized_text` contained zero standalone sentinel blocks,
   - `shadow_post_submit.dialog_text` eventually contained two standalone blocks: the previous successful send and the current send.
5. The active-request gate calls `_parse_mail_result_text(...)`, which currently requires exactly one sentinel-delimited block in the candidate text.
6. Since the only surface with standalone blocks contained both the old and the new block, parsing never succeeded for the active request, so `matched` stayed false forever.

So the root cause is not mailbox delivery failure and not active-request mismatch anymore. It is:

- local-interactive post-submit diffing is unstable once the pane reflows or scroll state changes,
- that instability causes fallback to whole-surface parsing,
- whole-surface parsing can include multiple mailbox result blocks from prior turns,
- and the current parser rejects that surface because it insists on exactly one block.

In short:

```text
baseline invalidation -> whole-surface fallback -> multiple visible sentinel blocks -> active-result parser never matches -> poll loop hangs
```

## Log-Injection Findings

The injected debug log showed this pattern for the stuck second send:

- initial baseline:
  - `baseline_len=9589`
  - `baseline_pos=6881`
- first poll after submit already had:
  - `startswith_baseline=false`
  - `dialog_text` still showing only the previous request id `mailreq-20260329T162129Z-e8f77a531c`
- later polls after the new message had been delivered showed:
  - `raw_text.block_count=0`
  - `normalized_text.block_count=0`
  - `dialog_text.block_count=2`
  - request ids:
    - `mailreq-20260329T162129Z-e8f77a531c`
    - `mailreq-20260329T162255Z-61ca887eea`
  - `matched=false` on every poll

That directly explains why a fresh visible sentinel for the active request was still insufficient to let the command return.

## What Is Already Fixed

This issue is narrower than the earlier mailbox failures observed in the same test stream.

The following problems were already mitigated in the workspace before this note was written:

1. local-interactive mailbox timeout budget was too short for unattended Claude sender turns,
2. mailbox shadow completion could match stale sentinel blocks from an earlier request instead of the active `request_id`.

Those fixes made the run progress far enough to deliver the message and surface the correct active-request sentinel. The remaining problem is what happens after that point.

## Suspected Boundary

The remaining bug appears to be in the local-interactive mail completion path after valid result detection, not in filesystem mailbox delivery itself.

Most likely touch points:

- `src/houmao/agents/realm_controller/backends/local_interactive.py`
- `src/houmao/agents/realm_controller/mail_commands.py`
- `src/houmao/agents/realm_controller/runtime.py`
- managed-agent prompt execution / event return plumbing after `send_mail_prompt(...)`

More specifically, the problematic interaction is between:

- baseline trimming in `build_shadow_mail_result_surface_payloads(...)`
- the prefix-only logic in `_trim_post_submit_text(...)`
- the `exactly one sentinel block` requirement in `_parse_mail_result_text(...)`
- long-lived tmux panes that still visibly contain prior mailbox result blocks

## Why This Matters

From the operator point of view, mailbox delivery alone is not enough. The command contract is:

1. deliver or fail explicitly,
2. return control to the CLI,
3. surface the machine-readable result for the active request.

If the message is delivered but the command still hangs, automation cannot trust the exit status or use the CLI as a completion signal.

## Acceptance Criteria

1. `houmao-mgr agents mail send` returns success after a valid active-request sentinel block is emitted by a local-interactive TUI agent.
2. The returned payload corresponds to the active `request_id`, not any older mailbox turn still visible in pane scrollback.
3. Successful delivery does not require manual interrupt or instance teardown for the CLI to exit.
4. A focused automated test reproduces the previous hang boundary and verifies normal return after sentinel detection.

## Connections

- testcase:
  - `context/tasks/testcases/20260329-150956-project-easy-claude-self-mailbox-roundtrip.md`
- related known issues:
  - `context/issues/known/issue-007-shadow-mail-result-observer-gated-by-generic-completion.md`
  - `context/issues/known/issue-008-mailbox-prompt-should-not-reference-skill-install-paths.md`
