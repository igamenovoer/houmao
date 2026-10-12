# Codex TUI Qualification Fixtures

Frozen 5 fps recordings of codex-cli 0.162.1 with blind-authored ground-truth
labels, promoted from the 2026-10-12 debug campaign
(`context/campaigns/debug/2026-10-12-codex-tui-parsing/`). The qualification
replay test (`tests/unit/shared_tui_tracking/test_codex_0_162_x_qualification.py`)
replays these sessions through the production `analyze_terminal_record` path
and compares the two admission booleans against the frozen labels.

## Provenance

| Fixture | Campaign run root (frozen, gitignored) | Recording SHA-256 | Labels SHA-256 |
| --- | --- | --- | --- |
| `session1_lifecycle/` | `tmp/houmao-dev-tui-testing/2026-10-12-codex-session1-lifecycle-002` | `55844e2e734a0219d8a7b3d9b90ffaa635d850e6e2b4be4410d1ac557194cc5f` | `6fac0c847f73bb3bd46fd6ac6ea507389d47ae4a5930dced219078d10c0a3e5f` |
| `session2_operator_surfaces/` | `tmp/houmao-dev-tui-testing/2026-10-12-codex-session2-operator-surfaces-002` | `e7d5d54d8d2a5acf…` (full digest in `labels-manifest.json`) | `a0487680b1f4ce9c…` (full digest in `labels-manifest.json`) |

Each fixture directory carries the recorder `manifest.json`, the managed input
events (`input_events.ndjson`), the gzipped pane snapshots
(`pane_snapshots.ndjson.gz`), the frozen blind labels (`labels.json`), and the
label provenance manifest (`labels-manifest.json`, blind-labeling declaration
and digests). Labels were authored from raw snapshots, runtime observations,
and drive events only — no detector or tracker output was inspected before or
during labeling.

## Coverage notes (from the label manifest)

- Session 1 covers cold start, prompt turns, a mid-busy queued follow-up
  (steer-merged), an Esc interruption, a `/compact` maintenance turn, and
  session exit; the single-sample `tui_down` (codex resume hint) is recorded
  as partial coverage.
- Session 2 covers operator surfaces: workspace-trust screen, model picker,
  warnings screen, approval denial, and editing spans.
- The queued-echo collapse window (`+ N lines (^t to expand)`) is a documented
  single-snapshot blind spot: pending input reads `no` there by design.
