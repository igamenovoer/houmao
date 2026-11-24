# Iteration 3 R13: Compact Mail Receipts Prevent Duplicate Sends

Date: 2026-11-24. Status: completed. Houmao `3.0.0rc6+g151d0891` returns a compact write receipt for `mail send`. Kimi sent exactly one message, confirmed it with a read-only peek, and did not resend. The full two-way mail round completed with one message in each direction.

Previous run: [R12 default tmux mail round](2026-11-24-iter3-mail-r12-default-tmux-mail-round.md).

## Update Basis

- `houmao-mgr 3.0.0rc6+g151d0891`
- Commit `151d0891 fix: return compact receipts for manager writes`, which says it fixes issue [#96](https://github.com/igamenovoer/houmao/issues/96).
- Issue #96 is closed.
- The mail send receipt now exposes `status`, `operation`, `authoritative`, `message_ref`, `sender_address`, `to`, `subject`, `created_at_utc`, `binding_id`, `channel`, `transport`, and `execution_path` at the top level. It no longer returns the full sent-message object.

## Clean Start

R12 notifiers were disabled and both R12 agents were stopped through their agent IDs. Ports `39377` and `32817` were free afterward. R13 uses a fresh root:

```text
tmp/houmao-30-iter3-mailbox-r13/
```

The shared mailbox was initialized before launch. Both runs were prepared with the updated fixture and `--tmux-server houmao-default`.

## Shared Server and Identities

Both agents share the Houmao server socket:

```text
/tmp/houmao-tmux-1001/8d7bee5d0672038af413d92d/default.sock
```

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `b3b721ef-c73e-454e-9ce8-932765ede74e` | `984c48fd-3242-4dea-98f3-fbd858316183` |
| Name | `dsh-mailer-r13` | `kimi-mailer-r13` |
| Address | `dsh-mailer-r13@houmao.localhost` | `kimi-mailer-r13@houmao.localhost` |
| Offline binding | `reg-1d7b07a257f04f54b3f180085762f148` | `reg-c5af2391e9834f43a35547fb1f793def` |
| Gateway | `http://127.0.0.1:33295` | `http://127.0.0.1:41131` |
| Native origin | `http://127.0.0.1:45755` | `http://127.0.0.1:33219` |
| Tmux session | `HOUMAO-dsh-mailer-r13-1795501795689` | `HOUMAO-kimi-mailer-r13-1795501802578` |
| Runtime session | `dsh_web-20261124-062955Z-dcfb1c3b` | `kimi_web-20261124-063002Z-a8cc0e76` |

Kimi `/api/v1/config` still reports `Qwen/Qwen3.8-27B-FP8` with `supportEfforts: [low, medium, high, xhigh]`, `defaultEffort: xhigh`, and `thinking.effort: xhigh`. DSH materialized patch still contains `"reasoning": "xhigh"`.

## Mail Send Receipt

Kimi ran the send once, with JSON output from the start:

```bash
houmao-mgr --print-json agents self mail send \
  --channel offline \
  --expected-binding-id reg-c5af2391e9834f43a35547fb1f793def \
  --to "dsh-mailer-r13@houmao.localhost" \
  --subject "R13 hello" \
  --body-content "Please reply with MAIL-OK and archive this message."
```

The receipt:

```json
{
  "schema_version": 1,
  "operation": "send",
  "status": "verified",
  "authoritative": true,
  "execution_path": "gateway_backed",
  "transport": "filesystem",
  "principal_id": "984c48fd-3242-4dea-98f3-fbd858316183",
  "address": "kimi-mailer-r13@houmao.localhost",
  "sender_address": "kimi-mailer-r13@houmao.localhost",
  "binding_id": "reg-c5af2391e9834f43a35547fb1f793def",
  "channel": "offline",
  "created_at_utc": "2026-11-24T06:30:51Z",
  "message_ref": "houmao-mail:...",
  "subject": "R13 hello",
  "to": ["dsh-mailer-r13@houmao.localhost"],
  "cc": []
}
```

There is no nested `message` object and no `{...}` placeholder. The receipt is sufficient to verify the write and to carry the opaque `message_ref`.

## Agent Behavior

Kimi did not resend. Its own report says it used the receipt to verify the send, then confirmed the stored message with a read-only peek on its own binding:

> “turned `status: verified` with `authoritative: true` via the gateway-backed path. I'll confirm the sent message's content with a read-only peek on my own binding.”

The wire log contains exactly one `mail send` call. The follow-up was a read-only `mail peek`, not a second write. This is the behavior issue #96 proposed.

## Round Timeline

| UTC | Event |
| --- | --- |
| 06:30:51 | Kimi sends `R13 hello`; receipt `status: verified`, `authoritative: true` |
| 06:31:03 | DSH notifier fires; DSH starts its mail turn |
| 06:31:38 | DSH replies `MAIL-OK` on the same thread |
| 06:31:44 | Kimi notifier fires; Kimi starts its processing turn |
| 06:31:51 | Kimi reads and archives the reply |

Final mailbox state:

```text
kimi-mailer-r13: inbox=0 archive=1 sent=1
dsh-mailer-r13: inbox=0 archive=1 sent=1
```

Exactly one message each way, one reply, both archived. No duplicate.

## Entrances and Watch Scripts

Ticketless entrances:

```text
http://127.0.0.1:33295/v1/web/enter
http://127.0.0.1:41131/v1/web/enter
```

Manifest-based helpers, mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r13/attach-dsh-mailer-r13.sh
tmp/houmao-30-iter3-mailbox-r13/attach-kimi-mailer-r13.sh
tmp/houmao-30-iter3-mailbox-r13/login-dsh-mailer-r13.sh
tmp/houmao-30-iter3-mailbox-r13/login-kimi-mailer-r13.sh
```

Both attach helpers resolve to the shared socket above with different session names.

## Manual Follow-Up Test

After the controlled hello round, the operator ran two manual prompts in the Kimi Web UI.

### Manual Prompt 1: S2 Paper Search

Operator prompt:

```text
ask dsh agent to find the latest rsi paper using s2, report back
```

Kimi sent the task mail at `06:34:06Z`:

```text
Task: find latest RSI paper via Semantic Scholar
```

DSH's notifier started turn 2 at `06:34:25Z`. DSH queried the Semantic Scholar Graph API without a key and received repeated HTTP `429` responses, including the bulk search endpoint. The operator then prompted DSH directly twice with:

```text
use the s2 key in bashrc
```

DSH turn 3 found `S2_API_KEY` in `~/.bashrc` and retried with the `x-api-key` header. The key was accepted, but CloudFront still returned HTTP `429` for the IP. DSH turns 2 and 3 both ended with `aborted` by the operator. The S2 failures are an external service rate-limit condition, not a Houmao error.

### Manual Prompt 2: Switch to Tavily

Operator prompt:

```text
tell the other agent to directly use tavily cli for paper search, no s2
```

Kimi first tried `mail reply` on its own task message. Because a reply routes to the parent message's sender, the amendment landed in Kimi's own inbox at `06:40:54Z`, not DSH's. Kimi peeked, detected the self-addressed reply, archived it, and sent a correctly addressed new message at `06:41:08Z`:

```text
Task amendment: use Tavily CLI, not S2
```

DSH's turn 4 started from the amendment. DSH found that `tavily-cli` was not installed, installed `tavily-cli@0.1.2` globally through npm, found the existing key in `~/.tavily/config.json`, configured the CLI with `tavily-cli auth set`, and ran the search. It cross-checked the results against arXiv submission dates. One arXiv request used `http` and hit a `301` plus an XML parse error; DSH retried with `https` and `curl -L` and completed the lookup.

DSH replied at `06:43:13Z` with four papers:

1. DriveDreamer-RSI, arXiv:2611.30671, submitted 2026-11-23.
2. Blind to What They Can Fix, arXiv:2611.29807, submitted 2026-11-22.
3. SELFWRITE / Recursive Self-Editing, arXiv:2611.29513, submitted 2026-11-22.
4. MM-DataLoop, arXiv:2611.29254, submitted 2026-11-22.

DSH marked the original S2 task answered and archived both task messages. Kimi received the report at `06:43:13Z` in its turn 4, read it, archived it, and stopped.

### Manual Test Observations

- `mail reply` routes to the parent message's sender. When Kimi replied to its own task mail, the amendment went to Kimi itself. Kimi detected and corrected it, but the skill could warn that an amendment to an agent-authored task must use `send` to the peer, not `reply`.
- DSH installed a global npm package (`tavily-cli@0.1.2`) and wrote Tavily CLI auth state during the task. This is a host-level side effect of `danger-full-access`; the campaign should note it for cleanup or isolation.
- The S2 `429` condition persisted with a valid key. It is external to Houmao and should not be treated as a product failure.
- DSH had two minor tool-call argument errors (`missing required property "description"`) and one arXiv `301`/XML parse error. It recovered without operator help.
- A second DSH session, `session-ffde2070-390a-4365-b848-6d0174a892b9`, was created at `06:34:21Z` but contains no turns. It appears to be an unused manual session and did not affect the task.

## Final Disposition

Test complete at `2026-11-24T06:44Z`. M1 and M2 passed on the shared `houmao-default` server with exactly one message in each direction and no duplicate delivery. Both notifiers woke their target once, both agents read, replied or confirmed, and archived. Kimi used the compact send receipt and a read-only peek instead of resending. The manual follow-up tests also completed: S2 was blocked by external HTTP 429s, the Tavily redirect produced a four-paper report, and Kimi archived it. Both R13 agents remain running for inspection; M4 teardown is pending.
