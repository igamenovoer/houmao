# Case: Unattended Full Run

This interactive guide walks the same canonical path as the automatic case, but it is designed for agent-driven execution while you watch the live demo. It assumes you want to inspect the headless tmux sessions directly instead of treating the run as a black box.

Default demo output root: `.agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output`

## Step 1. Confirm prerequisites

Action:

```bash
pixi --version
git --version
tmux -V
command -v claude
command -v codex
```

Expected outcome:

- all commands succeed

What to look for:

- missing local tool executables
- missing `PATH` setup for `claude` or `codex`

Decision point:

- if any command fails, stop and fix the local environment before continuing

## Step 2. Run pack-local preflight checks

Action:

```bash
pixi run python \
  scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/helpers/check_demo_preflight.py \
  --repo-root "$(pwd)" \
  --parameters scripts/demo/mail-ping-pong-gateway-demo-pack/inputs/demo_parameters.json
```

Expected outcome:

- preflight succeeds without starting the run yet

What to look for:

- no missing fixture, config, or credential-root errors
- both participant roles are present in the printed summary

Decision point:

- if preflight fails, stop and fix the reported prerequisite before starting the run
- if preflight succeeds, continue to an explicit `start`

## Step 3. Start the demo without kickoff

Action:

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh start \
  --demo-output-dir .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

Expected outcome:

- the command succeeds
- it prints the selected `output_root` and `api_base_url`

What to look for:

- both headless participants launch successfully
- no startup error from the demo-owned `houmao-server`

Decision point:

- if `start` fails, stop and investigate before attempting to watch tmux output

## Step 4. Summarize the persisted state

Action:

```bash
pixi run python \
  scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/helpers/print_demo_state_summary.py \
  .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output/control/demo_state.json
```

Expected outcome:

- the summary prints initiator/responder tool, role name, tracked agent id, tmux session name, recipe path, and working directory

What to look for:

- both tmux session names are non-empty
- both recipe paths point at the dedicated ping-pong recipes

Decision point:

- if the state file is missing or incomplete, stop and investigate startup

## Step 5. Refresh inspect artifacts and validate launch posture

Action:

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh inspect \
  --demo-output-dir .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

```bash
pixi run python \
  scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/helpers/check_launch_posture.py \
  .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output/control/inspect.json
```

Expected outcome:

- the inspect artifact is refreshed
- launch posture validation succeeds for both roles

What to look for:

- tracked recipe, built brain manifest, and live launch request all show `unattended`
- `launch_policy_applied=true` for both roles

Decision point:

- if launch posture validation fails, stop before kickoff

## Step 6. Attach to the initiator tmux session

Action:

```bash
bash scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/helpers/print_tmux_role_snapshot.sh \
  .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output/control/demo_state.json \
  initiator \
  120
```

Expected outcome:

- the helper prints recent pane output plus an attach hint

What to look for:

- the pane is not blank
- once a turn becomes active, you can see rolling CLI output rather than a frozen screen

Decision point:

- if the pane stays blank or frozen during active work, stop and investigate the headless tmux watch surface

## Step 7. Attach to the responder tmux session

Action:

```bash
bash scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/helpers/print_tmux_role_snapshot.sh \
  .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output/control/demo_state.json \
  responder \
  120
```

Expected outcome:

- the helper prints recent pane output plus an attach hint

What to look for:

- the pane is live and watchable
- once later turns wake, you can see rolling CLI output from the responder as well

Decision point:

- if the pane stays blank or frozen during active work, stop and investigate before trusting the watch flow

## Step 8. Submit kickoff

Action:

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh kickoff \
  --demo-output-dir .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

Expected outcome:

- the kickoff request is accepted
- the initiator begins the thread

What to look for:

- the initiator pane shows visible work instead of remaining blank

Decision point:

- if kickoff fails, stop and investigate before waiting

## Step 9. Watch active turns

Action:

- if you want a live view from another terminal, attach directly with:

```bash
tmux attach-session -t <tmux_session_name>
```

Expected outcome:

- the initiator sends round 1
- later turns wake through the gateway rather than repeated operator prompts
- both panes remain watchable while active turns are running

What to look for:

- rolling JSON or CLI progress in the active pane
- visible errors if a turn fails

Decision point:

- if the panes stay blank or frozen during active work, stop and investigate the tmux watch surface
- if the run looks healthy, continue to bounded wait

## Step 10. Wait, inspect, verify, and stop

Action:

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh wait \
  --demo-output-dir .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh inspect \
  --demo-output-dir .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh verify \
  --demo-output-dir .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/run_demo.sh stop \
  --demo-output-dir .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

Expected outcome:

- `wait` completes without timeout
- `verify` passes
- `stop` tears down the managed agents and server while keeping artifacts

What to look for:

- the final report reflects one thread, ten messages, and eleven completed turns

Decision point:

- if any step fails, inspect the preserved control artifacts before retrying

## Step 11. Inspect final artifacts

Action:

```bash
cat .agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output/control/autotest/case-unattended-full-run.result.json
```

Expected outcome:

- the case result shows `passed` or `failed`
- it points to the preserved inspect, report, sanitized report, and tmux snapshot artifacts

What to look for:

- `passed` only when launch posture, wait, inspect, verify, and stop all succeeded
- on failure, a concrete reason and preserved evidence paths

Decision point:

- if the result is `failed`, use the preserved artifacts to investigate the next blocker
