# `single-agent-gateway-wakeup-headless/`

Supported runnable demo for the modern single-agent `houmao-mgr project easy` headless gateway wake-up workflow.

It shows the maintained headless flow from project creation through gateway notifier wake-up:

1. use one canonical demo-owned state root under `outputs/`
2. copy a fresh dummy project under `outputs/project/`
3. redirect Houmao overlay state into `outputs/overlay/` with `HOUMAO_PROJECT_OVERLAY_DIR` so runtime, jobs, mailbox, and project-easy state stay demo-local
4. preserve reusable overlay-backed specialist/auth/setup state across fresh runs while resetting run-local project, mailbox, runtime, jobs, logs, deliveries, and evidence
5. import the local Claude, Codex, or Gemini fixture auth bundle into that overlay and create or reuse one project-easy specialist
6. initialize the project mailbox, register the agent and operator addresses, launch one headless instance through `houmao-mgr project easy instance launch --headless`, attach a live gateway in a separate watchable tmux window, and enable mail-notifier polling
7. inject one filesystem-backed operator message
8. verify gateway notifier evidence, managed-agent headless last-turn or turn-artifact evidence, deterministic artifact creation under `project/tmp/`, actor-scoped unread completion, and structural project-mailbox visibility

## Supported Lanes

- `claude`
- `codex`
- `gemini`

## Output Layout

The demo owns one canonical output root under `outputs/`:

- `project/`: copied dummy project and visible worktree
- `overlay/`: redirected Houmao overlay selected through `HOUMAO_PROJECT_OVERLAY_DIR`, including `agents/`, `runtime/`, `jobs/`, `mailbox/`, `content/`, and `easy/`
- `registry/`: isolated shared-registry override kept local to the demo output root
- `control/`, `logs/`, `deliveries/`, `evidence/`: persisted demo artifacts

Fresh `start` runs reset the copied project plus overlay-local mailbox, runtime, jobs, logs, deliveries, and evidence while preserving reusable specialist/auth/setup state under `overlay/`.

Generated outputs are ignored through [outputs/.gitignore](outputs/.gitignore).

## Prerequisites

- `pixi`
- `tmux`
- `claude`, `codex`, or `gemini` for the selected lane
- local fixture auth bundles at:
  - `tests/fixtures/agents/tools/claude/auth/kimi-coding`
  - `tests/fixtures/agents/tools/codex/auth/yunwu-openai`
  - `tests/fixtures/agents/tools/gemini/auth/personal-a-default`

The demo fails early and names the missing fixture path when a required auth bundle is absent.

The canonical supported Gemini lane uses the OAuth-backed fixture at `tests/fixtures/agents/tools/gemini/auth/personal-a-default`. The runtime importer also accepts `tests/fixtures/agents/tools/gemini/auth/api-key-a-default` for manual variation, but the maintained demo contract validates the OAuth-backed unattended path.

## Commands

One-shot automatic run:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh auto --tool claude
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh auto --tool codex
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh auto --tool gemini
```

Stepwise workflow:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh start --tool claude
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh attach
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh watch-gateway --follow
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier status
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh send
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh inspect
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh verify
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh stop
```

During stepwise `start`, the demo keeps the managed agent in the demo-owned headless tmux session and attaches the gateway in a separate foreground auxiliary tmux window. `attach` re-enters that live tmux session for inspection, and `watch-gateway` reuses persisted gateway window metadata and live gateway status to print the gateway console without manual tmux discovery.

Additional stepwise controls:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier on --seconds 2
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier off
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier set-interval --seconds 5
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh send --body-file path/to/message.md
```

Matrix run across all supported tools:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh matrix
```

## Verification Contract

Success means all of the following:

- gateway notifier evidence shows unread work was detected and processed
- managed-agent headless detail reports a successful completed last turn and durable turn-artifact evidence is present
- the agent created the requested file under `outputs/project/tmp/single-agent-gateway-wakeup-headless/`
- `houmao-mgr agents mail check --unread-only` reached zero actionable unread messages
- `houmao-mgr project mailbox messages list|get` corroborated the delivered message structurally

The demo does **not** depend on parser-owned TUI posture. Headless runtime detail and durable turn artifacts are the canonical execution evidence for this pack.

The stepwise controls are for live observation and experimentation only. `inspect` and `verify` remain the persisted evidence/report surfaces, and `auto` remains the canonical unattended path. Normal operator usage does not require `--demo-output-dir` because follow-up commands resolve the active run from the canonical persisted state under `outputs/control/demo_state.json`.

## Failure Modes

- fixture auth bundle missing or incomplete
- project-easy specialist launch posture is not unattended
- the Gemini OAuth fixture is missing required `oauth_creds.json` content
- gateway attach succeeds but notifier enable races; the demo retries a bounded number of times
- the headless session never becomes available for gateway work
- gateway wake-up never records a successful completed headless turn
- the agent does not create the requested output file with the expected deterministic content
- `agents mail check --unread-only` never reaches zero
- a fresh run finds an active prior session that has not been stopped yet
