# Iteration 3 Rerun: Two-Agent Mail With Default Agent System Skills

Date: 2026-11-20. Status: both rounds completed. The clean rerun installs the default `agent` system-skill pack in both runtime homes. Kimi's first notifier round hit a Web-session identity-gate failure and spent about three minutes investigating before completing the mail round through `houmao-mgr agents self mail`. DSH then completed the terminal reply round without replying, so the stop rule prevented a loop.

Previous run: [two-agent mail without system skills](2026-11-20-iter3-two-agent-mail.md). Plan: [Iteration 3](../iterations/2026-11-20-plan-3-mailbox-two-agent.md).

## Target

- Clean shared root: `tmp/houmao-30-iter3-mailbox-r2/`.
- Toolchain: uv-installed `houmao-mgr 3.0.0rc5+local.6290f21.dirty` (editable install).
- DSH: `0.2.2-rc.3`, mode `web`, backend `dsh_web`.
- Kimi: `2.6.0`, mode `web`, backend `kimi_web`.
- Model: `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`.

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `0df3de45-3dae-48ef-af31-49b046906681` | `888d3ac8-2ba3-4b44-9504-625956f86a69` |
| Name | `dsh-mailer-r2` | `kimi-mailer-r2` |
| Address | `dsh-mailer-r2@houmao.localhost` | `kimi-mailer-r2@houmao.localhost` |
| Offline binding | `reg-1418a06f7c98465cab465d71670d6795` | `reg-e94beb1e52574442993e1f46c0d12da2` |
| Gateway | `http://127.0.0.1:37505` | `http://127.0.0.1:37506` |
| Native origin | `http://127.0.0.1:36983` | `http://127.0.0.1:45011` |
| Native session | `session-5e9fdd05-805d-40ef-8a5f-078361d5a530` | `session_8ca4529d-2b3d-40f5-af5c-a72ad9c21ed3` |
| Tmux session | `HOUMAO-dsh-mailer-r2-1795166807853` | `HOUMAO-kimi-mailer-r2-1795166814732` |

Both prepared runs recorded `configuration.system_skill_policy = "default"`. Their runtime home `skills/` directories contain:

```text
houmao-agent-entrypoint
houmao-agent-loop-lite
houmao-agent-loop-pro
houmao-shared-routines
```

## Setup

- Old `dsh-mailer` and `kimi-mailer` agents were stopped cleanly. Their isolated tmux servers and gateway ports `37405`/`37406` are gone.
- Fresh runs were prepared with the updated fixture and launched through the shared-root launcher at `tmp/houmao-30-iter3-mailbox-r2/bin/launch_shared.py`.
- Both notifiers were enabled at `20s`, `unread_only`, and reported `supported: true`.
- DSH sent `Mailbox wake test r2` at `09:27:23Z`.

## Failure Found

Kimi's notifier enqueued the wake-up at `09:27:35Z`:

```text
request_id = gwreq-20261120-092735Z-aa75d3ed
state = observing
```

The Kimi turn began and called:

```bash
houmao-mgr --print-json agents self identity
```

The command failed with:

```text
Error: Current-session attach is unavailable for local tmux-backed control because neither `HOUMAO_AGENT_DEF_DIR` nor shared-registry `runtime.agent_def_dir` is available.
Command failed with exit code: 1.
```

The managed session has `HOUMAO_AGENT_ID` and the gateway host/port in its tmux environment, but it has no `HOUMAO_AGENT_DEF_DIR`, and its shell has `TMUX` empty. The system-skill entrypoint expects `agents self` to resolve the current session through the shared registry or the agent definition directory. It could not.

Instead of falling back to the exact gateway URL already present in the notifier prompt, Kimi spent the next few minutes reading `src/houmao/execution/tmux.py`, `src/houmao/srv_ctrl/commands/agents/gateway.py`, and `src/houmao/agents/realm_controller/backends/tmux_runtime.py`, and listing `/tmp/tmux-1001/`. At `09:29:38Z` the turn was still active. By `09:30` it had moved on to reading the `houmao-agent-email-comms` skill and trying `houmao-mgr agents self mail status`.

The important distinction is that `agents self identity` failed, but the mailbox commands did not. Kimi then ran, without the manual environment exports DSH used:

```text
houmao-mgr agents self mail status
houmao-mgr agents self mail list --channel offline --expected-binding-id ... --box inbox --read-state unread --not-archived
houmao-mgr agents self mail read --channel offline --expected-binding-id ... --message-ref ...
houmao-mgr agents self mail reply --channel offline --expected-binding-id ... --message-ref ... --body-content ...
houmao-mgr agents self mail archive --channel offline --expected-binding-id ... --message-ref ...
```

Those commands succeeded. Kimi replied at `09:30:14Z` with `Received. MAIL-OK. Archiving this message now.` and archived the original. The turn completed at `09:30:45Z`. The identity-gate detour cost roughly three minutes; the actual mail round took well under a minute once the agent stopped trying to satisfy the gate.

