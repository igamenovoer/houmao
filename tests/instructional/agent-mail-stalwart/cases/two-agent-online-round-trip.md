# Two Agents Exchange Mail Through the Real Service

Two managed agents each own an online mailbox binding. The operator asks one agent to send a work request to the other's real address; the recipient's notifier wakes it, it replies, and the sender's notifier wakes it for the reply. The proof is the pair of provider mailboxes plus both agents' session transcripts.

## Sub-cases

- `t1-request-sent`: the sender agent composes and sends one message through its online binding to the peer address.
- `t2-peer-reply`: the recipient agent reads the request, replies in the same thread, and archives it.
- `t3-sender-receives`: the sender's notifier wakes on the reply and archives it without starting an unbounded reply loop.

## How to get to it (user POV)

- Both agents are launched with the correspondent role and have run-owned online bindings; `doctor` exits zero.
- The operator enables both online notifiers, then asks the sender in natural language to mail the peer and ask for a one-line confirmation.
- The operator observes both provider inboxes and both transcripts; the agents are not asked to grade themselves.

## Driving it with mail_lab

Preconditions:

- `doctor` exits zero for the run handle and the selected mail config.
- Both agents are idle, and both notifiers were disabled before this case.
- `TOKEN` is a short neutral word chosen for this run, for example `path-3f9a1c`.

- **Disable both notifiers.** Run `mail_lab.py notifier --run-meta "$RUN_META" --role a --action disable` and the same with `--role b`.
- **Enable both notifiers.** Run the recipient first:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" notifier \
  --run-meta "$RUN_META" --role b --action enable \
  --interval-seconds 20 --mode unread_only \
  --appendix-text "New mail is waiting in the online inbox. Read the message, reply with the requested result, and archive it after the reply is accepted. Do not reply to a repeat reminder for the same message." \
  > "$EVIDENCE/two-agent-online-round-trip/b-notifier-enabled.json"
```

  Then the sender:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" notifier \
  --run-meta "$RUN_META" --role a --action enable \
  --interval-seconds 20 --mode unread_only \
  --appendix-text "New mail is waiting in the online inbox. If the message is a confirmation or acknowledgement, archive it without replying. Otherwise handle the request, reply, and archive after the reply is accepted." \
  > "$EVIDENCE/two-agent-online-round-trip/a-notifier-enabled.json"
```

- **Ask the sender to mail the peer.** Use the live operator prompt surface; the agent decides how to use the mailbox skill:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" prompt \
  --run-meta "$RUN_META" --role a \
  --prompt "Send an email to $ADDR_B with the subject 'Mailbox path $TOKEN'. Ask the recipient to reply with the single word confirmed. After the send succeeds, stop and report the send receipt." \
  > "$EVIDENCE/two-agent-online-round-trip/a-prompt.json"
```

- **Wait for the request at the peer.** Run `mail_lab.py wait --run-meta "$RUN_META" --role b --tag "$TOKEN" --timeout 180`, saved as `b-request.json`. The message is from `$ADDR_A`, and the subject carries the token.
- **Wait for the reply at the sender.** Run `mail_lab.py wait --run-meta "$RUN_META" --role a --tag "$TOKEN" --timeout 300`, saved as `a-reply.json`. The reply is from `$ADDR_B` and starts with `Re:`.
- **Cross-check both inboxes.** Run `mail_lab.py observe --run-meta "$RUN_META" --role b --tag "$TOKEN"` and the same for `--role a`. Both unarchived inboxes are empty for this token. Repeat with `--box archive`. The peer's request and the sender's reply both have `read=true` and `archived=true`. Confirm exactly one reply and compare its `inReplyTo` and `references` to the original RFC Message-ID.
- **Capture both transcripts.** Run `transcript --role a` and `transcript --role b` into `$EVIDENCE/two-agent-online-round-trip/a/` and `.../b/`. Each transcript shows the mailbox send, read, reply, or archive calls that the corresponding agent made.
- **Proof.** Save the artifacts under `$EVIDENCE/two-agent-online-round-trip/` and confirm they exist after cleanup. A pass requires the request and reply in provider metadata, the expected archive states, and both transcripts.

## Gotchas

- The helper's default tag filter is the run tag. Agent-composed mail uses the neutral `TOKEN`, so pass `--tag "$TOKEN"` to `wait` and `observe`.
- A notifier can wake an agent before the operator's prompt turn finishes. That is normal; wait for provider state rather than assuming turn ordering.
- Do not let the notifier appendix ask for a reply to every message; a confirmation can otherwise start a reply loop between the two agents.
- If one agent replies more than once to a repeat reminder, report the count. Do not hide it by filtering the evidence.
- The run-owned accounts are empty at start. If a foreign message appears, the run is using the wrong account pair; stop and re-provision rather than driving shared mail.

## Blinding and Transcript Checks

- Keep `eval`, `test`, `judge`, `rubric`, `benchmark`, and `candidate` out of the prompt and both notifier appendices.
- Grade from both native Web transcripts and both provider mailboxes. Use the agent summaries only for context.
- Use the general correspondent role for both agents; do not reduce either one to an acknowledgement-only smoke role.
