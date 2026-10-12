# KQ-2: Can the claude session transcript store serve as the state oracle?

Status: answered 2026-10-12 (offline-oracle feasibility confirmed; there is no live channel to test). Iteration owner: [iteration 1](../iterations/2026-10-12-plan-1-state-matrix-capture.md) (Arm C). Evidence: [session 1](../evidences/2026-10-12-session1-lifecycle-capture.md) + [session 2](../evidences/2026-10-12-session2-operator-surfaces-capture.md) Arm C sections.

## Opening Statement

Claude Code writes a live session transcript as JSONL under `~/.claude/projects/<workdir-slug>/` while the TUI runs. Claude ships no app-server or attach protocol (the codex KQ-2 live-attach lane has no claude equivalent), so this question is strictly post-hoc: if the transcript carries turn lifecycle and outcome records with usable timestamps, it can act as an independent ground-truth oracle for validating text-scraping repairs (Arms A) and for cross-checking blind labels. The launcher does not isolate `CLAUDE_CONFIG_DIR`, so transcripts land in the real `~/.claude/projects/`; they are read-only oracle inputs under the credential-hygiene rule.

## Critical Propositions

### P2.1 Event coverage

The transcript JSONL distinguishes, at minimum: user prompt submitted, assistant turn started/completed, tool call dispatched/finished, interruption, and approval request/resolution (session 2) — the events that flip the two user-facing booleans.

### P2.2 Timestamp alignment

Transcript records carry timestamps that align to labeled spans within the labeling tolerance the codex campaign demonstrated for rollouts (≤0.5 s at turn seams). Records are written promptly enough that post-hoc alignment is unambiguous at 5 fps sampling.

### P2.3 Fidelity vs surface truth

Transcript-derived turn boundaries agree with surface-derived blind labels at every driven turn seam: a transcript "turn complete" never co-occurs with a surface that still blocks submission, and a submitted-during-busy prompt is distinguishable from an immediately-processed one. Known risk: the relay (OpenLux) may add latency that shows in neither transcript nor surface the same way; mismatches are recorded, not smoothed over.

## Answer / Resolution

Answered by iteration 1's Arm C (post-hoc transcript inspection; inventories in the evidence docs):

- **P2.1 — confirmed for lifecycle.** The transcript carries `user` (prompt submissions), `assistant` (turn output), `system` records with subtype `turn_duration` (turn completion, one per docked turn: 4 in session 1), `queue-operation` (follow-up enqueue at 214.953 s and dequeue at 217.703 s — exactly the queue-hint window), `permission-mode` / `mode` changes, `file-history-snapshot`, and `last-prompt` records. Approval *denials* register as `turn_duration` completions (27.404 s and 222.846 s in 002, matching the two Esc denials to ≤0.5 s); distinguishing denial from success requires reading the surrounding user/assistant records, not the duration record alone.
- **P2.2 — confirmed.** All four session-1 `turn_duration` events align to labeled dock seams within 0.11–0.21 s (36.406 vs 36.52; 87.178 vs 87.33; 138.170 vs 138.38; 295.934 vs 296.14) — inside one 5 fps sample interval.
- **P2.3 — confirmed on the captured matrix.** No transcript/surface disagreement at any driven seam in either session; queue and denial events are distinguishable and correctly ordered. Relay latency manifests identically in both channels (long turn durations), so no skew class was observed.

Caveat: the transcript is a **post-hoc** oracle. It lags live state by write latency (sub-second on this host) and lives only where `CLAUDE_CONFIG_DIR` points; using it as a production detection channel is out of campaign scope, same posture as codex's rollout lane.

## Scope

Covers the `~/.claude/projects/` transcript store as a post-hoc oracle only. Claude has no live structured channel; none was discovered during the binary audit or the captures. Production adoption of any oracle channel is out of scope; integration follows only after manual review of campaign reports, with no OpenSpec artifacts produced by this campaign.

