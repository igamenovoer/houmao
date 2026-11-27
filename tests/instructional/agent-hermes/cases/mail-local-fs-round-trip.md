# Local Filesystem Mail Round Trip and Notifier Guardrails

Two managed Hermes agents (`agent-a` in `service` mode and `agent-b` in `tui` mode) share one run-local filesystem (`offline`) mailbox store. The scenario verifies operator-posted wake-up, `peek` non-mutation, agent reply and archive via `houmao-process-emails-via-gateway`, atomic SQLite `unread_count == 0` thread-summary updates on archive, a two-agent offline round trip without reply loops, and negative notifier guardrails (unconfigured binding refusal, unsupported `compact` policy refusal, and `unread_only` ignoring read/archived mail).

## Sub-cases

- `f1-operator-post-peek-and-wake`: an operator posts an offline message to `agent-b`; `mail peek` leaves `read == false`; enabling `agent-b`'s `offline` notifier wakes `agent-b` (`hermes_tui`), which replies and archives the original; independent store inspection confirms `unread_count == 0` in `agent-b`'s thread summary.
- `f2-two-agent-offline-round-trip`: `agent-a` (`hermes_service`) emails a workspace-backed question to `agent-b` (`hermes_tui`) over `offline` mail; `agent-b` wakes, reads its workspace file, replies in thread, and archives; `agent-a`'s `offline` notifier wakes on the reply and archives it without triggering a reply loop.
- `f3-negative-notifier-guardrails`: enabling `offline` notifier before joining an offline mailbox fails explicitly; enabling `pre_notification_context_action=compact` fails explicitly as unsupported on Hermes; `unread_only` ignores an already-read unarchived message and never re-notifies for archived mail.

## How to get to it (user POV)

- The operator launches `agent-a` (`service`) and `agent-b` (`tui`) with the `hermes-worker.md` role and default system skills. Hermes opens `houmao-agent-entrypoint`, which delegates to `houmao-shared-routines` for the protected `process-emails-via-gateway` route.
- Before joining `offline`, the operator verifies the negative unconfigured-notifier check, then initializes `$RUN_TMP/runtime/mailbox` via `hermes_lab.py offline-setup`, drives operator and agent-to-agent offline mail, and cross-checks both the `houmao-mgr mailbox messages list` projection and the recipient-local SQLite thread summary.

## Driving it with hermes_lab

Preconditions:

- `fixture.py check --pool-slot a --mode service --surface manager --live` and `--pool-slot b --mode tui --surface manager --live` both exit `0`.
- `CASE_EVIDENCE="$EVIDENCE/mail-local-fs-round-trip"` exists (`mkdir -p "$CASE_EVIDENCE"`).
- `OFFLINE_ROOT="$RUN_TMP/runtime/mailbox"` and neutral token `TOKEN="harbor-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"`.

- **Prepare and launch `agent-a` (`service`) and `agent-b` (`tui`), and verify negative unconfigured notifier (`f3`).**

```bash
pixi run python "$FIXTURE" prepare \
  --pool-slot a --mode service --surface manager \
  --prompt-mode unattended --tmux-server new --reasoning-level 5 \
  --role hermes-mail-a --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-fs-a" > "$CASE_EVIDENCE/a-prepare.json"
export RUN_FS_A="$(jq -er '.run_dir' "$CASE_EVIDENCE/a-prepare.json")"

pixi run python "$FIXTURE" prepare \
  --pool-slot b --mode tui --surface manager \
  --prompt-mode unattended --tmux-server new --reasoning-level 5 \
  --role hermes-mail-b --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-fs-b" > "$CASE_EVIDENCE/b-prepare.json"
export RUN_FS_B="$(jq -er '.run_dir' "$CASE_EVIDENCE/b-prepare.json")"

pixi run python "$FIXTURE" launch --run-dir "$RUN_FS_A" > "$CASE_EVIDENCE/a-launch.json"
pixi run python "$FIXTURE" launch --run-dir "$RUN_FS_B" > "$CASE_EVIDENCE/b-launch.json"

pixi run python "$LAB" notifier --run-dir "$RUN_FS_B" --channel offline --action enable \
  --interval-seconds 15 --mode unread_only --allow-error \
  > "$CASE_EVIDENCE/negative-unconfigured-notifier.json"
```

- **Initialize both fixture registries against the shared local FS mailbox, join both agents, and verify unsupported `compact` (`f1`, `f3`).**

