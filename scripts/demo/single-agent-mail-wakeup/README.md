# `single-agent-mail-wakeup/`

Supported runnable demo for the modern single-agent `houmao-mgr project easy` gateway wake-up workflow.

It shows the maintained TUI flow from project creation through gateway notifier wake-up:

1. use one canonical demo-owned state root under `outputs/`
2. copy a fresh dummy project under `outputs/project/`
3. redirect Houmao overlay state into `outputs/overlay/` with `HOUMAO_PROJECT_OVERLAY_DIR` so runtime, jobs, and mailbox state stay demo-local under that overlay
4. preserve reusable project-easy specialist state under that overlay across fresh runs
5. import the local Claude or Codex fixture auth bundle into that overlay and create or reuse one project-easy specialist
6. initialize the project mailbox, register the agent and operator addresses, attach a live gateway, and enable mail-notifier polling
7. inject one filesystem-backed operator message
8. verify artifact creation under `project/tmp/`, actor-scoped unread completion through `agents mail check --unread-only`, and structural project-mailbox visibility

## Supported Lanes

- `claude`
- `codex`

This demo is intentionally TUI-only. It does not claim headless or mixed-mode support.

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
- `claude` for the Claude lane or `codex` for the Codex lane
- an explicitly prepared external credential source and local parameter file.

Prepare credentials with `pixi run python scripts/agents/test-fixtures/fixture.py prepare --case cloud-api --client TOOL --model MODEL --env-file .env` (Kimi also needs `--context-window TOKENS`). Select `self-hosted` for a compatible local API or explicitly imported native-login state separately. Use only the returned external run-owned credential inputs and external demo outputs. See [the fixture helper](../../agents/test-fixtures/README.md).

Copy `inputs/demo_parameters.json` to a private external file and set the selected tool's `auth_fixture_dir` to `/external/prepared-run/assets/tools/TOOL/auth/default`. The checked-in paths are placeholders. Pass that file using `--parameters` and set `--demo-output-dir` to a private external directory for start/auto and follow-up commands. Codex uses the generic `api-compatible` Responses setup.

## Commands

One-shot automatic run:

```bash
scripts/demo/single-agent-mail-wakeup/run_demo.sh auto --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json --tool claude
scripts/demo/single-agent-mail-wakeup/run_demo.sh auto --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json --tool codex
```

Stepwise workflow:

```bash
scripts/demo/single-agent-mail-wakeup/run_demo.sh start --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json --tool claude
scripts/demo/single-agent-mail-wakeup/run_demo.sh attach --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json
scripts/demo/single-agent-mail-wakeup/run_demo.sh watch-gateway --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json --follow
scripts/demo/single-agent-mail-wakeup/run_demo.sh notifier --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json status
scripts/demo/single-agent-mail-wakeup/run_demo.sh send --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json
scripts/demo/single-agent-mail-wakeup/run_demo.sh inspect --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json
scripts/demo/single-agent-mail-wakeup/run_demo.sh verify --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json
scripts/demo/single-agent-mail-wakeup/run_demo.sh stop --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json
```

During stepwise `start`, the demo attaches the gateway in a foreground auxiliary tmux window while leaving the agent TUI in the primary agent window. `attach` re-enters the live agent session, and `watch-gateway` prints the gateway console by polling that auxiliary tmux window so the operator does not need to inspect tmux window metadata manually.

Additional stepwise controls:

```bash
scripts/demo/single-agent-mail-wakeup/run_demo.sh notifier --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json on --seconds 2
scripts/demo/single-agent-mail-wakeup/run_demo.sh notifier --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json off
scripts/demo/single-agent-mail-wakeup/run_demo.sh notifier --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json set-interval --seconds 5
scripts/demo/single-agent-mail-wakeup/run_demo.sh send --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json --body-file path/to/message.md
```

Matrix run across both supported tools:

```bash
scripts/demo/single-agent-mail-wakeup/run_demo.sh matrix --demo-output-dir /external/single-agent-mail-wakeup --parameters /external/single-agent-mail-wakeup-parameters.json
```

## Verification Contract

Success means all of the following:

- gateway notifier evidence shows unread work was detected and processed
- the agent created the requested file under `outputs/project/tmp/single-agent-mail-wakeup/`
- `houmao-mgr agents mail check --unread-only` reached zero actionable unread messages
- `houmao-mgr project mailbox messages list|get` corroborated the delivered message structurally

The demo does **not** treat project-mailbox `read` state as authoritative. Structural project-mailbox inspection is used only for canonical identity, folder, projection path, canonical path, sender, recipients, subject, body, and attachments.

The new stepwise controls are for live observation and experimentation only. `inspect` and `verify` remain the persisted evidence/report surfaces, and `auto` remains the canonical unattended path. Normal operator usage does not require `--demo-output-dir` because follow-up commands resolve the active run from the canonical persisted state under `outputs/control/demo_state.json`.

## Failure Modes

- fixture auth bundle missing or incomplete
- project-easy specialist launch posture is not unattended
- gateway attach succeeds but notifier enable races; the demo retries a bounded number of times
- gateway wake-up never occurs
- the agent does not create the requested output file with the expected deterministic content
- `agents mail check --unread-only` never reaches zero
- a fresh run finds an active prior session that has not been stopped yet

Prepared inputs supply both credentials and the selected setup/model. Import runs in-process, and credential diagnostics redact key values. The demo copies the prepared setup through the existing tool surface before specialist creation; credential-owned env remains separate from runtime env. New live credential imports reject checkout-local output roots.
