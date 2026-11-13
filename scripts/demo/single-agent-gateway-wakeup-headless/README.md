# `single-agent-gateway-wakeup-headless/`

Supported runnable demo for the modern single-agent `houmao-mgr project easy` headless gateway wake-up workflow.

It shows the maintained headless flow from project creation through gateway notifier wake-up:

1. use one canonical demo-owned state root under `outputs/`
2. copy a fresh dummy project under `outputs/project/`
3. redirect Houmao overlay state into `outputs/overlay/` with `HOUMAO_PROJECT_OVERLAY_DIR` so runtime, jobs, mailbox, and project-easy state stay demo-local
4. preserve reusable overlay-backed specialist/auth/setup state across fresh runs while resetting run-local project, mailbox, runtime, jobs, logs, deliveries, and evidence
5. import the local Claude or Codex fixture auth bundle into that overlay and create or reuse one project-easy specialist
6. initialize the project mailbox, register the agent and operator addresses, launch one headless instance through `houmao-mgr project easy instance launch --headless`, attach a live gateway in a separate watchable tmux window, and enable mail-notifier polling
7. inject one filesystem-backed operator message
8. verify gateway notifier evidence, managed-agent headless last-turn or turn-artifact evidence, deterministic artifact creation under `project/tmp/`, actor-scoped unread completion, and structural project-mailbox visibility

## Supported Lanes

- `claude`
- `codex`

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
- `claude` or `codex` for the selected lane
- an explicitly prepared external credential source and local parameter file.

Prepare credentials with `pixi run python scripts/agents/test-fixtures/fixture.py prepare --case cloud-api --client TOOL --model MODEL --env-file .env` (Kimi also needs `--context-window TOKENS`). Select `self-hosted` for a compatible local API or explicitly imported native-login state separately. Use only the returned external run-owned credential inputs and external demo outputs. See [the fixture helper](../../agents/test-fixtures/README.md).

Copy `inputs/demo_parameters.json` to a private external file and set the selected tool's `auth_fixture_dir` to `/external/prepared-run/assets/tools/TOOL/auth/default`. The checked-in paths are placeholders. Pass that file using `--parameters` and set `--demo-output-dir` to a private external directory for start/auto and follow-up commands. Codex uses the generic `api-compatible` Responses setup.

## Commands

One-shot automatic run:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh auto --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json --tool claude
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh auto --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json --tool codex
```

Stepwise workflow:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh start --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json --tool claude
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh attach --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh watch-gateway --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json --follow
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json status
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh ag-ui-smoke --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh send --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh inspect --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh verify --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh stop --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json
```

During stepwise `start`, the demo keeps the managed agent in the demo-owned headless tmux session and attaches the gateway in a separate foreground auxiliary tmux window. `attach` re-enters that live tmux session for inspection, and `watch-gateway` reuses persisted gateway window metadata and live gateway status to print the gateway console without manual tmux discovery.

Additional stepwise controls:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json on --seconds 2
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json off
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh notifier --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json set-interval --seconds 5
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh send --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json --body-file path/to/message.md
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh ag-ui-smoke --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json --abort-after-run-start
```

The AG-UI text smoke belongs in this demo pack because the pack already owns the maintained headless launch, gateway attach, isolated output root, fixture auth-bundle import, and cleanup flow. `ag-ui-smoke` posts AG-UI `RunAgentInput` JSON to the live per-agent gateway `POST /v1/ag-ui/runs` route, records stream events and durable gateway request state under `outputs/evidence/`, and verifies that stream abort does not enqueue an interrupt request when `--abort-after-run-start` is used.

Matrix run across all supported tools:

```bash
scripts/demo/single-agent-gateway-wakeup-headless/run_demo.sh matrix --demo-output-dir /external/single-agent-gateway-wakeup-headless --parameters /external/single-agent-gateway-wakeup-headless-parameters.json
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
- gateway attach succeeds but notifier enable races; the demo retries a bounded number of times
- the headless session never becomes available for gateway work
- gateway wake-up never records a successful completed headless turn
- the agent does not create the requested output file with the expected deterministic content
- `agents mail check --unread-only` never reaches zero
- a fresh run finds an active prior session that has not been stopped yet

Prepared inputs supply both credentials and the selected setup/model. Import runs in-process, and credential diagnostics redact key values. The demo copies the prepared setup through the existing tool surface before specialist creation; credential-owned env remains separate from runtime env. New live credential imports reject checkout-local output roots.