```bash
export OFFLINE_ROOT="$RUN_TMP/runtime/mailbox"
export ADDR_FS_A="hermes-a-${TOKEN}@houmao.localhost"
export ADDR_FS_B="hermes-b-${TOKEN}@houmao.localhost"
printf 'beacon-code=indigo-91\n' > "$RUN_FS_B/workdir/beacon.txt"

pixi run python "$LAB" offline-setup \
  --mailbox-root "$OFFLINE_ROOT" \
  --binding "$RUN_FS_A=$ADDR_FS_A" \
  --binding "$RUN_FS_B=$ADDR_FS_B" \
  > "$CASE_EVIDENCE/offline-setup.json"

pixi run python "$LAB" doctor --run-dir "$RUN_FS_A" --run-dir "$RUN_FS_B" \
  --expected-effort xhigh --mailbox-root "$OFFLINE_ROOT" \
  > "$CASE_EVIDENCE/doctor.json"

pixi run python "$LAB" notifier --run-dir "$RUN_FS_B" --channel offline --action enable \
  --interval-seconds 15 --mode unread_only --pre-notification-context-action compact --allow-error \
  > "$CASE_EVIDENCE/negative-compact-policy.json"
```

- **Operator post, `peek` non-mutation check, and `offline` notifier wake with Ink detached (`f1`).**

```bash
pixi run python "$LAB" manager --run-dir "$RUN_FS_B" --mailbox-root "$OFFLINE_ROOT" -- \
  mail post --channel offline --subject "Local status check $TOKEN" \
  --body-content "Read beacon.txt in your workspace, reply with the beacon-code value, and archive this message." \
  > "$CASE_EVIDENCE/operator-post.json"

pixi run python "$LAB" manager --run-dir "$RUN_FS_B" --mailbox-root "$OFFLINE_ROOT" -- \
  mail list --channel offline --box inbox > "$CASE_EVIDENCE/b-list-before-peek.json"
export OP_REF="$(jq -er '.messages[0].message_ref // .items[0].message_ref' "$CASE_EVIDENCE/b-list-before-peek.json")"
pixi run python "$LAB" manager --run-dir "$RUN_FS_B" --mailbox-root "$OFFLINE_ROOT" -- \
  mail peek --channel offline --message-ref "$OP_REF" > "$CASE_EVIDENCE/b-peek.json"
pixi run python "$LAB" manager --run-dir "$RUN_FS_B" --mailbox-root "$OFFLINE_ROOT" -- \
  mail list --channel offline --box inbox > "$CASE_EVIDENCE/b-list-after-peek.json"
jq -e --arg ref "$OP_REF" \
  'any(.messages[]; .message_ref == $ref and .read == false)' "$CASE_EVIDENCE/b-list-after-peek.json" >/dev/null

pixi run python "$LAB" state --run-dir "$RUN_FS_B" > "$CASE_EVIDENCE/b-state-before-detach.json"
FS_B_SOCKET="$(jq -er '.tmux_socket_path' "$RUN_FS_B/run.json")"
FS_B_SESSION="$(jq -er '.state.identity.tmux_session_name' "$CASE_EVIDENCE/b-state-before-detach.json")"
env -u TMUX -u TMUX_PANE -u TMUX_TMPDIR tmux -S "$FS_B_SOCKET" kill-session -t "$FS_B_SESSION"
pixi run python "$LAB" state --run-dir "$RUN_FS_B" > "$CASE_EVIDENCE/b-state-detached.json"
jq -e '.state.control | .terminal_attachment == "detached" and .owner_available' \
  "$CASE_EVIDENCE/b-state-detached.json" >/dev/null

pixi run python "$LAB" notifier --run-dir "$RUN_FS_B" --channel offline --action enable \
  --interval-seconds 15 --mode unread_only --mailbox-root "$OFFLINE_ROOT" \
  --appendix-text "Handle open offline mail using your Houmao mailbox skill, reply concisely, and archive after the reply succeeds." \
  > "$CASE_EVIDENCE/b-notifier-enabled.json"

pixi run python "$LAB" offline-wait --mailbox-root "$OFFLINE_ROOT" --run-dir "$RUN_FS_B" \
  --address "$ADDR_FS_B" --tag "$TOKEN" --box inbox --expect-absent --timeout 240 \
  > "$CASE_EVIDENCE/b-inbox-cleared-op.json"
pixi run python "$LAB" offline-observe --mailbox-root "$OFFLINE_ROOT" --run-dir "$RUN_FS_B" \
  --address "$ADDR_FS_B" > "$CASE_EVIDENCE/b-observe-after-op.json"
jq -e --arg tag "$TOKEN" \
  '(.messages.messages[] | select(.folder == "archive" and (.subject | contains($tag))) | .thread_id) as $thread |
    any(.thread_summaries[].row; .thread_id == $thread and .unread_count == 0)' \
  "$CASE_EVIDENCE/b-observe-after-op.json" >/dev/null
pixi run python "$LAB" notifier --run-dir "$RUN_FS_B" --channel offline --action status \
  --mailbox-root "$OFFLINE_ROOT" > "$CASE_EVIDENCE/b-notifier-status-op.json"
```

- **Two-agent offline round trip (`f2`).** Enable `agent-a`'s `offline` notifier (archive confirmations without replying), then prompt `agent-a` to email `agent-b`:

