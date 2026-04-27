## Context

`SingleSessionTrackingRuntime` (in `src/houmao/server/tui/tracking.py`) wraps the parser-driven `shared_tui_tracking` session and is responsible for resolving the `turn.phase` reported in `houmao-mgr agents state`. The `phase` lifecycle is:

1. The shared session ingests each tmux capture, derives `DetectedTurnSignals` via the active codex/claude detector profile, optionally overlays temporal hints, and decides between `active`, `ready`, `unknown`, or success-candidate paths.
2. Whenever `effective_signals.active_evidence` is true, the session emits `turn_phase="active"`. Every other branch emits `ready` or `unknown`. The active phase is therefore *latched fresh from the parser on every snapshot*, not held independently after the original trigger clears.
3. The runtime adds two corrective overlays — stale-active recovery (~5 s, restricted to `active_reasons ⊆ {status_row}`) and final stable-active recovery (~20 s, intended as the catch-all). Both build a recovery candidate signature; if the signature is byte-stable across the threshold, recovery overrides phase to `ready` and expires any synthetic `tui-anchor:<agent_id>` server-owned authority.

The current final stable-active candidate (`_build_final_stable_active_recovery_candidate`) keys its signature on a JSON blob that mixes `_raw_surface_signature(output_text) = sha1(tmux_capture_text)` with `tracker_state.stability_signature`, `parsed_surface.*`, `surface.model_dump()`, `turn_phase`, `last_turn_result`, `last_turn_source`, `active_reasons`, and `notes`. Two failure modes follow directly:

- **Raw bytes are too noisy**: ANSI styling, cursor positioning, trailing-pad-width, footer ellipsis, and any other byte-level redraw flips the signature on every poll. `_update_final_stable_active_recovery_locked` cancels the pending 20 s timer the moment `pending_signature != candidate.signature`, so the timer never reaches the threshold even when the visible screen is genuinely static for hours.
- **Parser-derived inputs are circular**: the candidate signature includes parser output, and the candidate's gate predicates (`_is_submit_ready(parsed_surface)`, `surface.accepting_input`, `surface.editing_input`, `"stream_retry_status" in active_reasons`) consult parser output. Recovery exists precisely to repair parser misclassification; tying it to those signals means the recovery is disabled in the cases it was designed to handle.

Issue #51 documents one such permanent latch: the gateway-owned tracker reported `stability.stable_for_seconds = 4745` (the *normalized* surface had been stable for 79 minutes) while the recovery's mixed signature flipped on every poll, so phase remained `active` and the mail-notifier silently skipped every wake until a manual workaround was applied.

## Goals / Non-Goals

**Goals:**

- Make final stable-active recovery resilient to any failure or noise in the activity-detection pipeline. The recovery decides *only* from raw rendered-surface stability and the fact that `turn.phase` is currently `active`.
- Provide one simple, parser-independent rendered-surface signature definition that survives ANSI styling, trailing-whitespace, and other invisible-byte jitter, while still flipping on any actual on-screen text change.
- Preserve the existing recovery-applied effect: when the recovery fires, phase is set to `ready`, any stale `tui-anchor:<agent_id>` server-owned authority is expired, and `last_turn.result` is *not* manufactured as `success`.
- Keep ReactiveX-based scheduler timing, the existing 20 s default window, and the existing `--gateway-tui-final-stable-active-recovery-seconds` configuration knob unchanged.

**Non-Goals:**

- Fixing the upstream parser false positive that produces the latch (`_TOOL_CELL_RE` matching completed tool-cell bullets in the codex live edge). That is a separate change against the parser layer and intentionally out of scope here.
- Touching the stale-active recovery's `active_reasons ⊆ {status_row}` fast path. It remains as an opportunistic shortcut and continues to depend on parser output; the redesigned final stable-active recovery is the parser-independent backstop.
- Changing the mail-notifier deferral logic, `agents state` projection of `active_turn_id`, or the gateway timing-configuration plumbing.
- Adding new diagnostics surfaces (`mail-notifier status.last_skip_reason` etc.) — useful but separately tracked.

## Decisions

### Decision: Use one rendered-surface signature as the *only* recovery key

Define a helper that hashes ANSI-stripped, per-line right-trimmed tmux text:

```python
def _rendered_surface_signature(output_text: str | None) -> str | None:
    if output_text is None:
        return None
    stripped = ANSI_ESCAPE_RE.sub("", output_text).replace(" ", " ")
    normalized = "\n".join(line.rstrip() for line in stripped.splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

The recovery candidate's `.signature` is exactly this hash — no JSON envelope, no parser-derived fields. `ANSI_ESCAPE_RE` is reused from `shared_tui_tracking/surface.py`, where it already drives `SurfaceView.stripped_lines`.

**Rationale**: this matches the user's "judgement by raw tmux surface watching" design intent. Stripping ANSI and right-trimming kills the dominant sources of byte-level jitter that make pure `sha1(output_text)` useless, while remaining a function of the rendered text content alone — no detector profile, no temporal hint, no `parsed_surface.business_state`.

**Alternatives considered**:

1. *Continue using `tracker_state.stability_signature`* (the issue-author's proposal). Rejected: the stability signature is computed from `_MutableTrackerState`, which is parser output. If the parser keeps re-emitting `turn_phase="active"` with the same `active_reasons`, the stability signature is stable and recovery would fire — but the same parser fault could equally flip `active_reasons` between `("tool_cell",)` and `("transcript_growth",)` once per poll, producing exactly the same "never settles" symptom one layer up. The recovery must not depend on parser stability at all.
2. *Keep raw `sha1(output_text)` but extend the timer to 60 s*. Rejected: doesn't solve the root issue (the timer keeps re-arming, not just running long), and harms latency when the surface is genuinely static.
3. *Hash `surface.stripped_lines` from the parser-built SurfaceView*. Rejected as the recovery input because it would require routing the SurfaceView through the recovery path. Hashing the raw `output_text` directly keeps the recovery free of parser dependencies and the result is equivalent in content.

### Decision: Reduce the recovery gate to two preconditions

`_build_final_stable_active_recovery_candidate` becomes:

```python
def _build_final_stable_active_recovery_candidate(
    *,
    turn: HoumaoTrackedTurn,
    rendered_surface_signature: str | None,
) -> _FinalStableActiveRecoveryCandidate | None:
    if turn.phase != "active":
        return None
    if rendered_surface_signature is None:
        return None
    return _FinalStableActiveRecoveryCandidate(
        signature=rendered_surface_signature,
        active_reasons=(),
    )
