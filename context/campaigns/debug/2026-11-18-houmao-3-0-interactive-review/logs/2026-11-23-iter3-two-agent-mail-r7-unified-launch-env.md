# Iteration 3 R7: Fresh Web Restart With Unified Launch Environment

Date: 2026-11-23. Status: in-agent peer discovery passed. A DSH-to-Kimi notifier round completed with an acknowledgement and archive, but the requested Tavily research was not performed because the fixture role explicitly defines an acknowledgement-only workload.

Previous run: [R6 Workspace and dashboard test](2026-11-23-iter3-two-agent-mail-r6-workspace-dashboard.md).

## Clean Start and Versions

Both R6 notifiers were disabled and both owned native Web hosts stopped successfully. Gateway ports `37605` and `37606` returned `connect_ex=111` (`ECONNREFUSED`), and both fixture-isolated tmux servers were no longer running. R7 uses a new root and does not reuse R6 conversations, native homes, registry, mailbox, or prepared runs:

```text
tmp/houmao-30-iter3-mailbox-r7/
```

The uv-installed manager is `3.0.0rc5+local.9c66cb3`; the local suffix is a tree identifier, not a commit hash. The source checkout contains `eb9481c6 fix: unify managed agent launch environments`, and [issue #93](https://github.com/igamenovoer/houmao/issues/93) is closed. DSH is `0.2.2-rc.3`, host Kimi is `2.7.2`, and the model is `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`. Both fixtures use the default managed system-skill policy and the bounded one-round mail role with the `Re:` reply-stop rule.

## Fresh Agents

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `b425037d-34de-447d-98cd-36479644c606` | `692594e2-445e-4a4c-9f9a-fe0f1c620629` |
| Name | `dsh-mailer-r7` | `kimi-mailer-r7` |
| Address | `dsh-mailer-r7@houmao.localhost` | `kimi-mailer-r7@houmao.localhost` |
| Offline binding | `reg-89135f7d597245959ba6a55f88806144` | `reg-f3071726886745dab48ceb5b01ca6623` |
| Gateway | `http://127.0.0.1:37605` | `http://127.0.0.1:37606` |
| Native origin | `http://127.0.0.1:39983` | `http://127.0.0.1:41187` |
| Native session | `session-4b65f1f9-792f-457f-a8c6-324e6a417fd5` | `session_be3da2ac-60ae-402e-91b0-a966c00c0524` |
| Runtime session | `dsh_web-20261123-110218Z-6d50c425` | `kimi_web-20261123-110223Z-5b4ffa57` |
| Tmux session | `HOUMAO-dsh-mailer-r7-1795431738928` | `HOUMAO-kimi-mailer-r7-1795431743872` |
| Prepared run | `runs/self-hosted-dsh-web-manager-163df6bd6e26` | `runs/self-hosted-kimi-web-manager-5492ee44672c` |

Both gateways report healthy, connected, idle, `queue_depth: 0`, and `request_admission: open`. Both native surfaces are available. Dashboard roots return HTTP 200 and both `/v1/web/enter` routes return HTTP 302.

Ticketless entrance links:

```text
http://127.0.0.1:37605/v1/web/enter
http://127.0.0.1:37606/v1/web/enter
```

Manifest-based watch and login helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r7/attach-dsh-mailer-r7.sh
tmp/houmao-30-iter3-mailbox-r7/attach-kimi-mailer-r7.sh
tmp/houmao-30-iter3-mailbox-r7/login-dsh-mailer-r7.sh
tmp/houmao-30-iter3-mailbox-r7/login-kimi-mailer-r7.sh
```

Both attach helpers passed `--print-target` checks and resolved their tmux session and isolated socket from the live Houmao manifest. Login helpers passed shell-syntax checks but were not used to issue ticket URLs.

## Unified Environment Verification

The R6 defect did not recur at the environment level. For both agents, `tmux show-environment` and the native process environment contain all four expected values:

- `HOUMAO_GLOBAL_REGISTRY_DIR=/data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox-r7/registry`
- `HOUMAO_GLOBAL_RUNTIME_DIR=/data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox-r7/runtime`
- `HOUMAO_GLOBAL_MAILBOX_DIR=/data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox-r7/mailbox`
- `HOUMAO_PROJECT_OVERLAY_DIR` points to each prepared run's own `workdir/.houmao`.

The runtime manifests now live under the shared R7 runtime root rather than an overlay-local runtime root. This verifies tmux and native-process propagation directly. The original in-agent `agents global list` scenario has not yet been rerun in R7 and remains an interactive acceptance step.

## Notifier State Before Mail

Both notifiers are enabled at `interval_seconds: 20`, `mode: unread_only`, with `supported: true`. Their first observed polls completed with `last_error: null`:

- DSH: `2026-11-23T11:03:25Z`, no notification.
- Kimi: `2026-11-23T11:03:26Z`, no notification.

Do not claim in-agent peer discovery, delivery, wake-up, reply, archive, busy-skip, or teardown until those events are observed.

## In-Agent Peer Discovery Passed

Before the mail request, Kimi ran `houmao-mgr agents global list` inside its managed Web session and reported exactly the two current R7 agents, `kimi-mailer-r7` and `dsh-mailer-r7`, both active. This is the in-agent acceptance evidence that was missing in R6 and complements the direct tmux/native environment checks above.

## Request Work Was Replaced by the Fixture's Ack-Only Role

At `2026-11-23T11:09:22Z`, DSH sent Kimi a request titled `Request: use Tavily to find recent RSI self-improvement papers`. The body asked Kimi to use Tavily to find recent Recurrent Self-Improvement and self-improvement publications and summarize key findings.

Kimi's notifier wake-up, gateway-backed list/read/reply/archive operations all succeeded. It loaded `houmao-process-emails-via-gateway`, read the full body with `content_complete: true`, replied with `MAIL-OK`, and archived the original at `2026-11-23T11:10:03Z` approximately. It did not invoke Tavily or perform the research.

The cause is the campaign fixture role at `tmp/houmao-30-iter3-mailbox-r7/inputs/mail-role.txt`. It instructs the agent to reply with a concise acknowledgement containing `MAIL-OK`, archive the message, and stop after one round. That role was designed for the earlier M1/M2 delivery and reply-stop test, not for executing arbitrary work requests.

The installed general mail skill does contain the missing behavior: `houmao-process-emails-via-gateway/SKILL-MAIN.md` steps 13 and 14 say to complete the requested work and reply only after that work succeeds. Its guardrails also forbid archiving unfinished mail. Kimi's native reasoning explicitly reconciled the two instructions by deciding, `Per my role, the work is the acknowledgment itself.` The test-specific role therefore narrowed the general workflow and caused the ack-only behavior. This is a fixture/test-design failure, not evidence that the installed mail skill omits task execution.

For future task-execution rounds, revise the role to require the requested work first, send a result-bearing reply only after success, and archive only after both succeed. Reserve `MAIL-OK` for delivery-only messages, or remove it from task-bearing rounds. The current message is already archived and must not be represented as completed research.

## R7 Teardown

Before the prompt-neutral R8 rerun, both R7 notifiers were disabled and both owned native Web hosts stopped successfully. R8 uses fresh registry, mailbox, runtime homes, and native conversations. Its specialist prompts were cleared before launch so only the default native and Houmao-managed prompts remain.
