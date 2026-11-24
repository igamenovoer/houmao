# Iteration 3 R6: Fresh Web Mailbox Test With Workspace and Dashboard Changes

Date: 2026-11-23. Status: ready for interactive operator inspection and mail testing. No R6 mail has been sent and no notifier-driven turn is claimed yet.

Previous run: [R5 fresh Web restart](2026-11-23-iter3-two-agent-mail-r5-fresh-web-restart.md).

## Clean Start and Versions

Both R5 notifiers were disabled and both owned native Web hosts stopped successfully. Gateway ports `37605` and `37606` then returned `connect_ex=111` (`ECONNREFUSED`), and both fixture-isolated tmux servers reported that they were not running. R6 uses a new root and does not reuse R5 conversations, native homes, registry, mailbox, or prepared runs:

```text
tmp/houmao-30-iter3-mailbox-r6/
```

The manager is `3.0.0rc5+local.fd857c7` at Git `fd857c72`. This includes `fdef343a fix: open the bound DSH Web conversation` and `9c69c96d feat: add public gateway dashboard`. DSH is `0.2.2-rc.3`, host Kimi is `2.7.2`, and the model is `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`. Both fixtures use the default managed system-skill policy and the bounded one-round mail role with the `Re:` reply-stop rule.

Two operator command errors occurred during setup and were corrected without changing product code:

- The first cleanup-check script used `set -e` around `tmux list-sessions`; the expected nonzero status for an already stopped isolated server ended that check early. The follow-up handled that expected status explicitly.
- The first R6 mailbox initialization incorrectly supplied `--channel offline`. This build's `houmao-mgr mailbox init` accepts mailbox and registry root options but no channel option. Running `houmao-mgr mailbox init` with `HOUMAO_GLOBAL_MAILBOX_DIR` initialized the store successfully.

## Fresh Agents

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `23d47ea1-866e-4984-a433-d0eaa19d3beb` | `7d418acb-2801-4a60-a1da-40a8ab91d271` |
| Name | `dsh-mailer-r6` | `kimi-mailer-r6` |
| Address | `dsh-mailer-r6@houmao.localhost` | `kimi-mailer-r6@houmao.localhost` |
| Offline binding | `reg-2b80afbabd1f44a78b286a5261dd5b51` | `reg-796278ec82eb4878a53d2b08b6d78c03` |
| Gateway | `http://127.0.0.1:37605` | `http://127.0.0.1:37606` |
| Native origin | `http://127.0.0.1:33045` | `http://127.0.0.1:40505` |
| Native session | `session-02ac5a05-517d-44dd-afaa-d7ba99f22b8b` | `session_4f364772-dc95-481f-811a-5a1f85a5b901` |
| Runtime session | `dsh_web-20261123-072602Z-512f05e5` | `kimi_web-20261123-072607Z-71d0ecd6` |
| Tmux session | `HOUMAO-dsh-mailer-r6-1795418762848` | `HOUMAO-kimi-mailer-r6-1795418767870` |
| Prepared run | `runs/self-hosted-dsh-web-manager-fc69c21a6eb7` | `runs/self-hosted-kimi-web-manager-ebb375c1c35c` |

Both gateways report healthy, connected, idle, `queue_depth: 0`, and `request_admission: open`. Both native surfaces are available and accept prompts. The dashboard roots return HTTP 200, and both `/v1/web/enter` routes return HTTP 302. This verifies route availability only; the operator's browser inspection remains the acceptance check for the new dashboard and DSH bound-conversation behavior.

Ticketless entrance links:

```text
http://127.0.0.1:37605/v1/web/enter
http://127.0.0.1:37606/v1/web/enter
```

