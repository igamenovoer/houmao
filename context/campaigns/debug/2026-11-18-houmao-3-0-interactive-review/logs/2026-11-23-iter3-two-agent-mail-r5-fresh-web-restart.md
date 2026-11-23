# Iteration 3 R5: Fresh Two-Agent Web Restart

Date: 2026-11-23. Status: ready for operator-driven mail testing. Both agents have fresh native homes and conversations, fresh mailbox bindings, healthy Web gateways, and enabled unread-only notifiers. No R5 mail exchange has been requested or claimed yet.

Previous run: [R4 version-floor rerun](2026-11-23-iter3-two-agent-mail-r4-version-floor.md).

## Clean Start

The R4 agents were stopped at `2026-11-23T04:37:42Z` after both notifiers were disabled. Their isolated tmux servers were absent, and gateway ports `37605` and `37606` returned `connect_ex=111` (`ECONNREFUSED`). R5 uses a new root and does not reuse R4 native conversations, runtime homes, registry, mailbox, or prepared runs:

```text
tmp/houmao-30-iter3-mailbox-r5/
```

The shared offline store was initialized with `houmao-mgr mailbox init` before the first launch. Both fixtures use the default managed agent system-skill pack and the same bounded mail role with the `Re:` reply-stop rule. The manager is `3.0.0rc5+local.0d642af`, DSH is `0.2.2-rc.3`, host Kimi is `2.7.2`, and the model is `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`.

## Fresh Agents

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `433682d6-57bd-47dc-8122-b98396e4afc4` | `8cb9e2d6-0b63-465f-8d32-8cf973c93ea7` |
| Name | `dsh-mailer-r5` | `kimi-mailer-r5` |
| Address | `dsh-mailer-r5@houmao.localhost` | `kimi-mailer-r5@houmao.localhost` |
| Offline binding | `reg-ff4762f07e6442d99caa2d7a10fba3b2` | `reg-bb4669c560724b8da0152fb74e32a58f` |
| Gateway | `http://127.0.0.1:37605` | `http://127.0.0.1:37606` |
| Native origin | `http://127.0.0.1:34391` | `http://127.0.0.1:44695` |
| Native session | `session-67aa251b-9588-44e8-85eb-189444650375` | `session_52592275-54c6-40da-a303-896a88214dfb` |
| Tmux session | `HOUMAO-dsh-mailer-r5-1795408706257` | `HOUMAO-kimi-mailer-r5-1795408715068` |
| Prepared run | `runs/self-hosted-dsh-web-manager-1bb32d700cfb` | `runs/self-hosted-kimi-web-manager-9143e9340457` |

Ticketless gateway entrance links:

```text
http://127.0.0.1:37605/v1/web/enter
http://127.0.0.1:37606/v1/web/enter
```

These links use the open gateway's automatic native authentication redirect. DSH's link opens the native application; select the current R5 conversation in the sidebar if the browser retains another conversation selection.

Watch helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r5/attach-dsh-mailer-r5.sh
tmp/houmao-30-iter3-mailbox-r5/attach-kimi-mailer-r5.sh
tmp/houmao-30-iter3-mailbox-r5/login-dsh-mailer-r5.sh
tmp/houmao-30-iter3-mailbox-r5/login-kimi-mailer-r5.sh
```

The attach helpers resolve their targets from the current Houmao manifest and passed `--print-target` checks. Login helpers were shell-syntax checked but not used to issue ticket URLs.

## Notifier State

Both notifiers are enabled with `interval_seconds: 20` and `mode: unread_only`. Their first observed polls were:

- DSH: `2026-11-23T04:39:42Z`, `last_error: null`, no notification because the fresh inbox is empty.
- Kimi: `2026-11-23T04:39:43Z`, `last_error: null`, no notification because the fresh inbox is empty.

Both gateways report healthy, connected, idle, `queue_depth: 0`, and `request_admission: open`. Both agents remain running for operator inspection and mail testing. R5 teardown is pending.

## DSH Workspace Selection Defect

The first DSH browser opening asked for a Workspace even though the fixture supplied an explicit workdir. Houmao's manifest, launch working directory, and native process cwd all agree on `/data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox-r5/runs/self-hosted-dsh-web-manager-1bb32d700cfb/workdir`. The defect is in native Workspace registration, not path configuration.

`src/houmao/agents/assets/dsh/managed-web.mjs` creates the managed Agent directly with `ctx.agents.create(... meta: {cwd: control.working_directory})` and verifies that cwd, but it does not register that path with DSH's Workspace registry. The browser's first-use flow therefore sees no managed Workspace and requests or creates one independently. At `04:42:21Z`, the native `storages/workspace.json` recorded a browser-created Workspace at `/home/huangzhe` and a separate session `session-7f993ab2-cb1f-492a-b754-77015275c1b5`, rather than the manifest-bound session `session-67aa251b-9588-44e8-85eb-189444650375`. Houmao mail notifications remain bound to the manifest session, not the browser-created one.

The existing Houmao browser-coexistence integration test explicitly calls `/api/workspace/create` with the managed root before using the browser (`tests/integration/agents/dsh/web/test_browser_coexistence.py`), confirming that Workspace projection is a separate setup step. The launch path should perform an idempotent `workspace/create` for `LaunchPlan.working_directory` and verify that the managed session appears in that Workspace before presenting browser entry. Selecting the configured workdir manually is a temporary workaround; no product code was changed during this diagnostic.

Follow-up inspection of the DSH source explains the home-directory display: `directory-picker-browse.list()` with no path lists the host account's home directory by design. DSH's automatic first-use Workspace is also account-centric, at `<Documents>/deepseek-harness/default-workspace`. Its `documentsDirectory` setting changes only the Documents parent and always appends `deepseek-harness/default-workspace`; DSH Web has no exact `--workspace` or `defaultWorkspace=<path>` launch option. That setting cannot represent the existing R5 workdir directly and would not attach the managed session, so it is not the appropriate Houmao fix.

## Live Workspace Create Experiment

At the operator's request, the running DSH instance received a native `/api/workspace/create` request through an authenticated Playwright browser session. The first attempt did not reach DSH because the previously located Chromium 1248 binary had been replaced; the installed Chromium 1255 build then ran the request successfully. The request used the exact managed workdir and returned HTTP 200 with `created: true`:

```text
workspaceId: 5dbd2bb7-62d3-4644-8a74-65017be311d8
path: /data/huangzhe/code/houmao/tmp/houmao-30-iter3-mailbox-r5/runs/self-hosted-dsh-web-manager-1bb32d700cfb/workdir
title: workdir
sessionIds: []
createdAt: 2026-11-23T04:58:56.880Z
```

The Workspace was added without creating a Session. The registry now contains both this `workdir` Workspace and the earlier `/home/huangzhe` Workspace. The managed native session remains `session-67aa251b-9588-44e8-85eb-189444650375`, but the new Workspace's `sessionIds` is empty, so `workspace/create` alone did not associate that existing managed session. A complete Houmao fix must handle session-to-Workspace association separately. [Issue #92](https://github.com/igamenovoer/houmao/issues/92) tracks the managed-launch Workspace and session projection defect and its browser-level acceptance criteria.

## R5 Teardown

Before the R6 rerun on `3.0.0rc5+local.fd857c7`, both R5 notifiers were disabled and both owned native Web hosts stopped successfully. Ports `37605` and `37606` returned `connect_ex=111`, and both fixture-isolated tmux servers were no longer running. R5 mail delivery remained untested; do not infer it from the later R6 run.
