# Passive-Server Parallel Validation Demo Pack

This pack implements the Step 7 migration validator from `context/design/future/distributed-agent-migration-path-greenfield.md`.

It answers one narrow question: can `houmao-server` and `houmao-passive-server` observe and control the same managed-agent runtime correctly when they share one runtime root, registry root, and jobs root?

Success looks like this:

- one demo-owned `houmao-server` and one demo-owned `houmao-passive-server` start on separate ports
- a shared locally launched interactive agent becomes visible on both authorities
- normalized identity, state, detail, and history parity checks pass
- a passive-server gateway prompt produces observable progress on both authorities
- a passive-server headless launch becomes visible from the old server
- stopping the shared interactive agent through the passive server removes it from both authorities
- `verify` writes `report.json` and `report.sanitized.json`, and the sanitized report matches `expected_report/report.json`

## Prerequisites

- `pixi`
- `git`
- `tmux`
- `claude` for `--provider claude_code`
- `codex` for `--provider codex`
- live credential material under the pack-owned `agents/brains/api-creds/...` tree

The pack is self-contained for tracked, non-secret launch inputs. It uses:

- pack-owned selectors under `agents/`
- tracked prompts and the copied project template under `inputs/`
- generated run state under `scripts/demo/passive-server-parallel-validation-demo-pack/outputs/`

## Implementation Idea

1. Run a fail-fast preflight against executables, ports, selector assets, and credentials.
2. Start one isolated old `houmao-server` and one isolated `houmao-passive-server`.
3. Point both authorities at the same shared runtime, registry, and jobs roots.
4. Launch a shared local interactive agent through the local managed-agent path.
5. Compare normalized managed-agent views across both authorities.
6. Submit a gateway prompt through the passive server and verify progress on both authorities.
7. Launch one passive headless agent and confirm old-server visibility for that same tracked agent.
8. Stop the shared interactive agent through the passive server, then stop both authorities.
9. Build and sanitize the final report and compare it to `expected_report/report.json`.

## Critical Inputs

The canonical tracked prompts are:

```text
shared_prompt.txt
Summarize the current validation target in one short sentence.

gateway_prompt.txt
Reply with one short sentence confirming the passive-server gateway validation prompt.

headless_prompt.txt
Reply with one short sentence confirming the passive-server headless validation launch.
```

The canonical tracked parameters are in `inputs/demo_parameters.json`:

```json
{
  "default_provider": "claude_code",
  "old_server_port": 9889,
  "passive_server_port": 9891
}
```

## Run The Workflow

### 1. Run preflight only

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/autotest/run_autotest.sh \
  --case parallel-preflight \
  --demo-output-dir /tmp/passive-server-parallel-preflight
```

This checks fixtures, ports, executables, and credentials without starting either authority.

### 2. Run the canonical unattended path

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh auto \
  --demo-output-dir /tmp/passive-server-parallel-auto
```

That command runs:

1. `start`
2. `inspect`
3. `gateway`
4. `headless`
5. `stop`
6. `verify`

Key success artifacts:

- `/tmp/passive-server-parallel-auto/control/demo_state.json`
- `/tmp/passive-server-parallel-auto/control/phases/inspect/result.json`
- `/tmp/passive-server-parallel-auto/control/phases/gateway/result.json`
- `/tmp/passive-server-parallel-auto/control/phases/headless/result.json`
- `/tmp/passive-server-parallel-auto/control/phases/stop/result.json`
- `/tmp/passive-server-parallel-auto/report.json`
- `/tmp/passive-server-parallel-auto/report.sanitized.json`

### 3. Run the same workflow stepwise

Start both authorities and the shared interactive agent:

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh start \
  --demo-output-dir /tmp/passive-server-parallel-stepwise \
  --provider claude_code \
  --old-server-port 9889 \
  --passive-server-port 9891
```

Inspect the shared interactive parity state:

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh inspect \
  --demo-output-dir /tmp/passive-server-parallel-stepwise
```

Exercise the passive gateway path:

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh gateway \
  --demo-output-dir /tmp/passive-server-parallel-stepwise
```

Launch the passive headless agent and verify old-server visibility:

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh headless \
  --demo-output-dir /tmp/passive-server-parallel-stepwise
```

Stop and verify:

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh stop \
  --demo-output-dir /tmp/passive-server-parallel-stepwise
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh verify \
  --demo-output-dir /tmp/passive-server-parallel-stepwise
```

### 4. Compare the sanitized report to the tracked expected snapshot

```bash
diff -u \
  scripts/demo/passive-server-parallel-validation-demo-pack/expected_report/report.json \
  /tmp/passive-server-parallel-auto/report.sanitized.json
```

### 5. Refresh the tracked expected snapshot intentionally

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/run_demo.sh verify \
  --demo-output-dir /tmp/passive-server-parallel-auto \
  --snapshot-report
```

## Autotest Cases

Use the harness when you want named cases with preserved logs and machine-readable result files:

```bash
scripts/demo/passive-server-parallel-validation-demo-pack/autotest/run_autotest.sh \
  --case parallel-all-phases-auto \
  --demo-output-dir /tmp/passive-server-parallel-autotest
```

Supported cases:

- `parallel-preflight`
- `parallel-all-phases-auto`

The harness preserves:

- result JSON under `<demo-output-dir>/control/autotest/`
- stdout/stderr/command logs under `<demo-output-dir>/logs/autotest/<case-id>/`

## Troubleshooting

- If preflight fails, inspect `control/autotest/case-parallel-preflight.preflight.json` first.
- If one authority never becomes healthy, inspect `logs/old_server/` and `logs/passive_server/`.
- If inspect parity fails, inspect `control/phases/inspect/` for both raw and normalized snapshots.
- If gateway validation fails, inspect `control/phases/gateway/`.
- If headless visibility fails, inspect `control/phases/headless/`.
- If cleanup fails, inspect `control/phases/stop/result.json`.

## Appendix

| Name | Value | Explanation |
| --- | --- | --- |
| `agent_profile` | `server-api-smoke` | Native selector resolved from the pack-owned `agents/` tree. |
| Default provider | `claude_code` | Default CLI provider if the caller does not override `--provider`. |
| Default old-server port | `9889` | Pack default for the owned `houmao-server`. |
| Default passive-server port | `9891` | Pack default for the owned `houmao-passive-server`. |
| History limit | `20` | Default `/managed-history` limit used during parity and progress checks. |
| Output root | `scripts/demo/passive-server-parallel-validation-demo-pack/outputs/` | Pack-local generated run and autotest artifact root. |
| Snapshot path | `expected_report/report.json` | Sanitized golden report used by `verify`. |
