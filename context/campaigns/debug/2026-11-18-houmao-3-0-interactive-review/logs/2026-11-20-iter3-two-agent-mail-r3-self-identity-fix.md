# Iteration 3 R3: Two-Agent Mail on the Managed-Self Fix

Date: 2026-11-20. Status: passed on `houmao-mgr 3.0.0rc5+local.f7f4245.dirty` (commit `f7f42458 fix: resolve managed self queries from runtime manifests`). Both rounds completed, both inboxes ended empty, and the previous `agents self identity` failure did not recur.

Previous runs: [no-skill run](2026-11-20-iter3-two-agent-mail.md), [system-skill run with identity failure](2026-11-20-iter3-two-agent-mail-r2-system-skills.md). Plan: [Iteration 3](../iterations/2026-11-20-plan-3-mailbox-two-agent.md).

## Target

- Clean shared root: `tmp/houmao-30-iter3-mailbox-r3/`.
- Toolchain: uv-installed `houmao-mgr 3.0.0rc5+local.f7f4245.dirty`, editable install.
- DSH: `0.2.2-rc.3`, mode `web`, backend `dsh_web`.
- Kimi: `2.6.0` from the locally pinned npm package, mode `web`, backend `kimi_web`.
- Model: `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`.

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `d2dee5ab-7aac-4375-a15d-e847dbf4b028` | `7d3a3d7d-61f4-4afb-9856-071fb055758d` |
| Name | `dsh-mailer-r3` | `kimi-mailer-r3` |
| Address | `dsh-mailer-r3@houmao.localhost` | `kimi-mailer-r3@houmao.localhost` |
| Offline binding | `reg-243af75cbb6f4dc79e276eeb31da9515` | `reg-926ac10a7ede4f8aacb3b3ea27d3989b` |
| Gateway | `http://127.0.0.1:37605` | `http://127.0.0.1:37606` |
| Native origin | `http://127.0.0.1:39137` | `http://127.0.0.1:35237` |
| Native session | `session-c5655812-5b44-45bb-8162-259bf270b07a` | `session_2538ade5-9fdd-4df5-9507-0cb86fd50b5c` |
| Tmux session | `HOUMAO-dsh-mailer-r3-1795175931488` | `HOUMAO-kimi-mailer-r3-1795176021551` |

Both prepared runs recorded `configuration.system_skill_policy = "default"`. Their runtime home `skills/` directories contain:

```text
houmao-agent-entrypoint
houmao-agent-loop-lite
houmao-agent-loop-pro
houmao-shared-routines
```

## Environment Note

The host Kimi binary auto-updated to `2.7.2`, and the current launch policy still requires `2.6.0`:

```text
Error: Kimi Web requires Kimi Code 2.6.0. Detected '2.7.2'.
```

The rerun installed the qualified package locally:

```bash
npm install --prefix tmp/kimi-2.6.0 @moonshot-ai/kimi-code@2.6.0
tmp/kimi-2.6.0/node_modules/.bin/kimi --version   # 2.6.0
```

The Kimi fixture run was prepared against that executable. This is a test-environment pinning step, not a product change.

The exact pins are filed as [#90](https://github.com/igamenovoer/houmao/issues/90). The issue covers the Kimi ACP/Web `==2.6.0` strategies and the Codex app-server `==0.169.0` strategy, and proposes lower-bounded ranges so routine client auto-updates do not block launch.

## Identity Fix Verification

Kimi's turn loaded `houmao-agent-entrypoint`, then ran:

```bash
houmao-mgr --print-json agents self identity
```

It returned the managed identity JSON for `kimi-mailer-r3` and exited successfully. The previous failure did not appear:

```text
Current-session attach is unavailable for local tmux-backed control ...
```

DSH also ran `agents self identity` and exited `0`. Both agents then loaded `houmao-shared-routines` and used the scoped `houmao-mgr agents self mail ...` commands.

## Exchange

- `12:00:49Z` DSH sent `Mailbox wake test r3`.
- `12:00:59Z` Kimi's notifier enqueued `gwreq-20261120-120100Z-2f1d8f45`.
- `12:01:33Z` Kimi replied with `MAIL-OK. Message received and processed; archiving now.`
- `12:01:42Z` Kimi's request completed.
- `12:01:39Z` DSH's notifier enqueued `gwreq-20261120-120139Z-f3b33f78`.
- `12:01:59Z` DSH's request completed after reading and archiving the reply.
- Both inboxes are empty. DSH sent only the original message; Kimi sent only the reply. The `Re:` stop rule prevented a loop.

Notifier audit:

| Agent | Poll | Unread | Outcome |
| --- | --- | ---: | --- |
| Kimi | `12:00:59Z` | 1 | `enqueued` |
| Kimi | `12:01:20Z` | 1 | `busy_skip` |
| Kimi | `12:01:40Z` | 0 | `empty` |
| DSH | `12:00:59Z` | 0 | `empty` |
| DSH | `12:01:19Z` | 0 | `empty` |
| DSH | `12:01:39Z` | 1 | `enqueued` |
| DSH | `12:02:00Z` | 0 | `empty` |

Both gateways recorded exactly one completed `mail_notifier_prompt` for the round. `busy_skip` occurred on Kimi while it was processing; DSH's reply arrived after DSH's early empty polls and was enqueued on the next poll.

## Errors Observed

Only one minor agent-side CLI mismatch appeared:

```text
Usage: houmao-mgr agents self mail archive [OPTIONS]
Error: No such option '--box'.
Command failed with exit code: 2.
```

Kimi tried `--box` on `archive`, then corrected. DSH's turn produced no non-zero exits. This is a small CLI/skill field mismatch, not the identity-gate failure.

## Comparison

| Observation | R2 system-skill run | R3 system-skill run |
| --- | --- | --- |
| `agents self identity` | Failed with `Current-session attach is unavailable` | Returned managed identity JSON, exit `0` |
| Kimi turn duration | About 3 minutes, including source and tmux investigation | About 43 seconds |
| Mail path | `houmao-mgr agents self mail ...` after detour | `houmao-mgr agents self mail ...` directly |
| Reply loop | Prevented by `Re:` stop rule | Prevented by `Re:` stop rule |
| Inboxes after round | Empty | Empty |

The managed-self fix removes the R2 detour. The system-skill path now exercises the intended CLI and completes the mailbox round without schema guessing.

## Final State

On 2026-11-23, both notifiers were disabled and both agents stopped successfully before the R4 rerun. Their isolated tmux servers were absent, and direct TCP checks confirmed that ports `37605` and `37606` no longer accepted connections. The host lacks `ss`, so the checks used Python socket `connect_ex`, which returned `111` (`ECONNREFUSED`) for both ports. This completes R3 teardown.

Watch helpers:

```text
tmp/houmao-30-iter3-mailbox-r3/attach-dsh-mailer-r3.sh
tmp/houmao-30-iter3-mailbox-r3/attach-kimi-mailer-r3.sh
tmp/houmao-30-iter3-mailbox-r3/login-dsh-mailer-r3.sh
tmp/houmao-30-iter3-mailbox-r3/login-kimi-mailer-r3.sh
```

## Next

- Decide whether the `mail archive --box` mismatch warrants a skill or CLI-documentation fix.
- R4 on 2026-11-23 superseded the local Kimi `2.6.0` workaround: host Kimi `2.7.2` launched under the new `>=2.6.0` policy and completed the same mail round. See the [R4 version-floor rerun](2026-11-23-iter3-two-agent-mail-r4-version-floor.md).
