# `single-agent-mail-wakeup/`

Supported runnable demo for the modern single-agent `houmao-mgr project easy` gateway wake-up workflow.

It shows the maintained TUI flow from project creation through gateway notifier wake-up:

1. copy a demo-owned dummy project under `outputs/<tool>/project/`
2. redirect Houmao overlay state into `outputs/<tool>/overlay/` with `HOUMAO_PROJECT_OVERLAY_DIR`
3. import the local Claude or Codex fixture auth bundle into that overlay
4. create a project-easy specialist and launch one TUI instance
5. initialize the project mailbox, register the agent and operator addresses, attach a live gateway, and enable mail-notifier polling
6. inject one filesystem-backed operator message
7. verify artifact creation under `project/tmp/`, actor-scoped unread completion through `agents mail check --unread-only`, and structural project-mailbox visibility

## Supported Lanes

- `claude`
- `codex`

This demo is intentionally TUI-only. It does not claim headless or mixed-mode support.

## Output Layout

Each tool lane owns one demo-local output root under `outputs/<tool>/`:

- `project/`: copied dummy project and visible worktree
- `overlay/`: redirected Houmao overlay selected through `HOUMAO_PROJECT_OVERLAY_DIR`
- `runtime/`, `registry/`, `jobs/`: demo-owned runtime state
- `control/`, `logs/`, `deliveries/`, `evidence/`: persisted demo artifacts

Generated outputs are ignored through [outputs/.gitignore](outputs/.gitignore).

## Prerequisites

- `pixi`
- `tmux`
- `claude` for the Claude lane or `codex` for the Codex lane
- local fixture auth bundles at:
  - `tests/fixtures/agents/tools/claude/auth/kimi-coding`
  - `tests/fixtures/agents/tools/codex/auth/yunwu-openai`

The demo fails early and names the missing fixture path when a required auth bundle is absent.

## Commands

One-shot automatic run:

```bash
scripts/demo/single-agent-mail-wakeup/run_demo.sh auto --tool claude
scripts/demo/single-agent-mail-wakeup/run_demo.sh auto --tool codex
```

Stepwise workflow:

```bash
scripts/demo/single-agent-mail-wakeup/run_demo.sh start --tool claude
scripts/demo/single-agent-mail-wakeup/run_demo.sh manual-send
scripts/demo/single-agent-mail-wakeup/run_demo.sh inspect
scripts/demo/single-agent-mail-wakeup/run_demo.sh verify
scripts/demo/single-agent-mail-wakeup/run_demo.sh stop
```

Matrix run across both supported tools:

```bash
scripts/demo/single-agent-mail-wakeup/run_demo.sh matrix
```

## Verification Contract

Success means all of the following:

- gateway notifier evidence shows unread work was detected and processed
- the agent created the requested file under `outputs/<tool>/project/tmp/single-agent-mail-wakeup/`
- `houmao-mgr agents mail check --unread-only` reached zero actionable unread messages
- `houmao-mgr project mailbox messages list|get` corroborated the delivered message structurally

The demo does **not** treat project-mailbox `read` state as authoritative. Structural project-mailbox inspection is used only for canonical identity, folder, projection path, canonical path, sender, recipients, subject, body, and attachments.

## Failure Modes

- fixture auth bundle missing or incomplete
- project-easy specialist launch posture is not unattended
- gateway attach succeeds but notifier enable races; the demo retries a bounded number of times
- gateway wake-up never occurs
- the agent does not create the requested output file with the expected deterministic content
- `agents mail check --unread-only` never reaches zero

