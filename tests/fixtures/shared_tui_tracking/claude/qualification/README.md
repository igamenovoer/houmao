# Claude Code TUI Qualification Fixtures

Frozen 5 fps recordings of Claude Code 2.1.296 with blind-authored ground-truth
labels, promoted from the 2026-10-12 debug campaign
(`context/campaigns/debug/2026-10-12-claude-code-tui-parsing/`). The
qualification replay test
(`tests/unit/shared_tui_tracking/test_claude_2_1_296_qualification.py`) replays
these sessions through the production `analyze_terminal_record` path and
compares the two admission booleans against the frozen labels.

## Provenance

| Fixture | Campaign run root (frozen, gitignored) | Recording SHA-256 | Labels SHA-256 |
| --- | --- | --- | --- |
| `session1_lifecycle/` | `tmp/houmao-dev-tui-testing/2026-10-12-claude-session1-lifecycle` | `0928bfc4e70273b4…` (full digest in `labels-manifest.json`) | `b8744344a3848610…` (full digest in `labels-manifest.json`) |
| `session2_operator_surfaces_002/` | `tmp/houmao-dev-tui-testing/2026-10-12-claude-session2-operator-surfaces-002` | `d4ab23e91832d3fd…` (full digest in `labels-manifest.json`) | `8e3b568c0f2126fa…` (full digest in `labels-manifest.json`) |
| `session2_operator_surfaces/` | `tmp/houmao-dev-tui-testing/2026-10-12-claude-session2-operator-surfaces` | `cd1ebd7b329f0b70…` (full digest in `labels-manifest.json`) | `d1fcfa8082cff5ca…` (full digest in `labels-manifest.json`) |

Each fixture directory carries the recorder `manifest.json`, the managed input
events (`input_events.ndjson`), the gzipped pane snapshots
(`pane_snapshots.ndjson.gz`), the frozen blind labels (`labels.json`), and the
label provenance manifest (`labels-manifest.json`, blind-labeling declaration
and digests). Labels were authored from raw snapshots, runtime observations,
and drive events only — no detector or tracker output was inspected before or
during labeling.

Labels were re-frozen on 2026-10-13 after post-repair boundary corrections
authored in `author_labels.py` with per-row notes (recorded in the campaign
iteration plan): (a) session 1 picker span starts at s001511 (fully rendered)
and ends at s001524, with s001525-s001532 labeled `active` — the preempted turn
resumes streaming after the picker closes until the queued `/model`
interruption lands at s001533; (b) session 1 draft-leg boundaries move to the
composer evidence (editing s000067-s000092, ready s000093-s000097); (c)
session 1's s000512-s000513 `editing_success` span dissolves into
`ready_success` (composer verifiably empty); (d) session 2-002's editing span
starts at s000067 (placeholder still renders at s000066); (e) session 2-001
gains an editing frame at s000066 (full command draft already in the
composer).

## Coverage notes (from the label manifests and the campaign repair report)

- Session 1 covers cold start with the workspace-trust dialog (renders even
  under `--dangerously-skip-permissions` for an untrusted workdir), prompt
  turns, queued follow-ups, an Esc interruption, a silent Esc abort with a
  restored composer draft, a `/model` picker that preempts and resumes a turn,
  and session exit.
- Session 2-002 covers operator surfaces under the replicated launcher lane
  minus bypass: trust dialog, `Do you want to …` approval panels with their
  `Esc to cancel · Tab to amend` footers (approve and deny paths), the model
  picker, and editing spans; deterministic approvals come from
  `permissions.ask` rules.
- Session 2-001 covers 2.1.296's default auto permission mode: the same
  operator actions render as auto-approved surfaces instead of approval
  panels, plus the silent-abort and draft-restore spans.
- Completion docks render `✻ <Verb> for <Nm Ns> · done <time>` from an
  eight-verb set (`Baked`, `Brewed`, `Churned`, `Cogitated`, `Cooked`,
  `Crunched`, `Sautéed`, `Worked`) and persist in the captured tail for every
  completed turn; a completed turn without a visible dock is the recorded
  qualification boundary for the silent-abort inference.
- Residual label/replay divergence classes (not gated): success settle-timer
  heads (1.0 s settle = 5 samples per success span) and submit-frame Enter
  event ordering.