```bash
export TOKEN2="pier-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
pixi run python "$LAB" notifier --run-dir "$RUN_FS_A" --channel offline --action enable \
  --interval-seconds 15 --mode unread_only --mailbox-root "$OFFLINE_ROOT" \
  --appendix-text "When an offline inbox message is a reply or confirmation with no further action, archive it without replying." \
  > "$CASE_EVIDENCE/a-notifier-enabled.json"

pixi run python "$FIXTURE" prompt --run-dir "$RUN_FS_A" \
  --prompt "Use your Houmao mailbox skill to send an offline email to $ADDR_FS_B with subject 'Workspace lookup $TOKEN2' asking the recipient to read beacon.txt and reply with the beacon-code value. Stop after the send succeeds." \
  > "$CASE_EVIDENCE/a-send-prompt.json"

pixi run python "$LAB" offline-wait --mailbox-root "$OFFLINE_ROOT" --run-dir "$RUN_FS_A" \
  --address "$ADDR_FS_A" --tag "$TOKEN2" --box archive --timeout 300 \
  > "$CASE_EVIDENCE/a-reply-observed.json"
pixi run python "$LAB" offline-wait --mailbox-root "$OFFLINE_ROOT" --run-dir "$RUN_FS_A" \
  --address "$ADDR_FS_A" --tag "$TOKEN2" --box inbox --expect-absent --timeout 180 \
  > "$CASE_EVIDENCE/a-inbox-cleared.json"
pixi run python "$LAB" offline-observe --mailbox-root "$OFFLINE_ROOT" --run-dir "$RUN_FS_B" \
  --address "$ADDR_FS_B" > "$CASE_EVIDENCE/b-observe-final.json"
pixi run python "$LAB" offline-observe --mailbox-root "$OFFLINE_ROOT" --run-dir "$RUN_FS_A" \
  --address "$ADDR_FS_A" > "$CASE_EVIDENCE/a-observe-final.json"
```

- **Cross-check and proof.**

```bash
pixi run python "$LAB" capture-transcript --run-dir "$RUN_FS_A" --output "$CASE_EVIDENCE/transcript-a" \
  > "$CASE_EVIDENCE/capture-a.json"
pixi run python "$LAB" capture-transcript --run-dir "$RUN_FS_B" --output "$CASE_EVIDENCE/transcript-b" \
  > "$CASE_EVIDENCE/capture-b.json"
pixi run python "$LAB" audit-redaction --run-dir "$RUN_FS_A" "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/redaction-audit-a.json"
pixi run python "$LAB" audit-redaction --run-dir "$RUN_FS_B" "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/redaction-audit-b.json"
pixi run python "$LAB" stop --run-dir "$RUN_FS_A" --run-dir "$RUN_FS_B" --evidence-root "$EVIDENCE" \
  > "$CASE_EVIDENCE/stop.json"
```

## Expected Outcome

- **Quantified checks:**
  - `negative-unconfigured-notifier.json` and `negative-compact-policy.json` both return explicit failures (`ok == false`).
  - `doctor.json` confirms both agents healthy, `agent.reasoning_effort == "xhigh"`, and both `offline` mailbox bindings `registered == true`.
  - `b-list-after-peek.json` still marks the operator-posted message `read == false` after `mail peek` (`peek` non-mutation).
  - After `agent-b` wakes and processes the operator message, `b-inbox-cleared-op.json` shows `0` matching Inbox items, `b-observe-after-op.json` shows the original archived and every affected SQLite thread summary row at `unread_count == 0`, and `b-notifier-status-op.json` records `last_notification_at_utc` later than enablement.
  - For `TOKEN2`, `a-observe-final.json` and `b-observe-final.json` show zero matching Inbox entries and exactly one reply from `$ADDR_FS_B` to `$ADDR_FS_A`. Match the reply's `thread_id` to rows from each recipient's `mailbox.sqlite` and check `unread_count == 0`.
  - Both redaction audits pass (`leak_count == 0`) and `stop.json` records both profiles parked.
- **Qualitative checks:**
  - Inspect the delivered reply body in `a-observe-final.json` and the captured transcripts (`transcript-a/`, `transcript-b/`) to confirm `agent-a` and `agent-b` used the gateway mailbox API via `houmao-process-emails-via-gateway` (not raw edits inside `$OFFLINE_ROOT`), `agent-b` reported `indigo-91` accurately from `beacon.txt`, and `agent-a` archived the reply cleanly without sending an unnecessary follow-up.

## Gotchas

- Both agents must receive `--mailbox-root "$OFFLINE_ROOT"` so `HOUMAO_GLOBAL_MAILBOX_DIR` resolves to the same run-local filesystem store. The worker profiles and tmux sockets remain separate.
- Because `xhigh` thinking plus a 15-second notifier poll interval can take 60-150 seconds per hop, always rely on `offline-wait` timeouts rather than fixed sleeps.

## Blinding and Transcript Checks

- Keep `eval`, `test`, `judge`, `rubric`, `benchmark`, `candidate`, and `arena` out of email subjects, bodies, notifier appendices, and workspace files.
- Verify mail state from `offline-observe` (filesystem projection + SQLite thread summaries) and captured transcripts rather than assistant summaries.
