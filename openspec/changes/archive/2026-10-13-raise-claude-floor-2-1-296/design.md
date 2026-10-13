# Design

## Context

See proposal.md — Why. The authoritative implementation reference is the campaign's qualified monkey-patched candidate at `scripts/explore/claude-code-tui-parsing/campaign_lib/patches.py`, replayed against three blind-labeled 5 fps recordings of claude 2.1.296 (scores in the repair report's Candidate Qualification section). The patch already encodes every detector, temporal, registry, and tracker-session repair this change promotes; the design question is how each candidate seam lands as production code, not what the repairs are.

Current production seams the candidate patches at replay time: `apps/claude_code/profile.py` module regexes (`COMPLETION_MARKER_RE`, `SPINNER_LINE_RE`, `INTERRUPTED_RE`), `signals/pending_input.py` ghost-cell detector, `session.py` visible-draft invalidation, and the registry's claude interval `[2.1.0, 2.2.0)` plus `FallbackClaudeDetector`.

## Goals / Non-Goals

**Goals:**
- Single floor-gated claude registration at `>=2.1.296` with `qualified_through_version="2.1.296"`, `claude` added to the floor-error tool-name map; fallback deleted.
- Production claude detector behavior identical to the qualified candidate on the three frozen sessions (booleans 1.0000/1.0000, 1.0000/1.0000, 1.0000/0.9995; zero false-ready).
- Tracker session stops clearing latched outcomes on visible drafts, for all apps, with kimi/codex qualification gates re-run as regression evidence.
- Launch floor realigned to `>=2.1.296` with a live unattended re-probe.
- Qualification replay test and fixtures promoted, mirroring the codex gate.

**Non-Goals:**
- Error/retry surface needles (overload, rate limit, disconnect) — never occurred on the relay during the campaign; declared follow-up (fault-injection iteration).
- Compaction maintenance-turn handling for claude (the codex `compaction_status` carve-out) — the claude compaction surface was never captured cleanly (driver bug mangled the `/compact` leg); no labels exist to qualify against.
- The `/btw` side-question surface, `atis-latch` records, tui_down exit-surface timing — declared campaign follow-ups.
- Extending the settle-identity signature projection to kimi/codex detectors — their recorded surfaces show no furniture churn; recorded as a follow-up note.

## Decisions

- **Candidate code moves, monkey-patch dies.** The production detector becomes a new `ClaudeCodeSignalDetectorV2_1_X` body whose `detect`, `build_temporal_frame`, `derive_temporal_hints`, and `temporal_window_seconds` (600 s) match the candidate class, with the module-level regexes and `pending_input_state` rewritten in place (no runtime patching). The candidate's subclass-of-stale-base shape collapses: the repaired logic replaces the 2.1.81-era code directly. Alternative considered (keep the old class alongside and register only the new one): rejected — the floor cut removes every consumer of the old code, and the repo's breaking-change policy favors deletion over preservation.
- **Modal shield runs before prompt classification inside the detector, not in the session.** The kimi/codex candidates established the same placement; the session's generic reducer stays modal-free. Approval/trust/picker needles live in the claude profile as bounded token pairs (`Quick safety check` + `trust this folder`; `do you want to ` + `esc to cancel`; `Select model` title, or numbered `❯ N.` options + `▔` border), per the bounded-pattern requirement in `versioned-tui-signal-profiles`.
- **Silent-abort and restore channels are profile-owned temporal hints, not session rules.** The session merges profile hints generically already; the claude profile carries the frame payload (busy footer, spinner, modal, slash menu, interrupt line, region/surface dock sets) and the three inference rules. Alternative considered (session-side abort detection): rejected — it would leak claude surface structure into the shared engine, against the profile-encapsulation requirement.
- **The fresh-dock rule disambiguates completion from abort.** A region dock counts as completion evidence only if the dock line was not visible during the preceding active frames; this keeps the previous turn's dock (re-anchored into the region when an aborted turn's echo scrolls off) from reading as completion. This is the load-bearing temporal rule for the silent-abort span and is why the temporal window is 600 s rather than the 3 s kimi/codex use: the inference must survive arbitrarily long post-abort idle spans in the recorded corpus shape.
- **Visible-draft invalidation is deleted from the tracker session, not carved per-app.** The candidate patches `session.py` to skip `reason="visible_draft"`; production removes that invalidation reason entirely (the draft branch keeps its phase decisions, it just stops clearing outcomes). Campaign labels contradict the old spec scenario directly, and kimi/codex corpora never exercised the path (their interrupted surfaces clear the composer, so draft authority never coincided with a latched outcome). Alternative considered (skip only when a claude profile is resolved): rejected — the rule was wrong for every app, and per-app reducer branches against the shared-engine encapsulation.
- **Settle-identity signature becomes detector-owned in shape.** The claude profile hashes a state-bearing-line projection (transcript anchors, box rules, mode footer); kimi/codex keep full-surface hashes. The session keeps consuming `surface_signature` opaquely.
- **Qualification gate thresholds mirror measured candidate scores with a hair of slack:** session 1 ≥ 0.999, session 2-002 = 1.0, session 2-001 ≥ 0.999 on the two booleans, replicating the codex test's structure (gzipped snapshots, labels, provenance).
- **Launch realignment is data plus a live re-probe, not a code change.** `claude.yaml` strategy renamed (`claude-unattended-2.1.296`), `supported_versions: ">=2.1.296"`, probe evidence refreshed against 2.1.296's auto-mode default and always-on trust dialog. Any hardcoded `2.1.81` floor references in launch-plan/brain-builder code move with it.

## Risks / Trade-offs

- [Shared draft-invalidation removal regresses kimi/codex live behavior] → Their qualification gates re-run in this change; the spec delta records that their recorded corpora never relied on the path, and the new rule (outcomes clear on submit/activity) matches all three tools' labeled evidence.
- [600 s temporal window grows per-session frame memory] → Frames are tiny frozen dataclasses sampled at pane-capture cadence (~5 fps worst case ≈ 3 k frames); bounded by eviction and session lifetime; measured during unit tests.
- [Auto mode makes approval coverage environment-dependent] → The qualification corpus pins deterministic approvals via `permissions.ask` rules (session 2-002) and records auto mode as its own evidence session (2-001); the launch re-probe records current auto-mode startup behavior as launch evidence, not as a tracking gate.
- [Stale-dock disambiguation depends on 5 fps visibility] → The fresh-dock rule compares dock-line text visibility across frames; a dock that appears and scrolls within one sample interval could misclassify — the corpus shape (dock persists in the captured tail for every completed turn) is recorded as the qualification boundary.
- [Launch re-probe may find 2.1.296 unattended breakage beyond this change's scope] → The probe is a task with recorded evidence; breakage that invalidates the unattended contract blocks the task list, not silent realignment.

## Migration Plan

Single commit sequence mirroring the codex floor change: detector + registry + session changes land with the fixtures and the qualification gate in one commit; below-floor claude then fails loudly at tracker resolution and at managed launch strategy selection. Rollback is `git revert` of the commit; there is no persisted-state or wire-format migration. Deployments on older claude upgrade to 2.1.296 or later.

## Open Questions

None blocking: error/retry needles, claude compaction handling, and kimi/codex signature projection are follow-up iterations recorded in the campaign's repair report.
