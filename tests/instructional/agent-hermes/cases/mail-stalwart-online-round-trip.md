# Stalwart Online Mail Round Trip and Dual-Channel Isolation

Two managed Hermes agents (`agent-a` in `service` mode and `agent-b` in `tui` mode) attach run-owned accounts provisioned on an already-running Stalwart JMAP service. The scenario verifies provider-side delivery waking a Hermes agent via the `online` notifier, threaded RFC `In-Reply-To`/`References` reply and archive, a two-agent online round trip without reply loops, independent coexistence of `offline` and `online` notifier channels on the same Hermes agent, and verified deprovisioning of run-owned principals during cleanup.

## Sub-cases

- `o1-provider-send-and-online-wake`: an external JMAP send from account A arrives in account B's Stalwart Inbox; `agent-b`'s `online` notifier wakes `agent-b` (`hermes_tui`), which replies in thread and archives the original.
- `o2-two-agent-stalwart-round-trip`: `agent-a` (`hermes_service`) sends a workspace-backed JMAP email to `agent-b`; `agent-b` wakes, reads its workspace file, replies in thread, and archives; `agent-a`'s `online` notifier wakes on the reply and archives it without starting a reply loop.
- `o3-dual-channel-isolation`: enabling, reconfiguring, or disabling the `online` notifier on `agent-a` preserves `agent-a`'s independent `offline` notifier configuration and appendix untouched (and vice versa).
- `o4-deprovision-and-unmet-precondition-bar`: cleanup deletes only the two run-owned Stalwart principals and verifies their absence while leaving the shared Stalwart service and domain untouched; if no live Stalwart service or `0600` `service.json` is configured, stop cleanly and record `VERIFIED-UNREACHABLE` without mocking Stalwart.

## How to get to it (user POV)

- The operator supplies an owner-private (`0600`) `$RUN_TMP/runtime/mail/service.json` (plus `admin.json`) pointing to a running Stalwart JMAP server (default `http://127.0.0.1:10080/.well-known/jmap`, plus `trusted_jmap_origins` when an alternate origin is advertised).
- The operator provisions two uniquely prefixed accounts with `hermes_lab.py stalwart-provision`, attaches them with `stalwart-attach`, runs `doctor`, drives provider-side and two-agent JMAP round trips, checks `offline`/`online` channel isolation, and tears down with `hermes_lab.py stop --mail-config "$MAIL_CONFIG"`.

## Driving it with hermes_lab

Preconditions:

- Live Stalwart deployment reachable at the configured `jmap_url`. Set `STALWART_SERVICE_CONFIG` to an explicit owner-private service configuration, or supply `$RUN_TMP/runtime/mail/service.json` and `admin.json` with mode `0600`. If this prerequisite is unavailable, report `VERIFIED-UNREACHABLE`.
- `fixture.py check --pool-slot a --mode service --surface manager --live` and `--pool-slot b --mode tui --surface manager --live` both exit `0`.
- `CASE_EVIDENCE="$EVIDENCE/mail-stalwart-online-round-trip"` exists (`mkdir -p "$CASE_EVIDENCE"`).

- **Provision run-owned Stalwart accounts (`o1`, `o4`).**

```bash
export MAIL_PREFIX="houmao-hermes-$(date -u +%Y%m%dt%H%M%Sz)-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
export MAIL_CONFIG="$RUN_TMP/runtime/mail/mail-config.json"
export STALWART_DOMAIN="${STALWART_DOMAIN:-houmao-jmap.example.com}"

pixi run python "$LAB" stalwart-provision \
  --mail-config "${STALWART_SERVICE_CONFIG:-$RUN_TMP/runtime/mail/service.json}" \
  --accounts-dir "$RUN_TMP/runtime/mail/accounts" \
  --output-config "$MAIL_CONFIG" \
  --domain "$STALWART_DOMAIN" \
  --prefix "$MAIL_PREFIX" \
  > "$CASE_EVIDENCE/provision.json"

export ONLINE_ADDR_A="$(jq -er '.accounts.a.address' "$CASE_EVIDENCE/provision.json")"
export ONLINE_ADDR_B="$(jq -er '.accounts.b.address' "$CASE_EVIDENCE/provision.json")"
```

- **Prepare and launch `agent-a` (`service`) and `agent-b` (`tui`), attach Stalwart online accounts plus an `offline` channel on `agent-a` (`o1`, `o3`).**

