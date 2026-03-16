# How Do I Watch The Gateway Mail Notifier Wake A Live Mailbox-Enabled Session And Inspect Its Durable Audit Trail?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This tutorial pack answers one concrete question:

> "How can I start one mailbox-enabled CAO session, attach the gateway, enable unread-mail polling, inject a wake-up message, and verify the outcome through gateway-owned artifacts instead of guessing from terminal text?"

Success means you can run one end-to-end automatic flow, inspect the durable notifier audit history in `queue.sqlite`, confirm the gateway either enqueued or skipped work for an explicit reason, and see the demo-owned output file written by the agent after the wake-up mail lands.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed (`pixi install` once).
- [ ] `tmux` is installed and on `PATH`.
- [ ] The default Codex credential profile selected by `tests/fixtures/agents/blueprints/gpu-kernel-coder-codex.yaml` is available.
- [ ] You are running from this repository checkout.

The default verified path is launcher-managed loopback CAO. The helper writes a demo-local launcher config under `<demo-output-dir>/cao/`, starts or reuses CAO there, derives the matching `CAO_PROFILE_STORE`, and stops that CAO again during cleanup when the demo owns it.

If you point `CAO_BASE_URL` at a non-loopback or intentionally external CAO service, provide `CAO_PROFILE_STORE` explicitly. Otherwise the helper exits `0` with a `SKIP:` message instead of guessing profile-store state.

## Filesystem Layout

```text
<demo-output-dir>/
├── cao/                       # demo-local CAO launcher config and runtime state
├── deliveries/                # staged Markdown plus managed delivery payload files
├── inputs/                    # copied tracked tutorial inputs
├── outputs/                   # demo-owned wake-up artifact written by the agent
├── project/                   # git worktree of this repository; the live agent workdir
├── runtime/                   # built brain outputs and session manifests
├── shared-mailbox/            # shared filesystem mailbox root
├── brain_build.json
├── session_start.json
├── gateway_attach.json
├── notifier_enable.json
├── inspect.json
├── report.json
└── report.sanitized.json
```

By default, the wrapper uses `tmp/demo/gateway-mail-wakeup-demo-pack`. Override it with `--demo-output-dir <abs-or-rel-path>`. Relative paths resolve from the repository root.

`project/` is provisioned through `git worktree add --detach ... HEAD`, so the managed agent sees committed repository state at `HEAD`, not your uncommitted changes in the source checkout.

## Unread-Set Semantics

The gateway notifier is unread-set based, not per-message based.

- One poll cycle asks whether unread mail exists and whether the session is eligible for a reminder prompt.
- A single reminder prompt may summarize multiple unread messages.
- If the unread set is unchanged, later polls may deduplicate instead of enqueueing another reminder.
- Burst delivery success means no unread mail was lost, not that one gateway prompt was emitted per message.

That is why this pack treats the durable audit table in `queue.sqlite` as the detailed source of truth. `GET /v1/mail-notifier` remains a compact snapshot, while `gateway_notifier_audit` records one structured decision row per enabled poll cycle.

## Automatic Workflow

Run the maintainer-style end-to-end flow:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh
```

What it does:

1. Provisions `<demo-output-dir>/project` as a git worktree.
2. Starts or reuses loopback CAO under `<demo-output-dir>/cao/`.
3. Builds the tracked Codex brain and starts one mailbox-enabled session.
4. Attaches the gateway and enables notifier polling with a one-second interval.
5. Waits for the session to look idle, using CAO terminal status first and gateway status as a fallback.
6. Injects one wake-up mail through the managed mailbox delivery script.
7. Waits for `<demo-output-dir>/outputs/wakeup-time.txt`.
8. Builds `report.json`, sanitizes it to `report.sanitized.json`, and compares that sanitized output to `expected_report/report.json`.

The tracked mail body lives in [`inputs/wake_up_message.md`](inputs/wake_up_message.md) and uses the `{{OUTPUT_FILE_PATH}}` token so the helper can point the managed agent at the current demo-owned output file.

## Manual Workflow

Start the live session and keep it running:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start
```

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

Stop the live session and demo-owned CAO:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh stop
```

## Inspect And Verify

Capture a fresh inspection snapshot:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh inspect
```

That snapshot writes `inspect.json` under the demo output directory and includes:

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

- notifier enabled,
- notifier enqueued at least one wake-up prompt,
- no poll errors were observed,
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

- `shared-mailbox/index.sqlite`: shared mailbox index.
- `shared-mailbox/mailboxes/<address>/mailbox.sqlite`: mailbox-local unread state.
- `gateway_root/queue.sqlite`: durable gateway requests plus `gateway_notifier_audit`.
- `gateway_root/events.jsonl`: request lifecycle evidence.
- `outputs/wakeup-time.txt`: demo-owned automatic wake-up artifact.
