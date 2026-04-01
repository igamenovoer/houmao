# How Do I Watch A Serverless Gateway Mail Notifier Wake A Live Filesystem-Mailbox Session?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENTSYS_AGENT_DEF_DIR=/path/to/agents` or `AGENT_DEF_DIR=/path/to/agents`).

This demo pack answers one narrow question:

> "How can I start one serverless local interactive agent through `houmao-mgr`, register a filesystem mailbox for it, attach a gateway after launch, inject one filesystem message, and prove from durable artifacts that the gateway wake-up completed and the processed mail became read?"

The rewritten pack keeps all generated state under this demo directory. The default roots are:

- `scripts/demo/gateway-mail-wakeup-demo-pack/outputs/claude/`
- `scripts/demo/gateway-mail-wakeup-demo-pack/outputs/codex/`

The pack-local `.gitignore` ignores `outputs/`, including the mailbox root, copied project, runtime, registry, jobs, and autotest artifacts.

## Prerequisites

- `pixi` is installed.
- `tmux` is installed and on `PATH`.
- The repo environment is installed once with `pixi install`.
- Claude credentials exist under `tests/fixtures/agents/brains/api-creds/claude/kimi-coding/`.
- Codex credentials exist under `tests/fixtures/agents/brains/api-creds/codex/yunwu-openai/`.

The tracked live fixtures for this pack are:

- selector: `gateway-mail-wakeup-demo`
- Claude provider: `claude_code`
- Codex provider: `codex`
- role: `gateway-mail-wakeup-demo`
- copied dummy project: `tests/fixtures/dummy-projects/mailbox-demo-python`

## Filesystem Layout

```text
scripts/demo/gateway-mail-wakeup-demo-pack/outputs/<tool>/
├── control/                    # persisted state, launch, inspect, report, and verify artifacts
├── deliveries/                 # staged Markdown plus managed delivery payload JSON
├── evidence/                   # best-effort tmux pane snapshots for processed deliveries
├── jobs/                       # run-local job root
├── logs/                       # stdout/stderr logs from `houmao-mgr`
├── mailbox/                    # pack-local filesystem mailbox root
├── outputs/                    # wake-up artifact written by the agent
├── project/                    # copied dummy project initialized as a fresh git repo
├── registry/                   # run-local managed-agent registry root
└── runtime/                    # run-local managed-agent runtime root
```

The mailbox root is always under the selected pack-local output root. This demo does not write mailbox state to repo-global temp roots or operator defaults outside the pack.

## Control Flow

The live flow is fully serverless:

1. `houmao-mgr mailbox init --mailbox-root <pack-local-root>/mailbox`
2. `houmao-mgr agents launch --agents gateway-mail-wakeup-demo --provider <claude_code|codex>`
3. `houmao-mgr agents mailbox register ...`
4. `houmao-mgr agents gateway attach ...`
5. `houmao-mgr agents gateway mail-notifier enable ...`
6. inject one filesystem message through the managed delivery boundary
7. wait until the gateway wake-up completes, the output file is written, and the delivered message is observed read

The injected body template is [`inputs/wake_up_message.md`](./inputs/wake_up_message.md). It asks the agent to write the current UTC timestamp to the pack-local output file and to avoid marking the message read until that write succeeds.

## Automatic Workflow

Run one canonical end-to-end flow for a single tool:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh auto --tool codex
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh auto --tool claude
```

Run both tools sequentially with separate tool-scoped artifacts:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh matrix
```

`auto` and `matrix` both stop the managed session after verification so repeated unattended runs do not leave stale live sessions behind.

## Manual Workflow

Start one live serverless session and keep it running:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh start --tool codex
```

Inject one message with the tracked body template:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh manual-send
```

Inject one message with explicit body content:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh manual-send \
  --subject "Manual wake-up" \
  --body-content "Write the current UTC time to scripts/demo/gateway-mail-wakeup-demo-pack/outputs/codex/outputs/manual.txt"
```

Inject a burst:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh manual-send-many \
  --count 3 \
  --subject-prefix "Gateway burst"
```

Stop the live managed agent:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh stop
```

The pack always stages Markdown and delivery payloads under `deliveries/` and delivers through the managed filesystem contract. It never mutates mailbox SQLite directly.

## Unread Reminder Semantics

The gateway notifier is readiness-gated, not one-prompt-per-message.

- One prompt may summarize multiple unread messages.
- The notifier skips polls while the managed prompt surface is not ready for input.
- If unread mail remains and the session becomes prompt-ready again, the gateway may remind again even when the unread snapshot is unchanged.
- Valid success means unread work was surfaced and processed, not that each message caused a unique prompt row.

That is why the verification contract focuses on durable notifier audit and queue evidence plus final mailbox read-state, instead of exact per-poll sequencing.

## Inspect And Verify

Capture a fresh inspection snapshot:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh inspect
```

Rebuild and verify the sanitized golden report:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh verify
```

The raw inspect snapshot keeps the detailed notifier audit rows. The sanitized golden report keeps only stable assertions:

- tool-selected serverless session identity
- notifier enabled
- notifier enqueued mail work
- no notifier poll errors
- queue recorded and completed a notifier request
- the canonical delivered message became read
- final unread count is zero
- the output file exists, looks like an RFC3339 timestamp, and is newer than the delivery
- the output root and mailbox root stayed pack-local

Refresh the tracked snapshot after an intentional contract change:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/run_demo.sh verify --snapshot
```

## Autotest

The pack ships a first-class real-agent harness:

```bash
scripts/demo/gateway-mail-wakeup-demo-pack/autotest/run_autotest.sh --case real-agent-preflight
scripts/demo/gateway-mail-wakeup-demo-pack/autotest/run_autotest.sh --case real-agent-both-tools-auto
```

The harness writes machine-readable results under `outputs/autotest/.../control/autotest/` and preserves per-phase logs under `outputs/autotest/.../logs/autotest/`.
