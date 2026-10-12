# codex TUI parsing campaign tooling (iteration 1)

Executable tooling for the debug campaign at
[`context/campaigns/debug/2026-10-12-codex-tui-parsing/`](../../../context/campaigns/debug/2026-10-12-codex-tui-parsing/).
It drives the iteration-1 state-matrix captures against codex-cli 0.162.1 and
replays them under the fallback detector (Arm A1), the maintained 0.144.x
profile (Arm A2), and a monkey-patched 0.162.x candidate. Production code under
`src/houmao/` stays untouched: candidate behavior is applied at runtime by
monkey patch only, and integration happens only after manual review of the
campaign's reports (user directive 2026-10-12).

Adapted from the kimi campaign tooling (`scripts/explore/kimi-code-tui-parsing/`);
the driver, spec loader, freeze, fixture, observer, and assertion contracts are
intentionally identical.

## Layout

| Path | Purpose |
| --- | --- |
| `run_session.py` | Session orchestrator: Boltons copy, delegated-style launch, 5 fps recording, tracker-blind op driving, freeze |
| `evaluate.py` | Promptfoo-contract assertion harness over frozen artifacts |
| `campaign_lib/spec.py` | Session YAML loading, `catalog_operation` resolution, `{{SAFE}}` expansion |
| `campaign_lib/fixture.py` | Boltons working-copy preparation (baseline tag, collection preflight, digests) |
| `campaign_lib/launch.py` | codex tmux launch per `houmao-dev-launch-agents` contract (pinned `CODEX_HOME`, model/effort flags) |
| `campaign_lib/drive.py` | Tracker-blind tmux driver with managed input-event logging |
| `campaign_lib/runtime_observer.py` | tmux/process liveness sampler (`runtime_observations.ndjson`) |
| `campaign_lib/freeze.py` | SHA-256 freeze gate (`capture/frozen-evidence.json`) |
| `campaign_lib/patches.py` | Candidate 0.162.x detector monkey patches (written after the gap analysis) |
| `campaign_lib/replay.py` | Arm A1/A2: baseline analyze subprocess + patched in-process analyze |
| `campaign_lib/esc_audit.py` | Arm B: OSC 133 / OSC `9;4` survival audit over frozen snapshots |
| `drivers/tui_driver.py` | Promptfoo Python-provider shim (`call_api`) over the same driver |
| `asserts/` | Promptfoo-contract assertion scripts per the iteration's `asserts/README.md` |

## Usage

```bash
# Session 1: lifecycle states (unattended bypass, fresh untrusted Boltons copy)
pixi run python scripts/explore/codex-tui-parsing/run_session.py \
  --spec context/campaigns/debug/2026-10-12-codex-tui-parsing/iterations/2026-10-12-plan-1-state-matrix-capture/session-1-lifecycle.yaml \
  --run-root tmp/houmao-dev-tui-testing/<run-id>

# Session 2: operator surfaces (as_is: -a untrusted -s read-only)
pixi run python scripts/explore/codex-tui-parsing/run_session.py \
  --spec context/campaigns/debug/2026-10-12-codex-tui-parsing/iterations/2026-10-12-plan-1-state-matrix-capture/session-2-operator-surfaces.yaml \
  --run-root tmp/houmao-dev-tui-testing/<run-id>

# After blind labeling (labels/labels.json + labels-manifest.json):
pixi run python scripts/explore/codex-tui-parsing/evaluate.py \
  --spec <same spec> --run-root <run-id> --replay-tags baseline-fallback baseline-0.144.x
```

## Boundaries

- Read-only: `src/houmao/`, `extern/orphan/codex`, `tests/fixtures/`, `openspec/`.
- Temporary state lives under `tmp/houmao-dev-tui-testing/<run-id>/` only.
- The codex home (`.codex/`) is the credential lane (`CODEX_HOME` pinned);
  `auth.json` and tokens are never read, copied, or embedded into artifacts.
  Session rollout/event files may be digested as Arm C evidence.