```

Removed gates: `parsed_surface is None`, `diagnostics.availability`, `_is_submit_ready(parsed_surface)`, `surface.accepting_input`, `surface.editing_input`, `"stream_retry_status" in active_reasons`. None of those signals can make a stuck `phase=active` *more* recoverable; they can only *suppress* recovery.

**Rationale**: the recovery is the safety net for parser fault. Letting parser-derived signals veto it is the bug.

**Alternatives considered**: keep `surface.editing_input != "yes"` (the user is mid-edit) as a guard. Rejected for the proposal: even mid-edit, if phase is genuinely stuck active for 20 s of identical screen, recovery is still correct (phase=ready does not interfere with the user's edit; the next snapshot will re-evaluate). Documented as an open question below.

### Decision: Keep the recovery-applied side effects unchanged

The branch at `tracking.py` ~L702–740 still mutates the response's `surface.ready_posture="yes"`, `turn.phase="ready"`, calls `_expire_turn_anchor_for_final_recovery_locked`, and emits the operator-state recovery detail. The redesign only changes *when* recovery fires, not *what* it does on fire.

### Decision: Drop `_raw_surface_signature` and `active_reasons` from the candidate

`_raw_surface_signature` has no remaining caller after this change and is removed. The candidate's `active_reasons` field becomes always-empty; we keep the field for now for debug-payload compatibility but stop populating it.

### Decision: Stale-active recovery stays as-is

Stale-active still requires `active_reasons ⊆ {"status_row"}` — narrow but correct for the codex idle-status-row case. Its 5 s threshold makes it useful as a fast path when the parser is *correct* and the only active reason is a transient status row; keeping it does not weaken the redesigned final stable-active path because that path no longer depends on stale-active having fired first.

## Risks / Trade-offs

- **Risk**: A genuinely active turn whose codex output happens to render byte-identically for 20 s (e.g., a long-running tool that emits no progress) would be falsely recovered to `phase=ready`. → **Mitigation**: codex's TUI emits a status-row tick (`• Working (esc to interrupt) … <Ns>`) while a tool is in flight, so the rendered text is not byte-identical for 20 s in real workloads. The 20 s window is also operator-tunable via `--gateway-tui-final-stable-active-recovery-seconds`. Tests should cover the active-screen-with-tick case to assert recovery does *not* fire there.
- **Risk**: Recovery firing while the operator is editing input could clear phase under their feet. → **Mitigation**: the recovery only sets `turn.phase` to `ready`; it does not interrupt the operator. The next snapshot will re-evaluate. If this turns out disruptive, add `surface.editing_input != "yes"` back to the gate.
- **Risk**: The new rendered-surface signature is sensitive to terminal width changes (a tmux pane resize would re-wrap text). → **Mitigation**: a resize is a real visible change; treating it as a signature flip is correct. The 20 s timer simply restarts, which matches operator expectations.
- **Trade-off**: We give up the previous candidate signature's ability to ignore some kinds of "noise" that the parser normalized away. In exchange, the recovery is no longer disabled when the parser misbehaves. Net win: parser faults that would have permanently latched phase now self-correct in 20 s.

## Migration Plan

This is an internal contract change; no persisted artifacts are involved. Steps:

1. Land the code change to `src/houmao/server/tui/tracking.py` and the spec delta.
2. Update unit tests under `tests/unit/server/tui/` to reflect the new gate (parser-independent) and the new signature (rendered-surface). Add a test that exercises the issue #51 shape: parser keeps re-emitting `turn_phase="active"` with non-empty `active_reasons`, but the rendered surface is byte-stable, and recovery fires after 20 s.
3. Bump the `tracker-recovery` debug-stream `event_type="final_stable_active_recovery_armed"` payload schema if any field name changes (only `recovery_signature_sha1` remains; same shape).
4. No deployment ordering or rollback considerations; the change is local to `houmao-server` and `houmao-passive-server`.

## Open Questions

- Should `surface.editing_input == "yes"` re-enter the gate purely as a UX guard against clearing phase mid-edit? Defer to implementation review with one test case demonstrating the actual user-visible effect.
- Should the rendered-surface signature also strip the codex bottom status footer line (`gpt-5.4 high · /path…`) so a directory rename or context-window tick does not re-arm the timer? Probably yes if observed in practice; defer until a test fixture exhibits the behavior.
- Should stale-active recovery be similarly redesigned to be parser-independent? Out of scope for this change; revisit once the redesigned final stable-active path has proven itself and the parser false-positive root-cause work has progressed.