```bash
pixi run python "$FIXTURE" prepare \
  --pool-slot a --mode service --surface manager \
  --prompt-mode unattended --tmux-server new --reasoning-level 5 \
  --role hermes-jmap-a --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-jmap-a" > "$CASE_EVIDENCE/a-prepare.json"
export RUN_JMAP_A="$(jq -er '.run_dir' "$CASE_EVIDENCE/a-prepare.json")"

pixi run python "$FIXTURE" prepare \
  --pool-slot b --mode tui --surface manager \
  --prompt-mode unattended --tmux-server new --reasoning-level 5 \
  --role hermes-jmap-b --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-jmap-b" > "$CASE_EVIDENCE/b-prepare.json"
export RUN_JMAP_B="$(jq -er '.run_dir' "$CASE_EVIDENCE/b-prepare.json")"

pixi run python "$FIXTURE" launch --run-dir "$RUN_JMAP_A" > "$CASE_EVIDENCE/a-launch.json"
pixi run python "$FIXTURE" launch --run-dir "$RUN_JMAP_B" > "$CASE_EVIDENCE/b-launch.json"
printf 'station-code=amber-44\n' > "$RUN_JMAP_B/workdir/station.txt"

export DUAL_OFFLINE_ROOT="$RUN_TMP/runtime/mailbox-dual"
pixi run python "$LAB" offline-setup \
  --mailbox-root "$DUAL_OFFLINE_ROOT" \
  --binding "$RUN_JMAP_A=dual-a-${MAIL_PREFIX}@houmao.localhost" \
  > "$CASE_EVIDENCE/a-offline-setup.json"

pixi run python "$LAB" stalwart-attach --mail-config "$MAIL_CONFIG" --run-dir "$RUN_JMAP_A" \
  --role a --mailbox-root "$DUAL_OFFLINE_ROOT" > "$CASE_EVIDENCE/a-online-attach.json"
pixi run python "$LAB" stalwart-attach --mail-config "$MAIL_CONFIG" --run-dir "$RUN_JMAP_B" \
  --role b > "$CASE_EVIDENCE/b-online-attach.json"

pixi run python "$LAB" doctor --run-dir "$RUN_JMAP_A" --run-dir "$RUN_JMAP_B" \
  --expected-effort xhigh --mailbox-root "$DUAL_OFFLINE_ROOT" --mail-config "$MAIL_CONFIG" \
  > "$CASE_EVIDENCE/doctor.json"
```

- **External JMAP send and online notifier wake (`o1`).**

```bash
export TAG1="jetty-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
pixi run python "$LAB" notifier --run-dir "$RUN_JMAP_B" --channel online --action enable \
  --interval-seconds 20 --mode unread_only \
  --appendix-text "Use the signed houmao-mgr agents self mail commands for this online inbox round. Pass --channel online and the supplied expected binding ID. Read the message, reply once with the requested result, and archive the message after the reply is accepted." \
  > "$CASE_EVIDENCE/b-notifier-enabled.json"

pixi run python "$LAB" stalwart-peer-send --mail-config "$MAIL_CONFIG" \
  --sender a --recipient b --tag "$TAG1" \
  --subject "Mailbox connection check" \
  --body "Please reply with the single word confirmed so I know this online mailbox is active." \
  > "$CASE_EVIDENCE/peer-send.json"

pixi run python "$LAB" stalwart-wait --mail-config "$MAIL_CONFIG" --role b --box inbox \
  --tag "$TAG1" --timeout 120 > "$CASE_EVIDENCE/b-inbox-before.json"
pixi run python "$LAB" stalwart-wait --mail-config "$MAIL_CONFIG" --role a --box inbox \
  --tag "$TAG1" --timeout 240 > "$CASE_EVIDENCE/a-inbox-reply.json"
pixi run python "$LAB" stalwart-wait --mail-config "$MAIL_CONFIG" --role b --box inbox --expect-absent \
  --tag "$TAG1" > "$CASE_EVIDENCE/b-inbox-after.json"
pixi run python "$LAB" stalwart-wait --mail-config "$MAIL_CONFIG" --role b --box archive \
  --tag "$TAG1" > "$CASE_EVIDENCE/b-archive.json"
```

- **Two-agent Stalwart round trip and dual-channel isolation (`o2`, `o3`).**

```bash
export TAG2="beacon-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
pixi run python "$LAB" notifier --run-dir "$RUN_JMAP_A" --channel offline --action enable \
  --interval-seconds 45 --mode any_inbox --mailbox-root "$DUAL_OFFLINE_ROOT" \
  --appendix-text "offline-sentinel-appendix" \
  > "$CASE_EVIDENCE/a-offline-notifier-before.json"

pixi run python "$LAB" notifier --run-dir "$RUN_JMAP_A" --channel online --action enable \
  --interval-seconds 20 --mode unread_only --mailbox-root "$DUAL_OFFLINE_ROOT" \
  --appendix-text "Use the signed houmao-mgr agents self mail commands with --channel online and the supplied expected binding ID. Archive replies and confirmations that contain no new request." \
  > "$CASE_EVIDENCE/a-online-notifier-enabled.json"

pixi run python "$FIXTURE" prompt --run-dir "$RUN_JMAP_A" \
  --prompt "Use your Houmao mailbox skill and the signed houmao-mgr agents self mail send command to send an online email to $ONLINE_ADDR_B with subject 'Station check $TAG2'. Ask the recipient to read station.txt and reply with the station-code value. Stop after the send succeeds." \
  > "$CASE_EVIDENCE/a-send-prompt.json"

pixi run python "$LAB" stalwart-wait --mail-config "$MAIL_CONFIG" --role b --box archive \
  --tag "$TAG2" --timeout 300 > "$CASE_EVIDENCE/b-archive-final.json"
pixi run python "$LAB" stalwart-wait --mail-config "$MAIL_CONFIG" --role a --box archive \
  --tag "$TAG2" --timeout 300 > "$CASE_EVIDENCE/a-reply-arrived.json"
pixi run python "$LAB" stalwart-wait --mail-config "$MAIL_CONFIG" --role a --box inbox \
  --tag "$TAG2" --expect-absent --timeout 180 > "$CASE_EVIDENCE/a-inbox-cleared.json"
pixi run python "$LAB" stalwart-observe --mail-config "$MAIL_CONFIG" --role a --box archive \
  --tag "$TAG2" > "$CASE_EVIDENCE/a-archive-final.json"
pixi run python "$LAB" notifier --run-dir "$RUN_JMAP_A" --channel online --action disable \
  --mailbox-root "$DUAL_OFFLINE_ROOT" > "$CASE_EVIDENCE/a-online-notifier-disabled.json"
pixi run python "$LAB" notifier --run-dir "$RUN_JMAP_A" --channel offline --action status \
  --mailbox-root "$DUAL_OFFLINE_ROOT" > "$CASE_EVIDENCE/a-offline-notifier-after.json"
```

