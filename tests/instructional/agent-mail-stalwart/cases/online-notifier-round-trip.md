# Real Email Wake, Reply, and Archive

An operator gives a managed agent a real mailbox address. A second account sends a message to that address; the gateway mail-notifier wakes the agent, the agent reads the message, replies, and archives it, and the sender's account receives the reply. The proof is the provider mailbox state plus the agent's own session transcript.

## Sub-cases

- `n1-external-delivery`: a message sent from the peer account appears in the managed agent's provider inbox with the run tag.
- `n2-notifier-wake`: the online notifier advances and the agent's transcript shows the mailbox read, reply, and archive actions.
- `n3-reply-visible`: the peer account receives exactly one reply in the same thread, and the original message is archived in the agent's inbox.

## How to get to it (user POV)

- The operator has two normal mail accounts on the selected Stalwart service, already provisioned by `mail_lab.py provision`.
- Both agents are launched and both online bindings are attached; `doctor` exits zero.
- The operator enables the recipient's online mail-notifier and sends one message from the peer account.
- The recipient agent's normal turn handles the message through the Houmao mailbox skill; the operator observes provider state and the transcript rather than asking the agent to report on itself.

## Driving it with mail_lab

Preconditions:

- `doctor` exits zero for the run handle and the selected mail config.
- Both agents are idle, and both notifiers were disabled before this case.

- **Disable both notifiers.** Reset the case to a known state. Run `mail_lab.py notifier --run-meta "$RUN_META" --role a --action disable` and the same with `--role b`. Both commands report a disabled notifier for `channel=online`.
- **Enable the recipient notifier.** Run:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" notifier \
  --run-meta "$RUN_META" --role b --action enable \
  --interval-seconds 20 --mode unread_only \
  --appendix-text "New mail is waiting in the online inbox. Read the message, reply to it with the requested result, and archive it after the reply is accepted. Do not reply to a repeat reminder for the same message." \
  > "$EVIDENCE/online-notifier-round-trip/notifier-enabled.json"
```

  The status reports `mode=unread_only`, a 20-second interval, and the appendix text.

- **Send from the peer account.** Use the real provider, not the agent under test:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" peer-send \
  --run-meta "$RUN_META" --sender a --recipient b \
  --subject "Mailbox connection check" \
  --body "Please reply with the single word confirmed so I know this mailbox is active." \
  > "$EVIDENCE/online-notifier-round-trip/peer-send.json"
```

  The receipt shows the run-tagged subject and recipient. Save the returned provider message ID.

- **Wait for provider delivery.** Run `mail_lab.py wait --run-meta "$RUN_META" --role b --timeout 120` and save the output as `b-inbox-before.json`. It exits zero only when a tagged message is present in the recipient's inbox. Its metadata shows `read=false`, `archived=false`, and `box=inbox`.
- **Wait for the agent reply.** Run `mail_lab.py wait --run-meta "$RUN_META" --role a --timeout 240` and save the output as `a-inbox-reply.json`. The reply carries `Re:` plus the run-tagged subject and references the original RFC Message-ID in `inReplyTo` and `references`.
- **Read the reply body.** Run `REPLY_ID="$(jq -r '.messages[0].id' "$EVIDENCE/online-notifier-round-trip/a-inbox-reply.json")"` followed by `mail_lab.py content --run-meta "$RUN_META" --role a --email-id "$REPLY_ID"`, saving the output as `a-reply-content.json`. The body contains the requested confirmation.
- **Cross-check the recipient inbox.** Run `mail_lab.py observe --run-meta "$RUN_META" --role b` and save it as `b-inbox-after.json`. The original message leaves the unarchived inbox. Run `mail_lab.py observe --run-meta "$RUN_META" --role b --box archive` and save `b-archive.json` with the original provider ID and `read=true`, `archived=true`.
- **Capture the notifier advance.** Run `mail_lab.py notifier --run-meta "$RUN_META" --role b --action status` and save it as `b-notifier-status.json`. `last_notification_at_utc` is later than the enable step. `open_count` may be reported as unavailable; use the timestamp and the inbox cross-check instead.
- **Capture the transcript.** Run:

```bash
pixi run python "$BUNDLE_ROOT/helpers/mail_lab.py" transcript \
  --run-meta "$RUN_META" --role b \
  --output "$EVIDENCE/online-notifier-round-trip/b"
```

  The helper copies the recipient's native journal under that directory. The transcript shows the mailbox read, reply, and archive calls for the selected message.

- **Proof.** The pass requires all of: one tagged provider message in `b-inbox-before.json`; one reply in `a-inbox-reply.json` with a matching thread; no unarchived inbox copy in `b-inbox-after.json` plus the matching provider Archive record; a notifier timestamp advance; and the transcript actions. Save the artifacts under `$EVIDENCE/online-notifier-round-trip/` and confirm they exist after cleanup.

## Gotchas

- `unread_only` only fires for unread unarchived inbox mail. If the agent reads the message before the notifier polls, no later reminder is expected; do not turn that into a false failure.
- The notifier interval plus a model turn can exceed two minutes. Use `wait` deadlines, not a fixed sleep.
- The helper prefixes the subject with the run tag. Keep the tag in every observed subject; do not match on the untagged text alone.
- A repeat reminder can produce a second reply. The case expects exactly one reply to the original message; if the agent replies again, count it and report the behavior rather than hiding it.
- A missing Archive role causes a readiness error during attachment. Ask the provider owner to repair a separately managed account before running this case.

## Blinding and Transcript Checks

- Keep `eval`, `test`, `judge`, `rubric`, `benchmark`, and `candidate` out of the mail body and notifier appendix. The notifier text is ordinary operator guidance.
- Grade from the recipient's native Web transcript and provider mailbox state. Use the agent's final summary only for context.
- The correspondent role is a general work role. Do not replace it with an acknowledgement-only prompt for this case.
