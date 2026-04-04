# How Do I Watch One Live TUI Agent Wake Up On Mail, Acknowledge The Work In Chat, And Clear Three Messages Through The Gateway Mailbox Flow?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This demo pack answers one narrow question:

> "How can I start one mailbox-enabled Claude Code or Codex TUI session, let the gateway wake it on unread filesystem mail, watch the agent acknowledge each turn in chat, and verify the outcome from stable mailbox and gateway artifacts instead of transcript wording?"

The pack is intentionally single-agent and tool-explicit. You pick `claude` or `codex` for each run. The harness then injects at most one new message every five seconds, only when the mailbox is clear and the gateway reports that the session is safe to admit new work.

## Prerequisites

- [ ] `pixi` is installed.
- [ ] `tmux` is installed and on `PATH`.
- [ ] The repository environment is installed (`pixi install` once).
- [ ] The selected tool profile referenced by the tracked `mailbox-demo` blueprint is available.
- [ ] You are running from this repository checkout.

## Command Surface

Automatic workflow:

```bash
scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh auto --tool codex
scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh auto --tool claude
```

Stepwise workflow:

```bash
scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh start --tool codex
scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh drive
scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh inspect
scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh verify
scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh stop
```

The automatic workflow is `start -> drive -> inspect -> verify -> stop`.

## Output Root Ownership

If you omit `--demo-output-dir`, the runner uses a tool-scoped pack-local root:

- `scripts/demo/tui-mail-gateway-demo-pack/outputs/claude/`
- `scripts/demo/tui-mail-gateway-demo-pack/outputs/codex/`

Relative `--demo-output-dir` values resolve from the repository root.

All demo-owned generated state stays under the selected output root:

- `control/`
- `cao/`
- `runtime/`
- `registry/`
- `mailbox/`
- `jobs/`
- `deliveries/`
- `project/`
- `evidence/`
- `logs/`

The copied dummy project comes from `tests/fixtures/dummy-projects/mailbox-demo-python`. The selected runtime blueprint comes from the tracked `mailbox-demo` fixture family.

## Harness Contract

The drive loop has two operator-facing constants:

- cadence: `5` seconds
- success rule: `3` processed turns with final unread count `0`

At each tick the harness:

1. inspects the shared mailbox unread state,
2. inspects whether the gateway reports `request_admission=open`, `active_execution=idle`, and `queue_depth=0`,
3. injects one new tracked message only when both checks are satisfied,
4. waits for that specific injected message to transition from unread to read before allowing the next injection.

The harness never mutates mailbox SQLite directly. It stages Markdown, writes a managed delivery payload, and commits the message through the managed mailbox delivery boundary.

## Inspect And Verify

`inspect` writes `control/inspect.json`. It includes:

- selected tool and session identity,
- gateway status plus notifier status,
- durable notifier-audit summary,
- mailbox unread snapshot,
- harness progress and per-turn delivery metadata,
- tmux evidence paths for each processed turn.

`verify` writes:

- `control/report.json`
- `control/report.sanitized.json`

The stable verification contract does not compare exact chat wording. Instead it checks that:

- three messages were injected,
- three processed-turn read transitions were observed,
- the final unread count is zero,
- notifier polling stayed enabled and enqueued work,
- each processed turn has bounded tmux evidence saved for human review.

Use `--snapshot` with `verify` or `auto` when you intentionally change the sanitized contract and want to refresh `expected_report/report.json`.

## Human-Review TUI Evidence

The demo keeps per-turn tmux pane captures under `evidence/turn-XXX/`. Those artifacts are for bounded review only. They help maintainers confirm that the live TUI surfaced an acknowledgment, but the sanitized contract intentionally avoids exact transcript assertions because Claude and Codex wording varies across runs.
