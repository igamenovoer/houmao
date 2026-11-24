# Iteration 3 R12: Two-Agent Mail on the Shared Houmao tmux Server

Date: 2026-11-24. Status: completed. Both agents ran on the shared `houmao-default` tmux server, cross-agent `mail resolve-live` worked, and a full mail round completed in both directions. Kimi sent one unintended duplicate because the default `mail send` output omitted the message details.

Previous run: [R11 Kimi config-backed effort](2026-11-24-iter3-two-agent-mail-r11-kimi-config-effort.md).

## Update Basis

- `houmao-mgr 3.0.0rc6`
- Issue [#95](https://github.com/igamenovoer/houmao/issues/95) is closed.
- Commit `e0a3e823` adds `--tmux-server {user-default|houmao-default|new|socket}` to agent launches and launch profiles.
- Commit `e7e536f1` uses native Kimi `config.toml` for managed launches.
- The fixture now defaults local managed runs to `--tmux-server houmao-default` and records `tmux_server_mode` in `run.json`.

## Clean Start

R11 notifiers were disabled and both R11 agents were stopped through their agent IDs. Ports `32995` and `43439` were free afterward. R12 uses a fresh root:

```text
tmp/houmao-30-iter3-mailbox-r12/
```

The shared mailbox was initialized before launch. Both runs were prepared with the updated fixture and explicit `--tmux-server houmao-default`.

## Shared Tmux Server

Both agents resolved to the same shared Houmao server socket:

```text
/tmp/houmao-tmux-1001/8d7bee5d0672038af413d92d/default.sock
```

The owner record is stored under:

```text
tmp/houmao-30-iter3-mailbox-r12/registry/tmux-default-8d7bee5d0672038af413d92da449ef873e87d3038abb9e1d8c3eb4fe0ee7f235/record.json
```

Manifests:

| Client | Session | Socket |
| --- | --- | --- |
| DSH | `HOUMAO-dsh-mailer-r12-1795499839302` | `/tmp/houmao-tmux-1001/8d7bee5d0672038af413d92d/default.sock` |
| Kimi | `HOUMAO-kimi-mailer-r12-1795499845784` | `/tmp/houmao-tmux-1001/8d7bee5d0672038af413d92d/default.sock` |

This is the direct retest of issue #95: the two agents now share one tmux server, so the cross-socket probe no longer hits a per-run shim.

## Kimi Native Configuration

The updated fixture writes Kimi `config.toml` directly. The runtime home contains:

```toml
default_model = "Qwen/Qwen3.8-27B-FP8"

[models."Qwen/Qwen3.8-27B-FP8"]
provider = "api-compatible"
model = "Qwen/Qwen3.8-27B-FP8"
max_context_size = 262144
capabilities = [ "tool_use", "thinking" ]
support_efforts = [ "low", "medium", "high", "xhigh" ]
default_effort = "xhigh"

[thinking]
enabled = true
effort = "xhigh"
```

`/api/v1/config` reports the same alias, `supportEfforts`, `defaultEffort`, and `thinking.effort: "xhigh"`. The Kimi launch environment no longer exports `KIMI_MODEL_*`.

DSH materialized patch still contains `"reasoning": "xhigh"`.

## Cross-Agent Peek

From the shared roots, with no fixture shim on `PATH`:

```bash
houmao-mgr --print-json agents single \
  --agent-id 46298882-51f4-4f23-b3eb-6b76fab991de mail resolve-live
```

returned:

```json
{
  "canonical_mail_identity": {
    "address": "dsh-mailer-r12@houmao.localhost",
    "channel": "offline"
  },
  "gateway": {
    "base_url": "http://127.0.0.1:39377",
    "port": 39377
  }
}
```

The `agents global list` roster also showed both agents as available.

## Agent Identities

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `46298882-51f4-4f23-b3eb-6b76fab991de` | `eaf21075-1c87-46f9-8d1f-1ad8fbaec925` |
| Name | `dsh-mailer-r12` | `kimi-mailer-r12` |
| Address | `dsh-mailer-r12@houmao.localhost` | `kimi-mailer-r12@houmao.localhost` |
| Offline binding | `reg-985c9f04626a427093706a33b67b9b44` | `reg-1064300102a8497fa71befa21e0cb2d4` |
| Gateway | `http://127.0.0.1:39377` | `http://127.0.0.1:32817` |
| Native origin | `http://127.0.0.1:33861` | `http://127.0.0.1:34795` |
| Runtime session | `dsh_web-20261124-055719Z-ae5efee2` | `kimi_web-20261124-055725Z-b0055c25` |

Both gateways return HTTP 200 at `/` and HTTP 302 at `/v1/web/enter`.

Ticketless entrances:

```text
http://127.0.0.1:39377/v1/web/enter
http://127.0.0.1:32817/v1/web/enter
```

Manifest-based helpers, mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r12/attach-dsh-mailer-r12.sh
tmp/houmao-30-iter3-mailbox-r12/attach-kimi-mailer-r12.sh
tmp/houmao-30-iter3-mailbox-r12/login-dsh-mailer-r12.sh
tmp/houmao-30-iter3-mailbox-r12/login-kimi-mailer-r12.sh
```

Both attach helpers resolve to the shared socket above, with different session names.

## Mail Round

Prompt sent to Kimi through the gateway:

```text
Use the houmao mail workflow to send a short test message to
dsh-mailer-r12@houmao.localhost. Subject: R12 hello. Body: Please reply
with MAIL-OK and archive this message. Then report whether the mail was
sent and what the peer gateway returned. Do not manipulate the peer's
tmux or process.
```

Timeline:

| UTC | Event |
| --- | --- |
| 05:58:37 | Kimi sends the first `R12 hello`, gateway returns `status: verified` |
| 05:58:39 | Kimi sends an identical second `R12 hello` to obtain JSON details |
| 05:58:57 | DSH notifier fires and DSH starts its mail-processing turn |
| 05:59:36 | DSH replies `MAIL-OK` on the second thread |
| 05:59:37 | DSH replies `MAIL-OK` on the first thread |
| 05:59:38 | Kimi notifier fires and Kimi processes the replies |
| 05:59:58 | Kimi turn completes; both replies archived |

Final mailbox state:

```text
kimi-mailer-r12: inbox=0 archive=2 sent=2
dsh-mailer-r12: inbox=0 archive=2 sent=2
```

The two replies are threaded correctly, one to each original message. Both agents archived their processed messages. Both notifiers show `last_error: null`.

## Duplicate Send Observation

Kimi disclosed the duplicate in its own report. The cause is the default `mail send` output shape:

- The first command, `houmao-mgr agents self mail send ...`, returned a human table with `status verified` but rendered the message as `message {...}`.
- Kimi could not see the message reference or confirm the full delivery record, so it re-ran the same send with `--print-json`.
- The second command returned the full message object and created a second identical message.

The gateway did not duplicate anything. The agent issued two separate send commands because the first response was not machine-actionable. The mail skill's send page shows the command without `--print-json`, so an agent following the page can hit the same ambiguity.

This is a UX/agent-contract finding, not a mail transport failure. Filed as [issue #96](https://github.com/igamenovoer/houmao/issues/96): make `mail send` return a compact write-status receipt instead of the sent message record, and leave message retrieval to a separate read-only command.

**Follow-up:** Issue #96 is closed by commit `151d0891`. [R13](2026-11-24-iter3-mail-r13-compact-receipts.md) verifies the compact receipt on `3.0.0rc6+g151d0891`: Kimi sends once, reads the top-level `message_ref`, uses a read-only peek for details, and does not resend.

## Conclusion

- Issue #95 is fixed for this path: the shared `houmao-default` server lets Kimi resolve DSH's live mailbox binding.
- The full two-way mail round passes, including notifier wake-up, read, reply, and archive.
- The new duplicate-send behavior is disclosed and documented.
- No product or fixture code changed in this run.
