# Evidence: session 2 operator-surfaces capture (codex 0.162.1)

Date: 2026-10-12. Iteration: [plan 1](../iterations/2026-10-12-plan-1-state-matrix-capture.md). Run root: `tmp/houmao-dev-tui-testing/2026-10-12-codex-session2-operator-surfaces-002` (attempt 002; launch attempt 001 failed before recording because codex 0.162.1 removed the `untrusted` approval value — see plan Corrections).

## Environment and Identity

Same as [session 1](2026-10-12-session1-lifecycle-capture.md) except posture: **as_is** launch `codex -a on-request -s read-only -m gpt-6.1-sol -c model_reasoning_effort="medium" -C <workdir>` so approval surfaces render deterministically (out-of-sandbox write for the command approval; workspace write for the edit approval).

## Frozen Evidence

| File | SHA-256 (prefix) | Rows |
| --- | --- | --- |
| `capture/recording/pane_snapshots.ndjson` | `e7d5d54d8d2a5acf` | 437 samples |
| `labels/labels.json` | `a0487680b1f4ce9c` | 12 label spans, complete coverage |

Recording window 06:19:42–06:21:21 UTC. `run_tainted=false`. `stop_reason` is the same recorder post-teardown quirk (`no such session` while unsetting the live-state env after the session ended); all bound files complete. Labels frozen 06:27:36 UTC before any replay (G3 holds).

## Captured State Coverage (G2)

| Family | Span samples | Rendering (exact 0.162.1 text) |
| --- | --- | --- |
| startup_modal | 50 | trust screen, as session 1 (as_is launch, untrusted git-repo copy) |
| warnings_screen | 13 | F2 overlay: `Warnings · 1 of 2 · Startup` + `k keep & next · esc dismiss & close · ^o copy · ←/→ warning · ↓ scroll`; composer fully replaced |
| active | 157 | two pre-approval thinking turns; 1-sample status-row flickers stay active |
| approval_modal | 28 | both legs raised the **command** form: `Would you like to run the following command?` + `Environment: local` + `Reason: …` + `$ <command>` + `› 1. Yes, proceed (y) / 2. Yes, and don't ask again… (p) / 3. No, and tell Codex what to do differently (esc)` + `Press enter to confirm or esc to cancel`. The edit leg arrived as a `printf … > docs/…` shell command; the `…make the following edits?` form was not captured (coverage gap) |
| model_picker | 13 | `/model` popup: `Select Model and Effort` + numbered model rows + `enter select · esc back` |
| ready | 176 | post-denial turns end with `✗ You canceled the request…` + `• Failed (exit 1)` + the same `■ Conversation interrupted` notice; labeled `last_turn_result=interrupted` |

Coverage gaps (declared, per plan): edits-form approval, `Would you like to grant these permissions?`, `Would you like to send input to the existing terminal?` (needs a background terminal session), error/retry cells (cannot be forced reliably).

## Detector Scores (booleans first)

| Arm | accepting_input | ready_posture | false-ready | false-busy | Notes |
| --- | --- | --- | --- | --- | --- |
| A1 fallback | 0.826 | 0.764 | 68 | 22 | every modal family mismatches (28/28, 13/13, 13/13, 50/50) |
| A2 0.144.x override | 0.826 | 0.815 | 68 | 0 | same modal misses (approval posture blocked but `turn_phase` semantics off) |
| Candidate 0.162.x | **1.0000** | **1.0000** | **0** | **0** | only `last_turn_result` seam mismatches in ready spans (16/176) |

## Arm B (escape audit)

Zero OSC in 437 samples (`osc_any=0`); SGR 21 195. Same conclusion as session 1.

## Arm C (rollout inventory)

1 rollout file, 7 lifecycle events (`task_started`/`task_complete`/`turn_aborted` for the two approval turns + startup); denial turns record `turn_aborted` — the oracle distinguishes operator denial from completion.
