# kimi-code TUI parsing campaign tooling (iteration 1)

Executable tooling for the debug campaign at
[`context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/`](../../../context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/).
It drives the iteration-1 state-matrix captures against kimi-code 2.1.1 and
replays them under the current detector and a monkey-patched 2.1.x candidate.
Production code under `src/houmao/` stays untouched: candidate behavior is
applied at runtime by monkey patch only.

## Layout

| Path | Purpose |
| --- | --- |
| `run_session.py` | Session orchestrator: Boltons copy, delegated-style launch, 5 fps recording, tracker-blind op driving, freeze |
| `evaluate.py` | Promptfoo-contract assertion harness over frozen artifacts |
| `campaign_lib/spec.py` | Session YAML loading, `catalog_operation` resolution, `{{SAFE}}` expansion |
| `campaign_lib/fixture.py` | Boltons working-copy preparation (baseline tag, collection preflight, digests) |
| `campaign_lib/launch.py` | kimi tmux launch per `houmao-dev-launch-agents` contract |
| `campaign_lib/drive.py` | Tracker-blind tmux driver with managed input-event logging |
| `campaign_lib/runtime_observer.py` | tmux/process liveness sampler (`runtime_observations.ndjson`) |
| `campaign_lib/freeze.py` | SHA-256 freeze gate (`capture/frozen-evidence.json`) |
| `campaign_lib/patches.py` | Candidate 2.1.x detector + parser monkey patches (`kimi_2_1_x_patch`) |
| `campaign_lib/replay.py` | Arm A: baseline analyze subprocess + patched in-process analyze |
| `campaign_lib/esc_audit.py` | Arm B: OSC 133 / OSC `9;4` survival audit over frozen snapshots |
| `drivers/tui_driver.py` | Promptfoo Python-provider shim (`call_api`) over the same driver |
| `asserts/` | Promptfoo-contract assertion scripts per the iteration's `asserts/README.md` |

## Usage

```bash
# Session 1: lifecycle states (unattended --auto, untrusted workdir)
pixi run python scripts/explore/kimi-code-tui-parsing/run_session.py \
  --spec context/campaigns/debug/2026-10-10-kimi-code-tui-parsing/iterations/2026-10-10-plan-1-state-matrix-capture/session-1-lifecycle.yaml \
  --run-root tmp/houmao-dev-tui-testing/<run-id>

# After blind labeling (labels/labels.json + labels-manifest.json):
pixi run python scripts/explore/kimi-code-tui-parsing/evaluate.py \
  --spec <same spec> --run-root <run-id> --replay-tags baseline candidate-2.1.x
```

Arm A replay and the Arm B audit run through `campaign_lib.replay.run_arm_a`
and `campaign_lib.esc_audit.run_arm_b` (invoked by the campaign execution
log, see the iteration evidence docs).

## Boundaries

- Read-only: `src/houmao/`, `extern/orphan/kimi-code`, `tests/fixtures/`.
- Temporary state lives under `tmp/houmao-dev-tui-testing/<run-id>/` only.
- The kimi home (`.kimi-code/`) receives at most a workspace-trust record for
  session 2's trusted workdir, recorded in the run summary.
