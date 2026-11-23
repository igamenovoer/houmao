# Iteration 3 R4: Lower-Bounded Kimi and Clean Mailbox Rerun

Date: 2026-11-23. Status: passed on `houmao-mgr 3.0.0rc5+local.0d642af` for the tested DSH-to-Kimi mail and notifier round. The run also live-verified the Kimi Web side of [#90](https://github.com/igamenovoer/houmao/issues/90): host Kimi `2.7.2` launched under `supported_versions: ">=2.6.0"`. R4 teardown and browser login remain unrun.

Previous run: [managed-self fix rerun](2026-11-20-iter3-two-agent-mail-r3-self-identity-fix.md). Plan: [Iteration 3](../iterations/2026-11-20-plan-3-mailbox-two-agent.md). Implementation under test: commit `64300f7c fix: accept newer supported agent tool versions`; the installed manager reports the following documentation commit `0d642af6` because it is an editable uv installation.

## R3 Teardown

Before R4 preparation, both R3 notifiers were disabled and both R3 agents stopped successfully at `2026-11-23T04:02:10Z`. Their isolated tmux servers were absent. The host does not provide `ss`, so direct TCP checks were used instead; ports `37605` and `37606` both returned `connect_ex=111` (`ECONNREFUSED`). This completes the retained R3 teardown, not the R4 teardown.

## Target

- Clean shared root: `tmp/houmao-30-iter3-mailbox-r4/`.
- Toolchain: uv-installed `houmao-mgr 3.0.0rc5+local.0d642af` and its Python environment. No Pixi or source-checkout launcher was used for live control.
- DSH: `0.2.2-rc.3`, mode `web`, backend `dsh_web`.
- Kimi: host `/home/huangzhe/.kimi-code/bin/kimi`, version `2.7.2`, mode `web`, backend `kimi_web`.
- Model: `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`.
- Mail: one explicitly initialized offline filesystem registry and mailbox root, with unread-only notifiers at 20 seconds.

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `e1a2a511-d612-4a20-ae4d-ef5d54aff54f` | `c4beca12-29ba-40ca-bcd1-583235913bc5` |
| Name | `dsh-mailer-r4` | `kimi-mailer-r4` |
| Address | `dsh-mailer-r4@houmao.localhost` | `kimi-mailer-r4@houmao.localhost` |
| Offline binding | `reg-08d6678b49ce4fa48247766c9547b895` | `reg-9a690eee84584471aace50d7d5ff40db` |
| Gateway | `http://127.0.0.1:37605` | `http://127.0.0.1:37606` |
| Native origin | `http://127.0.0.1:45185` | `http://127.0.0.1:39551` |
| Native session | `session-6223cb5f-a0aa-410c-89f0-e717b4a8b702` | `session_dc5d27c8-cc92-4e32-938e-9dbbc84e3a30` |
| Tmux session | `HOUMAO-dsh-mailer-r4-1795406608771` | `HOUMAO-kimi-mailer-r4-1795406617001` |
| Prepared run | `runs/self-hosted-dsh-web-manager-65826f7d463a` | `runs/self-hosted-kimi-web-manager-07550408efc1` |

The Kimi manifest records `detected_tool_version: "2.7.2"` and `supported_versions: ">=2.6.0"`. No local Kimi `2.6.0` package was used. The Codex and Kimi ACP version-range changes were not exercised by this run.

## Setup Failures and Corrections

The first DSH launch failed before an agent was created. The fixture's in-process manager wrapper emitted only `Managed project operation failed: project/--project-dir`; its private diagnostic at `tmp/houmao-30-iter3-mailbox-r4/manager-error.txt` contained the actionable cause:

```text
Error: Failed to prepare mail bindings: registry /data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox-r4/registry has no offline store; initialize it with houmao-mgr mailbox init
```

This was a test-setup omission. The shared store was initialized explicitly:

```bash
houmao-mgr --print-json mailbox init \
  --mailbox-root tmp/houmao-30-iter3-mailbox-r4/mailbox \
  --registry-root tmp/houmao-30-iter3-mailbox-r4/registry
```

The command returned `status: ready` and `bootstrapped: true`. The same prepared DSH run then launched successfully, followed by Kimi. Future fresh shared-root runs must perform this initialization before the first launch.

The preparation-time `home/skills` directories were empty or absent, which was the wrong inspection location. The launched manifest's `home_selector.home_path` points to the actual runtime home. Both launched runtime homes contain `houmao-agent-entrypoint`, `houmao-agent-loop-lite`, `houmao-agent-loop-pro`, and `houmao-shared-routines` under `skills/`. Both prepared runs record `configuration.system_skill_policy = "default"`.

## Launch Verification

- Both gateways report healthy, connected, idle, and `request_admission: open`.
- Both offline mailbox bindings are registered and active with distinct addresses.
- Both notifiers reported `supported: true` before enable and `last_error: null` after the exchange.
- Both agents ran `houmao-mgr --print-json agents self identity` successfully during their notifier rounds. Kimi returned its R4 managed identity with `isError: false`; DSH's identity job settled with `exit code: 0`. The R2 `Current-session attach is unavailable` failure did not recur.
- The attach helpers resolve the tmux target from the live Houmao manifest and were checked with `--print-target`. Login helpers were generated and shell-syntax checked, but no browser login was attempted.

Watch helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r4/attach-dsh-mailer-r4.sh
tmp/houmao-30-iter3-mailbox-r4/attach-kimi-mailer-r4.sh
tmp/houmao-30-iter3-mailbox-r4/login-dsh-mailer-r4.sh
tmp/houmao-30-iter3-mailbox-r4/login-kimi-mailer-r4.sh
```

## Exchange

- `04:05:20Z`: DSH's authoritative binding sent `Mailbox wake test r4` to Kimi.
- `04:05:33Z`: Kimi's notifier enqueued `gwreq-20261123-040533Z-8d7d1a15`.
- `04:06:01Z`: Kimi sent `Re: Mailbox wake test r4` containing `MAIL-OK` and archived the original.
- `04:06:08Z`: Kimi's notifier request completed. Its observed native turn was idle by the next manager sample at `04:06:15Z`.
- `04:06:13Z`: DSH's notifier enqueued `gwreq-20261123-040613Z-254d6ee4`.
- `04:06:30Z`: DSH's notifier request completed after reading and archiving the reply without sending another message.

Notifier audit evidence:

| Agent | Poll | Unread | Active execution | Outcome |
| --- | --- | ---: | --- | --- |
| Kimi | `04:05:33Z` | 1 | idle | `enqueued` |
| Kimi | `04:05:54Z` | 1 | running | `busy_skip` |
| Kimi | `04:06:14Z` | 0 | idle | `empty` |
| DSH | `04:05:32Z` | 0 | idle | `empty` |
| DSH | `04:05:52Z` | 0 | idle | `empty` |
| DSH | `04:06:13Z` | 1 | idle | `enqueued` |
| DSH | `04:06:33Z` | 0 | idle | `empty` |

Later polls through `04:07:55Z` stayed empty. Each gateway's request table contains exactly one `mail_notifier_prompt`, in `completed` state with `error_detail: null`. No prompts were injected into either browser or supervisor pane.

Final mailbox evidence:

| Agent | Inbox | Sent | Archive |
| --- | ---: | --- | --- |
| DSH | 0 | Original only | Kimi's `Re:` reply, read and archived |
| Kimi | 0 | Reply only | DSH's original, read, answered, and archived |

The `Re:` stop rule prevented a reply loop. Both agents used the installed Houmao system skills and direct `agents self mail` commands. Automated inspection found zero agent-side command errors in either native log. In particular, Kimi checked `mail archive --help` and used the supported arguments; R3's `No such option '--box'` error did not recur.

## Remaining Observations

- Kimi Web still exposes `web.model: null` and `web.native_agent_live: null` in gateway state even though its configured model is present in the launch manifest and its native turn completed. This is an observability gap, not a mail-round failure.
- Browser login was not tested in R4.
- At the end of the mail test, both gateways were healthy and idle, both notifiers remained enabled at 20 seconds, and both inboxes were empty. R4 teardown is pending.

## Operator Web Restart and Gateway UX

On 2026-11-23, the operator requested a stepwise Web restart with inspection between agents. DSH was relaunched first with a new chat session. Its agent id, gateway port `37605`, tmux session, and mailbox binding remained unchanged; its native session changed to `session-2d1390f0-049f-457b-bd6f-5182a4608a5c` and its native origin to `http://127.0.0.1:36067`. The attach and login helpers were regenerated, and DSH's notifier was temporarily disabled pending the paired restart. Kimi had not yet been relaunched at this checkpoint.

The open gateway's ticketless `http://127.0.0.1:37605/v1/web/enter` route provides the automatic native Web handoff, so the CLI-issued one-time ticket is unnecessary for this access mode. The gateway root itself returned `404 {"detail":"Not Found"}`, which makes the capability hard to discover. [Issue #91](https://github.com/igamenovoer/houmao/issues/91) requests a human-friendly gateway dashboard whose first action is one-click native Web entry for Web-mode agents.

## R4 Notifier Resume, Session Selection, and Teardown

The DSH notifier remained disabled during the restart pause, so Kimi's `Re: Echo message` at `04:31:24Z` initially produced no DSH action. Re-enabling the notifier at 20 seconds admitted `gwreq-20261123-043340Z-8df7adc8` at `04:33:40Z`; the new DSH native session completed the turn at `04:34:04Z`, archived the reply without responding, and emptied its inbox.

The DSH relaunch used `--chat-session-mode new`, which intentionally replaced native conversation `session-6223cb5f-a0aa-410c-89f0-e717b4a8b702` with `session-2d1390f0-049f-457b-bd6f-5182a4608a5c`. The notifier correctly targeted the new manifest-bound conversation. The gateway entry route opens the DSH application but does not select a conversation, so an operator watching the previous conversation initially saw no activity. Selecting the new conversation revealed the turn.

This turn exposed two recoverable agent-side schema mistakes: a direct `/v1/mail/offline/list` request using unsupported fields returned `{"detail":[{"type":"extra_forbidden","loc":[]}]}` before the agent switched to the scoped CLI, and the first archive command used `--message-refs`, receiving `Error: No such option '--message-refs'. Did you mean '--message-ref'?` before correcting the option. Both operations ultimately succeeded.

At `2026-11-23T04:37:42Z`, both R4 notifiers had been disabled and both agents stopped. Their isolated tmux servers were absent and direct socket checks confirmed ports `37605` and `37606` closed. R4 is fully stopped. The operator then requested a completely fresh pair, launched as [R5](2026-11-23-iter3-two-agent-mail-r5-fresh-web-restart.md).
