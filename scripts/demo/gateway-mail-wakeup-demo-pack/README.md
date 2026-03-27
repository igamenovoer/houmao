# How Do I Watch The Gateway Mail Notifier Wake A Live Mailbox-Enabled Session And Inspect Its Durable Audit Trail?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This tutorial pack answers one concrete question:

> "How can I start one mailbox-enabled `houmao_server_rest` session through demo-owned `houmao-server`, attach the gateway after launch, inject a wake-up message, and verify the outcome through gateway-owned artifacts instead of guessing from terminal text?"

Success means you can run one end-to-end automatic flow, inspect the durable notifier audit history in `queue.sqlite`, confirm the gateway either enqueued or skipped work for an explicit reason, and see the demo-owned output file written by the agent after the wake-up mail lands.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed (`pixi install` once).
- [ ] `tmux` is installed and on `PATH`.
- [ ] The default Codex credential profile selected by `tests/fixtures/agents/blueprints/mailbox-demo-codex.yaml` is available.
- [ ] You are running from this repository checkout.

The default verified path is demo-owned `houmao-server`. The helper starts or reuses one local server rooted under `<demo-output-dir>/server/`, launches the runtime session with `backend=houmao_server_rest`, attaches the gateway through the server-managed agent route after launch, and stops that same server again during cleanup when the demo owns it.

Override the listener with `HOUMAO_BASE_URL=http://127.0.0.1:<port>` if needed. The selected server must belong to the same demo output root; the helper fails clearly instead of targeting an unrelated external server instance.

## Filesystem Layout

```text
<demo-output-dir>/
├── deliveries/                # staged Markdown plus managed delivery payload files
├── inputs/                    # copied tracked tutorial inputs
├── outputs/                   # demo-owned wake-up artifact written by the agent
├── project/                   # copied dummy-project fixture initialized as a fresh git repo
│   └── skills/mailbox/        # project-local mailbox skill docs mirrored from the runtime home
├── runtime/                   # built brain outputs and session manifests
├── server/                    # demo-owned `houmao-server` runtime and process logs
├── shared-mailbox/            # shared filesystem mailbox root
├── server_start.json
├── brain_build.json
├── session_start.json
├── gateway_attach.json
├── notifier_enable.json
├── inspect.json
├── report.json
└── report.sanitized.json
```

By default, the wrapper uses `tmp/demo/gateway-mail-wakeup-demo-pack`. Override it with `--demo-output-dir <abs-or-rel-path>`. Relative paths resolve from the repository root.

Notes:

- The default tracked fixture is `tests/fixtures/dummy-projects/mailbox-demo-python`.
- The default tracked blueprint is `blueprints/mailbox-demo-codex.yaml`.
- `project/` is provisioned by copying the tracked source-only dummy project into the selected demo root, writing `.houmao-demo-project.json`, and initializing a fresh standalone git repo for that run.
- This pack is intentionally a narrow mailbox and runtime-contract walkthrough, so it uses the copied dummy-project plus `mailbox-demo` fixture shape instead of a repository worktree plus heavyweight engineering role.
- Demo roots that still contain the old repository-worktree layout are stale for this pack. Use a fresh `--demo-output-dir` or remove the old demo root before rerunning.

## Unread-Set Semantics

The gateway notifier is unread-set based, not per-message based.

- One poll cycle asks whether unread mail exists and whether the session is eligible for a reminder prompt.
- A single reminder prompt may summarize multiple unread messages.
- If the unread set is unchanged, later polls may deduplicate instead of enqueueing another reminder.
- Burst delivery success means no unread mail was lost, not that one gateway prompt was emitted per message.

That is why this pack treats the durable audit table in `queue.sqlite` as the detailed source of truth. The live notifier-status surface remains a compact snapshot, while `gateway_notifier_audit` records one structured decision row per enabled poll cycle.

## Automatic Workflow