DSH's terminal round used the same `agents self mail` surface, but DSH manually exported `TMUX`, `HOUMAO_AGENT_ID`, `HOUMAO_MANIFEST_PATH`, and `HOUMAO_AGENT_DEF_DIR` in its shell before each command. It also hit one minor CLI error, `Missing option '--message-ref'` on `mail read`, then corrected. DSH read the reply, did not reply, and archived it. Its turn completed at `09:31:22Z`.

This is a new failure exposed by the default agent system-skill pack. The previous no-skill run used direct `/v1/mail/offline/*` calls and never invoked `agents self`.

## Notifier Behavior Captured

While Kimi was busy, its notifier kept polling the same unread message and recorded `busy_skip`:

| Poll time | Unread | Outcome |
| --- | ---: | --- |
| `09:27:35Z` | 1 | `enqueued` (`gwreq-20261120-092735Z-aa75d3ed`) |
| `09:27:56Z` | 1 | `busy_skip` |
| `09:28:16Z` | 1 | `busy_skip` |
| `09:28:36Z` | 1 | `busy_skip` |
| `09:28:56Z` | 1 | `busy_skip` |
| `09:29:17Z` | 1 | `busy_skip` |
| `09:29:37Z` | 1 | `busy_skip` |
| `09:29:57Z` | 1 | `busy_skip` |

The Kimi request completed at `09:30:23Z`. DSH's notifier then showed the same pattern: one `enqueued` request `gwreq-20261120-093016Z-5c887e93` at `09:30:16Z`, two `busy_skip` rows at `09:30:36Z` and `09:30:57Z`, and an `empty` row at `09:31:17Z` after DSH archived the reply. The DSH request completed at `09:31:18Z`.

This confirms the notifier does not enqueue a second prompt while the target is busy, and the message remains eligible for a later round. Both gateways recorded exactly one completed `mail_notifier_prompt` for the round.

## Current State

- Kimi gateway: healthy, idle. Native turn completed at `09:30:45Z` with `last_outcome: completed`.
- DSH gateway: healthy, idle. Native turn completed at `09:31:22Z` with `last_outcome: completed`.
- Both inboxes are empty. DSH sent only the original message; Kimi sent only the reply. No reply loop occurred.
- Both notifiers remain enabled, but their inboxes are empty, so they are polling without eligible work.
- The `busy_skip` audit rows above remain the evidence that the notifier did not duplicate or lose the message while Kimi was busy.

Watch helpers:

```text
tmp/houmao-30-iter3-mailbox-r2/attach-dsh-mailer-r2.sh
tmp/houmao-30-iter3-mailbox-r2/attach-kimi-mailer-r2.sh
tmp/houmao-30-iter3-mailbox-r2/login-dsh-mailer-r2.sh
tmp/houmao-30-iter3-mailbox-r2/login-kimi-mailer-r2.sh
```

## Comparison With The No-Skill Run

| Observation | No-skill run | System-skill run |
| --- | --- | --- |
| Mail transport | Direct `/v1/mail/offline/*` | `houmao-mgr agents self mail ...` |
| Schema guessing | `body`/`message_ref` 422s, then corrected | No 422 schema errors on the successful CLI path |
| Reply loop | Repeating chain, stopped by disabling notifiers | Terminal `Re:` rule; DSH archived without replying |
| Main friction | Fallback API summary omitted fields | `agents self identity` gate failed and caused a long detour |
| Notifier behavior | `enqueued` only | `enqueued` plus repeated `busy_skip` while the target was busy |

The system-skill pack clearly changed the agent's chosen path: it used the maintained CLI and skill routing instead of raw curl. It also eliminated the reply/schema guessing. The new cost is the identity-gate failure in the Kimi Web session.

## Classification

- **Product bug candidate: `agents self identity` is not usable from a Kimi Web managed session.** The command fails because the session has no `HOUMAO_AGENT_DEF_DIR` and the shared registry record does not supply `runtime.agent_def_dir`. The same session can run `agents self mail status/list/read/reply/archive` successfully, so the failure is specific to the identity gate, not to mailbox access generally. Candidate fixes: make `agents self identity` resolve through the manifest path or the gateway-owned session identity, or propagate `HOUMAO_AGENT_DEF_DIR` into the managed Web session.
- **Design flaw candidate: the mailbox skill requires an identity gate the notifier does not need.** The notifier already supplies the exact gateway URL, channel, and binding. The skill's identity step adds a failure point and, in Kimi's case, sent the agent into source-code investigation instead of processing mail. Candidate fix: skip the `agents self identity` gate when the prompt already carries validated gateway context, or treat the gate as advisory.
- **Confirmed notifier behavior:** `busy_skip` works as documented and does not duplicate or lose the message.
- **Test-role fix validated:** the `Re:` stop rule ended the exchange after one reply. DSH archived without replying, and both inboxes ended empty.

## Next

- Decide whether to file the `agents self identity` Web-session failure as a product issue.
- Decide whether the mailbox skill should be changed to prefer the supplied gateway context over the identity gate.
- Disable both notifiers and tear down both agents after operator inspection.
- Keep this rerun separate from the no-skill result when judging the system-skill path; the current failure is an identity-gate defect, not a mailbox-transport failure.
