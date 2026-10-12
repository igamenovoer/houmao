# claude code TUI parsing campaign tooling (iteration 1)

Executable tooling for the debug campaign at
[`context/campaigns/debug/2026-10-12-claude-code-tui-parsing/`](../../../context/campaigns/debug/2026-10-12-claude-code-tui-parsing/).
It drives the iteration-1 state-matrix captures against Claude Code 2.1.296
through the OpenLux relay launcher (`claude-openlux-0.5x`, sonnet model per
the cost directive) and replays them under the maintained 2.1.x profile
(Arm A1, today's resolution) and the fallback detector (Arm A2, control).
Production code under `src/houmao/` stays untouched: candidate behavior is
applied at runtime by monkey patch only after the gap analysis, and
integration happens only after manual review of the campaign's reports.

Adapted from the codex campaign tooling (`scripts/explore/codex-tui-parsing/`);
the driver, spec loader, freeze, fixture, observer, and assertion contracts
are intentionally identical.

## Layout

| Path | Purpose |
| --- | --- |
| `run_session.py` | Session orchestrator: Boltons copy, openlux-lane launch, 5 fps recording, tracker-blind op driving, freeze |
| `run_analysis.py` | Arm A replays + Arm B escape audit + Arm C transcript inventory (after labels freeze) |
| `evaluate.py` | Promptfoo-contract assertion harness over frozen artifacts |
| `campaign_lib/spec.py` | Session YAML loading, `catalog_operation` resolution, `{{SAFE}}` expansion |
| `campaign_lib/fixture.py` | Boltons working-copy preparation (baseline tag, collection preflight, digests) |
| `campaign_lib/launch.py` | claude tmux launch through the OpenLux lane (launcher as-is or env lane minus bypass) |
| `campaign_lib/drive.py` | Tracker-blind tmux driver with managed input-event logging |
| `campaign_lib/runtime_observer.py` | tmux/process liveness sampler (`runtime_observations.ndjson`) |
| `campaign_lib/freeze.py` | SHA-256 freeze gate (`capture/frozen-evidence.json`) |
| `campaign_lib/replay.py` | Arm A1/A2: baseline analyze subprocess per observed version |
| `campaign_lib/esc_audit.py` | Arm B: OSC 133 / OSC `9;4` survival audit over frozen snapshots |
| `campaign_lib/event_store.py` | Arm C: `~/.claude/projects/` transcript JSONL inventory |
| `drivers/tui_driver.py` | Promptfoo Python-provider shim (`call_api`) over the same driver |
| `asserts/` | Promptfoo-contract assertion scripts per the iteration's `asserts/README.md` |

## Usage

```bash
# Session 1: lifecycle states (openlux launcher as-is, fresh untrusted Boltons copy)
pixi run python scripts/explore/claude-code-tui-parsing/run_session.py \
  --spec context/campaigns/debug/2026-10-12-claude-code-tui-parsing/iterations/2026-10-12-plan-1-state-matrix-capture/session-1-lifecycle.yaml \
  --run-root tmp/houmao-dev-tui-testing/<run-id>

# Session 2: operator surfaces (openlux env lane minus --dangerously-skip-permissions)
pixi run python scripts/explore/claude-code-tui-parsing/run_session.py \
  --spec context/campaigns/debug/2026-10-12-claude-code-tui-parsing/iterations/2026-10-12-plan-1-state-matrix-capture/session-2-operator-surfaces.yaml \
  --run-root tmp/houmao-dev-tui-testing/<run-id>

# After blind labeling (labels/labels.json + labels-manifest.json):
pixi run python scripts/explore/claude-code-tui-parsing/run_analysis.py --run-root <run-id>
pixi run python scripts/explore/claude-code-tui-parsing/evaluate.py --spec <same spec> --run-root <run-id>
```

## Boundaries

- Read-only: `src/houmao/`, `tests/fixtures/`, `openspec/`.
- Temporary state lives under `tmp/houmao-dev-tui-testing/<run-id>/` only.
- The OpenLux lane is the credential lane: `~/.local/bin/openlux-api-key` and
  `~/.claude/.credentials.json` are never read, copied, or embedded into
  artifacts. Session transcripts under `~/.claude/projects/` are read-only
  Arm C oracle inputs (structure and timestamps only, never payloads).
- Cost discipline (user directive 2026-10-12): `--model sonnet` everywhere,
  verified in-TUI at session start; exactly two planned sessions.