Run the maintainer-style end-to-end flow:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh
```

What it does:

1. Provisions `<demo-output-dir>/project` by copying the tracked dummy-project fixture and initializing it as a fresh standalone git repo.
2. Starts or reuses demo-owned `houmao-server` under `<demo-output-dir>/server/`.
3. Builds the tracked lightweight mailbox-demo Codex brain, mirrors its runtime mailbox skill docs into `project/skills/mailbox/`, and starts one mailbox-enabled `houmao_server_rest` session.
4. Resolves the server-managed agent identity for that session, attaches the gateway through the server-managed route, and enables notifier polling with a one-second interval.
5. Waits for the session to look idle, using server-managed agent readiness first and gateway status as a fallback.
6. Injects one wake-up mail through the managed mailbox delivery script.
7. Waits for `<demo-output-dir>/outputs/wakeup-time.txt`.
8. Builds `report.json`, sanitizes it to `report.sanitized.json`, and compares that sanitized output to `expected_report/report.json`.

The tracked mail body lives in [`inputs/wake_up_message.md`](inputs/wake_up_message.md) and uses the `{{OUTPUT_FILE_PATH}}` token so the helper can point the managed agent at the current demo-owned output file.

## Manual Workflow

Start the live session and keep it running:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start
```

If an old demo root already contains a repository worktree or another unmanaged `project/` directory, the command now fails before any live runtime work starts. That failure is intentional; remove the stale demo root or choose a fresh `--demo-output-dir`.

Inject one message from inline text:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh manual-send \
  --subject "Manual wake-up" \
  --body-content "Write the current UTC time to /tmp/manual-wakeup.txt"
```

Inject one message from a Markdown file:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh manual-send \
  --subject "Manual wake-up from file" \
  --body-file scripts/demo/gateway-mail-wakeup-demo-pack/inputs/wake_up_message.md
```

Inject a burst of messages against the same live session:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh manual-send-many \
  --count 3 \
  --subject-prefix "Gateway burst" \
  --body-content "Unread burst message for gateway batching."
```

The helper always stages Markdown under `deliveries/staged/`, writes one managed delivery payload under `deliveries/payloads/`, and invokes the projected mailbox script `shared-mailbox/rules/scripts/deliver_message.py`. The pack never mutates mailbox SQLite directly.

Stop the live managed agent and demo-owned server:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh stop
```

## Inspect And Verify

Capture a fresh inspection snapshot:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh inspect
```

That snapshot writes `inspect.json` under the demo output directory and includes:

- server lifecycle and managed-agent identity evidence,
- compact notifier status,
- durable notifier audit summary plus raw rows,
- notifier-related queue and event evidence,
- mailbox-local unread state,
- output-file evidence.

Rebuild and verify the sanitized report explicitly:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh verify
```

The expected contract intentionally compares summary-shaped evidence rather than exact poll-by-poll sequences. Raw audit rows remain in `inspect.json` for debugging, but `expected_report/report.json` only tracks stable facts such as:

- demo-owned server lifecycle and managed-agent identity,
- notifier enabled,
- notifier enqueued at least one wake-up prompt,
- no poll errors were observed,
- project-local mailbox skill surface present,
- mailbox unread state was visible,
- the output file existed and looked timestamp-like.

## Snapshot Refresh

Refresh the tracked sanitized snapshot after an intentional contract change:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh --snapshot-report
```

Or rebuild the report from an already-started demo:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh verify --snapshot-report
```

## Appendix

Tracked inputs:

- [`inputs/demo_parameters.json`](inputs/demo_parameters.json)
- [`inputs/wake_up_message.md`](inputs/wake_up_message.md)

Pack-local helpers:

- [`scripts/tutorial_pack_helpers.py`](scripts/tutorial_pack_helpers.py)
- [`scripts/inspect_demo.py`](scripts/inspect_demo.py)
- [`scripts/sanitize_report.py`](scripts/sanitize_report.py)
- [`scripts/verify_report.py`](scripts/verify_report.py)

Key output artifacts:

- `server_start.json`: persisted demo-owned `houmao-server` lifecycle state.
- `shared-mailbox/index.sqlite`: shared mailbox index.
- `shared-mailbox/mailboxes/<address>/mailbox.sqlite`: mailbox-local unread state.
- `gateway_root/queue.sqlite`: durable gateway requests plus `gateway_notifier_audit`.
- `gateway_root/events.jsonl`: request lifecycle evidence.
- `outputs/wakeup-time.txt`: demo-owned automatic wake-up artifact.