Manifest-based watch and login helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r6/attach-dsh-mailer-r6.sh
tmp/houmao-30-iter3-mailbox-r6/attach-kimi-mailer-r6.sh
tmp/houmao-30-iter3-mailbox-r6/login-dsh-mailer-r6.sh
tmp/houmao-30-iter3-mailbox-r6/login-kimi-mailer-r6.sh
```

Both attach helpers passed `--print-target` checks and resolved their tmux session and isolated socket from the live Houmao manifest. Login helpers passed shell-syntax checks but were not used to issue ticket URLs.

## Notifier State Before Mail

Both notifiers are enabled at `interval_seconds: 20`, `mode: unread_only`, with `supported: true`. Their first observed polls completed with `last_error: null`:

- DSH: `2026-11-23T07:28:24Z`, no notification.
- Kimi: `2026-11-23T07:28:25Z`, no notification.

The next interactive step is DSH-to-Kimi mail delivery after the operator inspects both Web entrances. Do not claim delivery, wake-up, reply, archive, busy-skip, or teardown until those events are observed.

## In-Agent Peer Discovery Failure

At the operator's request, both managed agents tried to list their peers. Their native histories show that both followed the installed guidance and ran `houmao-mgr agents global list`. Both received the account-default registry containing stale R2 records, `dsh-mailer-r2` and `kimi-mailer-r2`, rather than the active R6 registry. Kimi explicitly noticed that its own R6 identity was absent. Neither discovered the current R6 peer.

The shared registry itself is intact. From the host, the absolute R6 root lists both R6 agents as active and available. Repeating the command with either agent's project overlay and the same absolute shared roots also lists both agents. The native DSH and Kimi process environments, however, contain none of `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_RUNTIME_DIR`, or `HOUMAO_GLOBAL_MAILBOX_DIR`. Without the registry override, `agents global list` resolves the account-default `~/.config/houmao/registry`, which explains the R2 result.

This is a Web launch-environment defect, not an error in either agent's command selection:

- `src/houmao/agents/realm_controller/backends/dsh_web.py:357-367` builds the DSH environment from a baseline allowlist plus `plan.env`; the resulting native environment omits the shared Houmao roots.
- `src/houmao/agents/realm_controller/backends/kimi_web.py:303-311` applies the same baseline-plus-`plan.env` pattern and omits those roots.
- `src/houmao/srv_ctrl/commands/managed_agents.py:5543-5562` makes `agents global list` read the process-global registry path. It does not derive the registry from the caller's verified managed-self manifest.
- Verified-self mail resolution is a separate path: `src/houmao/agents/realm_controller/self_manifest.py:108-117` reads the execution binding and supplies its registry root explicitly. The peer-listing failure therefore does not establish that notifier-driven mail is broken.

A first attempted host reproduction was invalid and is not product evidence: it computed `ROOT=$PWD/tmp/...` after changing into each agent workdir, producing a nested nonexistent registry path and an empty list. The corrected reproduction used one absolute R6 root and found both agents from both overlays. A related `mail resolve-live` failure against port `9891` during that invalid reproduction had the same bad-root cause and was not retaken as a product failure.

No product code was changed. A fix should make the managed shared registry available to in-agent global discovery, either by preserving the non-secret root in the Web native environment or by making the command select the verified-self registry when invoked in a managed context. Add an end-to-end assertion inside both Web agents; host-only listing does not cover this failure.

Follow-up inspection found that Houmao already has a central `LaunchPlan.env`, an owner-private persisted launch environment, and a mapping-based tmux setter, but the Web backends do not connect them. One-off `project agents launch --env-set NAME=value|NAME` can add values to the native Web process, but persistent specialist records reject Houmao-owned names and neither Web backend publishes the mapping to tmux. [Issue #93](https://github.com/igamenovoer/houmao/issues/93) requests one authoritative environment-publication contract across backends, covering tmux, native processes, relaunch, and in-agent peer discovery with explicit credential-handling rules.

## R6 Teardown

Before the R7 rerun, both R6 notifiers were disabled and both owned native Web hosts stopped successfully. Ports `37605` and `37606` returned `connect_ex=111`, and both fixture-isolated tmux servers were no longer running. R6 mail delivery remained untested; only the operator-requested peer-listing turns ran. R7 uses fresh state and the unified launch-environment implementation.