- **Cross-check, redaction audit, and scoped cleanup (`o4`).**

```bash
pixi run python "$LAB" capture-transcript --run-dir "$RUN_JMAP_A" --output "$CASE_EVIDENCE/transcript-a" \
  > "$CASE_EVIDENCE/capture-a.json"
pixi run python "$LAB" capture-transcript --run-dir "$RUN_JMAP_B" --output "$CASE_EVIDENCE/transcript-b" \
  > "$CASE_EVIDENCE/capture-b.json"
pixi run python "$LAB" audit-redaction --run-dir "$RUN_JMAP_A" "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/redaction-audit-a.json"
pixi run python "$LAB" audit-redaction --run-dir "$RUN_JMAP_B" "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/redaction-audit-b.json"
pixi run python "$LAB" stop --run-dir "$RUN_JMAP_A" --run-dir "$RUN_JMAP_B" \
  --mail-config "$MAIL_CONFIG" --evidence-root "$EVIDENCE" \
  > "$CASE_EVIDENCE/stop.json"
```

## Expected Outcome

- **Quantified checks:**
  - `provision.json` creates two uniquely prefixed accounts; `doctor.json` exits `0` with both Stalwart JMAP accounts authenticated and both Hermes agents healthy with `agent.reasoning_effort == "xhigh"`.
  - For `TAG1`: `a-inbox-reply.json` contains `count == 1` reply from `$ONLINE_ADDR_B` with `inReplyTo` / `references` matching the original `messageId` from `peer-send.json`; `b-inbox-after.json` reports `count == 0`; `b-archive.json` reports `count == 1` with `read == true` and `archived == true`.
  - For `TAG2`: `a-archive-final.json` and `b-archive-final.json` confirm both request and reply are archived (`read == true`, `archived == true`), `a-inbox-cleared.json` confirms `count == 0`, and exactly `1` reply exists from `$ONLINE_ADDR_B` with matching `inReplyTo`/`references` (zero reply-loop duplicates).
  - Agent B's retained gateway authorization records show two `mail.reply` handoffs for the selected online binding. Each handoff identifies verified self for the current managed generation.
  - `a-offline-notifier-after.json` still reports `enabled == true`, `interval_seconds == 45`, `mode == "any_inbox"`, and `appendix_text == "offline-sentinel-appendix"` after disabling the `online` notifier.
  - Both redaction audits report `leak_count == 0`; `stop.json` records `surviving_daemon_pids == []` and `stalwart_cleanup.verified_absent == true`.
- **Qualitative checks:**
  - Inspect the delivered Stalwart replies and captured transcripts (`transcript-a/`, `transcript-b/`) to confirm `agent-b` answered `TAG1` with `confirmed` and `TAG2` with `amber-44` from `station.txt`, used the gateway mailbox API through `houmao-process-emails-via-gateway`, and `agent-a` archived the confirmation cleanly without triggering an extra reply.

## Gotchas

- A native approval wait fails this unattended case. Capture the outstanding admission and check both mailboxes before scoped cleanup.
- Never start, stop, reset, or reconfigure the shared Stalwart deployment. If the Stalwart server advertises an alternate origin (for example `http://mail.houmao.localhost:10080`), list that exact origin in `trusted_jmap_origins` inside `service.json`.
- If setup fails after `stalwart-provision` and before `stop`, run `hermes_lab.py stalwart-deprovision --mail-config "$MAIL_CONFIG"` to remove the run-owned principals.

## Blinding and Transcript Checks

- Keep `eval`, `test`, `judge`, `rubric`, `benchmark`, `candidate`, and `arena` out of email subjects, bodies, notifier appendices, and workspace files.
- Grade from Stalwart JMAP provider observations (`stalwart-observe`) and captured transcripts (`transcript-a/`, `transcript-b/`), never from assistant summaries alone.
