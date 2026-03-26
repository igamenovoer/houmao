# Shadow Parser TUI State Detection — Code Review & Design Proposal

**Date:** 2026-03-18
**Scope:** `scripts/demo/mailbox-roundtrip-tutorial-pack/`, `src/houmao/agents/realm_controller/backends/shadow_parser_core.py`, `claude_code_shadow.py`, `codex_shadow.py`, `cao_rest.py`, `mail_commands.py`
**Focus:** TUI parsing accuracy, state transition reliability, root problems

---

## 1. Executive Summary

The shadow parser is a runtime-owned system that converts raw tmux scrollback snapshots into two artifacts: a **SurfaceAssessment** (what is the tool doing?) and a **DialogProjection** (what visible text changed?). The `_TurnMonitor` state machine in `cao_rest.py` consumes these assessments across a polling loop to track a seven-state lifecycle: `awaiting_ready → submitted_waiting_activity → in_progress → completed` (happy path), with `blocked_operator`, `stalled`, and `failed` as error branches.

The system works but has **fundamental fragility rooted in its core approach**: inferring structured state from unstructured, version-specific, decoration-heavy terminal output. This review identifies five root problems and proposes a layered redesign.

---

## 2. Root Problems

### 2.1 — Regex-Based Classification on Tail Lines Is Inherently Ambiguous

**Where:** `claude_code_shadow.py:_build_surface_assessment()` (lines 427–509), `_detect_output_variant()` (lines 588–614), `_classify_surface_axes()` (lines 749–804)

**Problem:** State classification depends on regex matches against the last N lines (`status_tail_lines=100`) of the terminal scrollback. These boolean flags (`has_idle_prompt`, `has_processing`, `has_response_marker`, `operator_blocked_excerpt`, `has_trust_prompt`, etc.) are all computed independently and then combined in a priority-ordered if/elif chain in `_classify_surface_axes()`.

This creates **state confusion** when multiple signals co-exist in the tail window:

- A **response marker** (`●`) and an **idle prompt** (`❯`) can both be visible simultaneously. The classifier resolves this by priority (operator blocked > processing > idle > unknown), but this priority chain doesn't account for the *temporal ordering* of these signals within the scrollback.
- A **slash command** left in scrollback history (`/model`) combined with a current idle prompt creates a false `slash_command` ui_context. The code defends against this in `_active_prompt_payload()` by checking only the last non-empty line, but the pattern is fragile — any intermediate blank line or TUI chrome can shift what counts as "last."
- **Processing spinner** detection (`[✶✢✽✻·✳].*…`) can false-positive on response text that contains Unicode symbols followed by an ellipsis.

**Root cause:** The parser treats the scrollback tail as a bag of signals rather than a structured sequence. It has no model of "which line is the current prompt line" vs. "which lines are historical output." It tests for the *presence* of patterns anywhere in 100 lines, not their *position relative to the active cursor/prompt*.

### 2.2 — No Temporal Model Between Snapshots

**Where:** `cao_rest.py:_TurnMonitor.observe_completion()` (lines 395–454)

**Problem:** The `_TurnMonitor` consumes snapshots as independent observations. It tracks two boolean flags (`m_saw_working_after_submit`, `m_saw_projection_change_after_submit`) and timestamps for unknown/stalled timing, but has no memory of the *sequence of states* it observed.

This means:

- **Transient idle flicker is indistinguishable from real completion.** If the TUI briefly shows an idle prompt while the tool is still processing (e.g., during a tool approval that resolves instantly), the monitor sees `submit_ready` + `m_saw_working_after_submit=True` → declares completion prematurely.
- **No hysteresis or debounce.** A single snapshot showing `idle` after a `working` snapshot is immediately treated as terminal. There's no requirement for N consecutive idle snapshots or a minimum idle duration.
- **Projection drift is coarse.** The completion check compares `dialog_projection.dialog_text != baseline` — a single-character change in the projection (even from TUI redraw noise) counts as "projection changed." Combined with a subsequent idle snapshot, this can trigger false completion.

**Root cause:** The state machine is memoryless about state *duration* and *stability*. It makes irrevocable decisions (completion) from single-sample observations.

### 2.3 — Sentinel Completion Gating vs. TUI Parse Mismatch

**Where:** `mail_commands.py:_contains_complete_mail_result_payload()`, `shadow_mail_result_contract_reached()`, `parse_mail_result()` / `_parse_mail_result_text()`

**Problem:** (Already documented in `openspec/changes/fix-shadow-mailbox-sentinel-prompt-echo/`) The provisional completion observer uses `str.find()` to detect `BEGIN`/`END` sentinel substrings anywhere in the surface, while the final parser expects these as standalone delimiter lines around valid JSON. When the prompt itself echoes sentinel names (the `response_contract` JSON in the prompt contains the sentinel strings), the observer declares "contract reached" but the parser then fails.

**Root cause:** Two independent detection paths (loose substring gate vs. strict block parser) applied to the same text surface, with no shared contract.

### 2.4 — Version Preset Rigidity Creates a Maintenance Treadmill

**Where:** `claude_code_shadow.py:_PRESETS` (lines 221–267), `codex_shadow.py:_PRESETS`

**Problem:** Each new Claude Code or Codex version can change:
- Prompt characters (`>` → `❯`)
- Response markers (`⏺` → `●`)
- Spinner format (parenthesized suffix requirement changes)
- Menu/approval wording
- Banner format

The parser maintains a hard-coded preset per known version. Unknown versions fall back to the latest known preset with an anomaly logged (`unknown_version_floor_used`). This means every upstream CLI release is a potential regression — and the parser can't know it's wrong until a real failure occurs in production.

**Root cause:** The system is structurally coupled to implementation details of third-party CLI tools' visual output, with no negotiated contract between the tools and the parser.

### 2.5 — Baseline Position Tracking Is Fragile Against Terminal Buffer Cycling

**Where:** `claude_code_shadow.py:parse_snapshot()` (line 330), `cao_rest.py:_capture_shadow_baseline()` (lines 1377–1393)

**Problem:** The baseline position is captured as a character offset into the normalized text. If the terminal buffer cycles (tmux scrollback limit reached), the entire prefix may disappear, making `len(clean_output) < baseline_pos`. The parser records `baseline_invalidated=true` as an anomaly but doesn't have a recovery strategy — it continues parsing with the invalid baseline, which can cause:
- Response markers from the current turn to be counted as pre-baseline (ignored)
- Or, conversely, old markers from a different turn to be counted as current

**Root cause:** Character-offset baselines assume a monotonically growing text buffer. Terminal emulators don't guarantee this.

### 2.6 — Fresh Environment TUI Noise Destroys Parser Assumptions

**Where:** `claude_code_shadow.py:_classify_surface_axes()`, `_operator_blocked_excerpt()`, `_TRUST_PROMPT_RE`, `_SETUP_BLOCK_RE`

**Observed in:** Real-agent HTT worktree run (`context/issues/known/issue-real-agent-htt-worktree-runs-mix-snapshot-and-host-state.md`)

**Problem:** The shadow parser was developed and tested against tools that are already set up, logged in, and configured on the developer's machine. In a fresh environment (disposable worktree, clean CI runner, new machine), CLI tools emit first-run content that the parser either misclassifies or can't handle:

- **Installer/onboarding prompts** — Claude Code may show "Complete setup", "Sign in", or "Continue in browser" before any prompt appears. The parser detects these via `_SETUP_BLOCK_RE` and classifies as `awaiting_operator`, but the readiness gate then raises `BackendExecutionError` with no recovery path. The operator has no way to intervene through the automation pipeline.
- **Trust/folder prompts on first entry** — "Allow Claude to work in this folder?" appears when the tool has never seen the project directory. Detected as `awaiting_operator` / `trust_prompt`, but again the automation has no mechanism to answer it.
- **Banner messages and version announcements** — Fresh installs may emit extra banner lines, update notices, or migration messages that aren't in any test fixture. These land in the tail window and can shift what `_active_prompt_payload()` considers the "last non-empty line."

The HTT run showed this concretely: after working around credential and CAO-home issues, the mailbox turn failed because the terminal contained "the injected mailbox request plus a Claude-side installer/banner message, but not one clean machine-readable mailbox result block."

**Root cause:** The parser's signal vocabulary was calibrated to the steady-state TUI of an already-configured tool. Fresh-environment startup noise is a different signal regime that the parser encounters but cannot recover from. The system implicitly depends on ambient host state (tool already set up, already trusted the folder) — a dependency that is invisible in the main checkout but immediately breaks in a clean environment.

**Connection to other problems:**
- Amplifies 2.1 (bag-of-signals): startup noise adds extra signals to the tail window that co-exist with the actual prompt
- Amplifies 2.3 (sentinel mismatch): when the tool shows setup prompts instead of processing the mailbox request, the sentinel never appears, but the completion observer may still see echoed sentinel names from the prompt
- Is the specific failure mode that the HTT worktree exposed as the third cascading failure

### 2.7 — Implicit Four-Root Environmental Coupling

**Observed in:** Real-agent HTT worktree run

**Problem:** The shadow parser's reliability depends not just on its own logic, but on the runtime environment being in a specific state. The HTT issue identified four root classes that must all be correct for a real-agent run to reach the point where parsing matters:

1. **Source snapshot** — the code itself
2. **Operator-local credentials and login state** — API keys, tool auth tokens
3. **Tool-owned runtime state** — tool home directories, cached configs, trust decisions
4. **Launched project workdir** — where the tool is pointed at

In the main checkout, these roots overlap implicitly: credentials exist in gitignored dirs, the tool has been set up, and the workdir is the developer's actual project. In a clean worktree, the first three are absent, causing a cascade of failures that ultimately surface as TUI parsing failures:

```
Missing credentials → preflight fail → (workaround) →
CAO workdir-outside-home → session start fail → (workaround) →
Tool shows setup/installer prompts → parser sees noise instead of expected TUI → parse fail
```

The parser appears to fail on TUI parsing, but the root cause is environmental. The parser can't distinguish "tool is showing first-run setup because the environment is wrong" from "tool is in an unexpected TUI state."

**Why this belongs in the parser review:** The shadow parser is the last line of defense — it's where all upstream environmental problems eventually manifest as observable failures. A more robust parser (with the Rx stability pipeline and cursor-anchored detection) would at least fail with clearer diagnostics and potentially recover from transient startup noise, rather than silently misclassifying or timing out.

---

## 3. Secondary Issues

### 3.1 — `_active_prompt_payload()` Is Positionally Fragile

The method scans backwards from the last non-empty line looking for an idle prompt character. But Claude Code sometimes renders status lines, spinners, or blank lines after the prompt. If the tail happens to end on a blank or a status line, the "active prompt" detection fails and the surface falls through to `unknown`.

### 3.2 — Dialog Projection Leaks State Into Completion Logic

The `_TurnMonitor` uses `dialog_projection.dialog_text` for coarse diffing, but this text is produced by a best-effort projector that drops banners, spinners, separators, etc. If the projector's drop rules change (e.g., a new preset handles a line differently), the diff behavior changes, which can flip the `m_saw_projection_change_after_submit` flag differently across versions. State detection should not depend on a "best-effort" surface.

### 3.3 — Polling Interval and Stall Timeout Are Disconnected

The default poll interval is 0.4s, and the stall timeout is 30s. But the stall timer measures *continuous unknown*, not *poll count*. If a poll takes longer than expected (slow CAO, network), the stall timer may fire after fewer actual observations than intended, and the subsequent `stalled_recovered` may not represent genuine recovery.

### 3.4 — No Preflight Capability Probe for Tool/Environment Readiness

The shadow parser assumes the tool will reach a parseable steady-state TUI after launch. There is no preflight step that verifies:

- Whether the tool requires login/setup before it can accept prompts
- Whether the tool has already trusted the project directory
- Whether the installed CAO server version supports the expected workdir-outside-home policy
- Whether the tool version matches a known parser preset

These are discovered only when the readiness or completion loop encounters unexpected TUI output. The failure mode is a timeout or `awaiting_operator` error that doesn't explain *why* the tool isn't ready. A capability probe before the first turn would convert late, confusing parse failures into early, actionable preflight errors.

### 3.5 — No Recovery Path for `awaiting_operator` During Automation

When the parser detects `awaiting_operator` (trust prompt, setup block, approval menu), the `_TurnMonitor` transitions to `blocked_operator` and the turn engine raises `BackendExecutionError`. There is no mechanism to:

- Auto-answer trust prompts when running in automated mode
- Dismiss setup/login blocks with a configured response
- Retry readiness after the operator resolves the block externally

In interactive/demo use, the operator can manually answer in the tmux session, but the automation pipeline has no callback or retry-after-intervention path. This makes `awaiting_operator` a terminal state in automation, even when the block is trivially resolvable.

---

## 4. Design Proposal: Layered State Detection with Stability Requirements

### 4.1 — Principle: Separate Signal Extraction from Temporal State Decision (Rx Replaces Sliding Window)

**Current:** One function (`_build_surface_assessment`) both extracts signals AND decides state. The `_TurnMonitor` then layers temporal logic on top via hand-rolled mutable fields.

**Proposed:** Split into two clean layers, where ReactiveX operators replace the need for any explicit sliding window or ring buffer:

1. **Signal Extractor** — Pure function. Produces a `SnapshotSignalSet` (structured, typed) from one snapshot. No state decisions. No temporal awareness. Stateless.
2. **Rx Temporal Pipeline** — Consumes the signal stream and applies temporal rules via Rx operators. The operators themselves carry the temporal memory that would otherwise require a sliding window:

| Temporal need | Old approach (sliding window / mutable fields) | Rx approach (operators carry state internally) |
|---|---|---|
| "Was working seen after submit?" | `m_saw_working_after_submit` boolean | `ops.scan()` accumulating evidence flags across the stream |
| "Has projection changed?" | `m_saw_projection_change_after_submit` boolean | `ops.distinct_until_changed(key=normalized_text)` — silence = stable |
| "Idle for N consecutive polls?" | Ring buffer of last N signal sets | `ops.debounce(stability_seconds)` — implicit consecutive-quiet requirement |
| "Unknown persisted for 30s?" | `m_unknown_started_at` timestamp | `ops.timeout(stall_seconds)` on a filtered sub-stream |
| "Last few snapshots for diagnostics?" | Ring buffer | `ops.do_action()` logging to a bounded deque (diagnostic concern, not decision logic) |

```
┌─────────────────┐    ┌──────────────────────┐    ┌────────────────┐
│ Raw TUI snapshot │───▶│ Signal Extractor      │───▶│ SnapshotSignals│
│ (scrollback)     │    │ (stateless, per-snap) │    │ (typed struct) │
└─────────────────┘    └──────────────────────┘    └───────┬────────┘
                                                           │
                                    rx.interval(0.4s) drives polling
                                                           │
                                                           ▼
                                             ┌──────────────────────────┐
                                             │ Rx Temporal Pipeline     │
                                             │                          │
                                             │ scan()       → evidence  │
                                             │ distinct()   → change    │
                                             │ debounce()   → stability │
                                             │ timeout()    → stall     │
                                             │ take_while() → terminal  │
                                             └────────────┬─────────────┘
                                                          │
                                                          ▼
                                             ┌──────────────────────┐
                                             │ LifecycleState       │
                                             │ + evidence chain     │
                                             │ + diagnostic trace   │
                                             └──────────────────────┘
```

**Why no sliding window is needed:** Rx operators are stateful internally. `debounce` remembers the last emission timestamp and resets on each new item. `distinct_until_changed` remembers the previous value. `scan` accumulates a reducer across the stream. `timeout` tracks elapsed silence. These operators *are* the temporal memory — there is nothing left that requires an explicit buffer of past snapshots for state decisions. A small diagnostic deque (last ~5 snapshots for error messages) can be maintained via `do_action` as a side effect, but it plays no role in lifecycle decisions.

### 4.2 — Introduce Cursor-Anchored Prompt Detection

Instead of scanning 100 tail lines for pattern presence, detect the **active prompt line** positionally:

1. Identify the last non-blank line in the scrollback.
2. If it matches an idle prompt pattern → that's the active prompt. Everything above it is historical output.
3. If it matches a processing spinner → tool is working. The active zone is the spinner + any preceding response text.
4. If it matches a menu/approval pattern → tool is blocked. The active zone is the menu block.
5. If none match → unknown.

The key change: **signals found above the active zone boundary should not influence current state classification.** A response marker 50 lines above the current prompt is historical, not current.

This requires defining a `prompt_boundary_index` per snapshot, then partitioning the scrollback into `historical_zone` and `active_zone`. State classification should only inspect the active zone. The dialog projector can still operate on the full scrollback.

### 4.3 — Replace Imperative State Timing with ReactiveX Debounce Pipeline

The current `_TurnMonitor` hand-rolls temporal logic via mutable timestamp fields (`m_unknown_started_at`, `m_stalled_started_at`) and single-sample boolean flags. The pattern we actually need — "TUI changed N seconds ago, wait M more seconds for stability, reset the timer if it changes again" — is a textbook **debounce with reset**, which is exactly what ReactiveX operators are designed for.

**Recommendation:** Use `reactivex` (already available in the pixi environment) to replace the `_TurnMonitor` completion and stall logic with a declarative pipeline.

**Key operator mapping:**

| Current imperative code | Rx operator |
|------------------------|-------------|
| Polling loop with `time.sleep(0.4)` | `rx.interval(poll_interval)` |
| `m_unknown_started_at` timestamp tracking | `ops.timeout(stall_seconds)` |
| Manual "did projection change?" boolean | `ops.distinct_until_changed(key=signal_fingerprint)` |
| Single-sample completion on idle | `ops.debounce(stability_seconds)` — reset timer on each new change, emit only after quiet period |
| Ring buffer of recent states | Not needed — Rx operators carry temporal state internally (see 4.1) |

**Sketch of the completion pipeline:**

```python
from reactivex import operators as ops
from reactivex.scheduler import NewThreadScheduler

def observe_completion_rx(poll_snapshot, baseline, policy):
    """
    poll_snapshot: Callable[[], ParsedShadowSnapshot]
    baseline: DialogProjection from pre-submit
    policy: CompletionPolicy(stability_seconds=2.0, poll_interval=0.4)
    """
    return rx.interval(policy.poll_interval).pipe(
        ops.map(lambda _: poll_snapshot()),
        ops.map(lambda s: (s, _signal_fingerprint(s))),
        ops.publish(lambda shared: shared.pipe(
            ops.do_action(lambda pair: _track_activity(pair, baseline)),
            ops.map(lambda pair: _check_terminal(pair)),
            ops.take_while(lambda r: r is None),
        )),
        # Core insight: only emit when fingerprint STOPS changing
        ops.distinct_until_changed(key=lambda pair: pair[1]),
        ops.debounce(policy.stability_seconds),   # ← "wait 2s, reset on change"
        ops.filter(lambda pair: is_submit_ready(pair[0].surface_assessment)),
        ops.filter(lambda _: saw_activity()),
        ops.first(),
        ops.timeout(policy.timeout_seconds),
    )
```

**The debounce semantic this enables:**

> "TUI changed 1 second ago → we consider TUI state is *changing* → wait for 2 more seconds of quiet. If TUI changes again, the timer resets and we start a fresh wait. Completion only fires after the full quiet period with a stable idle surface."

This replaces all of `_observe_unknown()`, the stall timestamp bookkeeping, and the single-sample completion gate with composable, testable operators.

**Threading model:** Keep the synchronous boundary at the `ShadowOnlyTurnEngine.execute_turn()` level. Use `NewThreadScheduler` or `TimeoutScheduler` internally and block on `observable.run()` / `threading.Event` at the call site. Callers don't need to change.

**Testing:** Rx's `TestScheduler` allows advancing virtual time deterministically — no real sleeps in unit tests, and complex temporal scenarios (transient flicker, stall recovery, debounce reset) become straightforward to assert.

**What to keep outside Rx:** The signal extractor (per-snapshot parsing) and sentinel block extraction remain plain functions. Rx is for the *temporal composition* layer only.

### 4.3.1 — Rx Also Addresses Readiness Monitoring, Stall Recovery, and Baseline Invalidation

The Rx approach isn't limited to completion. It naturally subsumes several other problems identified in this review:

**Readiness phase (currently `_wait_for_shadow_ready_status`):**

The current readiness loop is another hand-rolled poll-observe-sleep cycle with the same stall timing issues. With Rx:

```python
def observe_readiness_rx(poll_snapshot, policy):
    return rx.interval(policy.poll_interval).pipe(
        ops.map(lambda _: poll_snapshot()),
        # Terminal: blocked or disconnected → error immediately
        ops.do_action(lambda s: _raise_if_terminal(s)),
        # Wait for submit_ready with stability
        ops.filter(lambda s: is_submit_ready(s.surface_assessment)),
        ops.debounce(policy.readiness_stability_seconds),  # brief debounce to avoid flicker
        ops.first(),
        # Stall = no submit_ready within timeout
        ops.timeout(policy.readiness_timeout_seconds),
    )
```

This replaces the readiness loop's `_observe_unknown()` path, its stall timestamp tracking, and its `blocked_operator` / `failed` branching — all the same `m_unknown_started_at` bookkeeping that plagues the completion side.

**Stall detection and recovery (currently `_observe_unknown` + `_recover_if_stalled`):**

Currently: manual timestamps, manual elapsed calculation, manual anomaly emission on entry/exit. With Rx:

```python
# Within the main pipeline, fork a "stall watchdog" sub-stream:
ops.publish(lambda shared: rx.merge(
    # Happy path: known states flow through
    shared.pipe(ops.filter(lambda s: not is_unknown_for_stall(s))),
    # Stall watchdog: if only unknowns for 30s, emit stall event
    shared.pipe(
        ops.filter(lambda s: is_unknown_for_stall(s)),
        ops.debounce(policy.stall_timeout_seconds),  # 30s of continuous unknown
        ops.map(lambda s: _StallEvent(s)),            # typed stall marker
    ),
))
```

`debounce` here means: "if we keep seeing unknowns without interruption for 30s, emit once." If a known state appears, `distinct_until_changed` upstream resets the flow. No manual `m_stalled_started_at` or `_recover_if_stalled()` needed.

**Baseline invalidation recovery (problem 2.5):**

Currently: `baseline_invalidated=true` is recorded as an anomaly but no recovery happens. With Rx, the pipeline can re-baseline on detection:

```python
ops.scan(lambda acc, snapshot: _maybe_rebaseline(acc, snapshot), seed=initial_state)
```

The `scan` accumulator detects baseline invalidation (scrollback shrank below baseline offset), captures a new baseline from the current snapshot, and emits an anomaly — all within the stream, no external mutable state.

**Polling interval / stall timeout disconnect (problem 3.3):**

Currently: wall-clock stall timeout fires regardless of how many polls actually happened. With Rx, `timeout` is based on *emissions*, and `debounce` is based on *inter-emission gaps*. If polls slow down (slow CAO), fewer items enter the pipeline, and `debounce(2.0)` naturally waits for 2 real seconds of idle *between actual observations*, not 2 seconds of wall clock during which zero polls may have completed. This is inherently more correct.

**Summary of `_TurnMonitor` mutable fields eliminated by Rx:**

| Mutable field | Rx replacement |
|---|---|
| `m_state` | Pipeline terminal event type (completed / failed / stalled / blocked) |
| `m_unknown_started_at` | `ops.timeout()` on unknown-filtered sub-stream |
| `m_stalled_started_at` | `ops.debounce()` on unknown-filtered sub-stream |
| `m_saw_working_after_submit` | `ops.scan()` accumulator flag |
| `m_saw_projection_change_after_submit` | `ops.distinct_until_changed()` — any emission = change happened |
| `m_baseline_projection_text` | `ops.scan()` accumulator baseline, or pipeline seed |
| `m_anomalies` | `ops.do_action()` appending to a diagnostic list (side effect, not decision) |

The entire `_TurnMonitor` class — its 7 mutable fields, 5 methods, and manual timestamp arithmetic — collapses into two Rx pipelines (readiness + completion) composed from standard operators.

### 4.4 — Unified Sentinel Block Extraction

(Aligns with the existing openspec change `fix-shadow-mailbox-sentinel-prompt-echo`.)

Replace the dual-path sentinel detection with a single `extract_sentinel_blocks()` function that:
1. Scans for sentinel-on-own-line patterns (not substrings)
2. Returns zero or more `SentinelBlock(begin_line, end_line, payload_text)` candidates
3. Is used by BOTH the provisional completion observer AND the final parser

The provisional gate becomes: "Does `extract_sentinel_blocks()` return at least one candidate?" The final parser validates the candidate(s) against the active request contract.

### 4.5 — Normalized Text Diffing Instead of Projection Diffing

For the "did the TUI change?" completion evidence, diff against `normalized_text` (ANSI-stripped, close to source) rather than `dialog_text` (heavily projected). This decouples completion logic from projector behavior. The projector can evolve independently without accidentally changing lifecycle decisions.

### 4.6 — Structured Version Negotiation (Longer-Term)

For tools that support it, negotiate the output contract at session start rather than detecting it from the output:

1. At `start-session`, query the tool for its version (e.g., `claude --version` or read the banner).
2. Store the version in `CaoSessionState`.
3. Select the preset once at session start, not on every snapshot.
4. If the version is unknown, log a warning and proceed with latest-known — but do this once, not on every poll.

Even better (if feasible): work with tool authors to emit machine-readable status signals (e.g., a structured status line at a known position) rather than relying on visual parsing of decorative TUI output.

### 4.7 — Environment-Aware Readiness: Capability Probe and Operator-Block Recovery

**Problem addressed:** 2.6 (fresh-environment TUI noise), 2.7 (four-root coupling), 3.4 (no preflight probe), 3.5 (no recovery for `awaiting_operator`)

The shadow parser is the last component in the chain, but it absorbs failures from every upstream environmental assumption. Two improvements would prevent parser-layer confusion:

**4.7.1 — Pre-turn capability probe:**

Before the first `_wait_for_shadow_ready_status()`, run a lightweight probe phase:

1. Capture one snapshot immediately after session creation.
2. Parse it for `_SETUP_BLOCK_RE`, `_TRUST_PROMPT_RE`, `_DISCONNECTED_RE` signals.
3. If setup/login block detected → fail fast with a specific error: "Tool requires interactive setup. Run `<tool> --setup` in the terminal first, or configure auto-trust."
4. If trust prompt detected → either auto-send trust confirmation (if policy allows) or fail fast with: "Tool is prompting for folder trust. Configure `--trust` flag or pre-approve."
5. If idle prompt detected → proceed to readiness phase.
6. If unknown → proceed to readiness with a warning that the initial state is unrecognized.

This converts the late, confusing "timed out waiting for shadow readiness" into an early, actionable "the tool isn't set up for automated use."

**With Rx**, this probe naturally becomes the head of the readiness pipeline:

```python
def observe_readiness_with_probe_rx(poll_snapshot, policy):
    return rx.interval(policy.poll_interval).pipe(
        ops.map(lambda _: poll_snapshot()),
        # Phase 1: Probe — detect unrecoverable environment blocks early
        ops.do_action(lambda s: _raise_if_setup_block(s)),     # fail fast
        ops.do_action(lambda s: _auto_trust_if_policy(s)),     # auto-answer if allowed
        # Phase 2: Wait for submit_ready with stability
        ops.filter(lambda s: is_submit_ready(s.surface_assessment)),
        ops.debounce(policy.readiness_stability_seconds),
        ops.first(),
        ops.timeout(policy.readiness_timeout_seconds),
    )
```

**4.7.2 — Operator-block retry with external intervention window:**

Instead of treating `blocked_operator` as immediately terminal during automation, allow a configurable intervention window:

1. When `awaiting_operator` is detected, emit a structured event: `{"kind": "operator_intervention_needed", "block_type": "trust_prompt", "excerpt": "..."}`.
2. Keep polling for `operator_block_intervention_timeout_seconds` (configurable, default 0 for current behavior).
3. If the block clears within the window (operator manually answered in tmux) → resume.
4. If timeout → raise `BackendExecutionError` as today.

With Rx, this is a `timeout` on an inner observable that filters for the block clearing:

```python
# Inside the completion pipeline, when blocked_operator is detected:
ops.timeout(policy.operator_intervention_timeout_seconds,
            other=rx.throw(BackendExecutionError("operator block not resolved")))
```

**Connection to four-root model (2.7):**

The capability probe and intervention window don't solve the four-root separation problem directly — that requires the run planner to model `source_root`, `project_workdir`, `runtime_root`, `tool_state_root`, and `external_prereqs` as first-class inputs (as the HTT issue recommends). But they prevent the parser from being the place where environmental failures silently accumulate. The parser should report "tool not ready because X" rather than "unknown TUI state, timed out."

---

## 5. Prioritized Recommendations

| Priority | Issue | Fix | Risk if Unfixed |
|----------|-------|-----|-----------------|
| **P0** | Sentinel prompt-echo false positive (2.3) | Unified block extraction (4.4) | Mailbox turns fail intermittently |
| **P1** | Single-sample completion (2.2) | Rx debounce pipeline (4.3) | False completion on transient idle |
| **P1** | Bag-of-signals classification (2.1) | Cursor-anchored detection (4.2) | Historical signals pollute current state |
| **P1** | Stall timing / readiness fragility (2.2, 3.3) | Rx readiness + stall pipelines (4.3.1) | Stall false positives, timing disconnects |
| **P1** | Fresh-environment TUI noise (2.6, 3.4) | Capability probe + Rx readiness head (4.7.1) | Late, confusing failures in clean environments / HTT / CI |
| **P2** | Projection-based diffing (3.2) | Normalized text diffing (4.5) — or Rx `distinct_until_changed` on normalized text | Projector changes break completion |
| **P2** | Baseline invalidation (2.5) | Rx `scan()` re-baseline (4.3.1) | Long-running sessions drift |
| **P2** | No recovery for operator blocks (3.5) | Intervention window with Rx timeout (4.7.2) | Automation can't survive trivially resolvable blocks |
| **P2** | Four-root environmental coupling (2.7) | Run planner models roots explicitly (4.7 + HTT issue) | Every new environment rediscovers the same cascade |
| **P3** | Version preset treadmill (2.4) | Structured negotiation (4.6) | Each CLI release is a risk |

---

## 6. Appendix: Key Code Paths Traced

### A. Mailbox Roundtrip Tutorial Pack Flow

```
run_demo.sh auto
  → tutorial_pack_helpers.py phase_start()
    → houmao realm-controller start-session --cao-parsing-mode shadow_only
      → CaoRestSession.__init__() → ShadowOnlyTurnEngine
  → tutorial_pack_helpers.py phase_roundtrip()
    → houmao realm-controller send-prompt (mail_send)
      → ShadowOnlyTurnEngine.execute_turn()
        → _wait_for_shadow_ready_status()   [polling loop, _TurnMonitor.observe_readiness()]
        → _capture_shadow_baseline()
        → client.send_terminal_input()
        → _wait_for_shadow_completion()     [polling loop, _TurnMonitor.observe_completion()]
          → _build_mail_shadow_completion_observer()
            → build_shadow_mail_result_surface_payloads()
            → shadow_mail_result_contract_reached()  ← BUG: loose substring match
    → houmao realm-controller send-prompt (receiver_check)
      → [same engine, same observer pipeline]
```

### B. Shadow Parser Classification Chain (Claude)

```
ClaudeCodeShadowParser.parse_snapshot(scrollback, baseline_pos)
  → normalize_shadow_output(strip_ansi(scrollback))
  → _resolve_preset(scrollback)              # banner version detection → preset selection
  → _detect_output_variant(clean, compiled)   # priority: menu > spinner > marker > idle
  → _build_surface_assessment(clean, compiled, metadata)
    → _tail_lines(clean, 100)                 # take last 100 lines
    → _operator_blocked_excerpt(tail)         # scan for approval/trust/option patterns
    → _contains_processing_spinner(tail)      # scan for spinner pattern
    → _active_prompt_payload(tail, preset)    # last non-empty line with prompt char
    → _classify_surface_axes(...)             # if/elif priority chain → business_state + input_mode
  → _build_dialog_projection(raw, clean, metadata, projector, context)
    → projector.project(normalized_text, context)  # line-by-line drop/keep rules
    → finalize_projected_dialog()
```

### C. _TurnMonitor State Transitions

```
readiness phase:
  observe_readiness() called per poll
    is_unknown_for_stall? → unknown timer → stalled (after 30s)
    availability unsupported/disconnected? → failed
    is_operator_blocked? → blocked_operator
    is_submit_ready? → [exit loop, proceed to submit]
    else → awaiting_ready (keep polling)

completion phase:
  record_submit(baseline_projection)  # sets baseline for diffing
  observe_completion() called per poll
    check projection drift: dialog_text != baseline → m_saw_projection_change = True
    check working: business_state=="working" → m_saw_working = True
    is_unknown_for_stall? → unknown timer → stalled
    availability unsupported/disconnected? → failed
    is_operator_blocked? → blocked_operator
    business_state=="working"? → in_progress
    is_submit_ready? AND (saw_working OR saw_projection_change)? → completed  ← SINGLE SAMPLE!
    is_submit_ready? AND !(saw_working OR saw_projection_change)? → submitted_waiting_activity
    else → submitted_waiting_activity
```

### D. HTT Worktree Failure Cascade (Real-Agent Run)

Source: `context/issues/known/issue-real-agent-htt-worktree-runs-mix-snapshot-and-host-state.md`

The following cascade was observed during a hack-through-testing run in a disposable worktree. Each failure was worked around to expose the next:

```
Layer 1: Source snapshot (code-only worktree)
  ✗ Credential profiles missing — gitignored api-creds/ not in snapshot
  → Workaround: symlink credentials from host checkout

Layer 2: Tool runtime state (CAO home)
  ✗ CAO rejects workdir outside derived home directory
  → Workaround: widen CAO home to include demo project dir

Layer 3: Tool login/setup state (ambient host state)
  ✗ Tool shows installer/banner/setup prompt instead of idle prompt
  → Shadow parser sees noise, not the expected steady-state TUI
  → Readiness gate: either times out (unknown) or raises awaiting_operator
  → No recovery path in automation

Layer 4: TUI parse contract (shadow parser)
  ✗ Mailbox turn: terminal contains prompt echo + installer noise
  ✗ Sentinel completion observer matches echoed sentinels in prompt text
  ✗ Final parser rejects: "expected exactly one sentinel-delimited payload"
  → Root cause masked by layers 1-3 in main checkout
```

**Key insight:** The shadow parser appeared to be the failing component, but it was actually the last in a four-layer cascade. In the main checkout, layers 1-3 are silently satisfied by ambient host state. The worktree removed that ambient context, exposing that the parser's apparent reliability was partially environmental, not structural.

This means parser fixes alone (4.2–4.5) are necessary but not sufficient. The capability probe (4.7.1) addresses layer 3 at the parser boundary. The four-root run model (4.7 / HTT issue recommendations) addresses layers 1-2 at the run planner level.

### E. Four-Root Environmental Model

From the HTT issue, the roots that must all be correct for a real-agent run:

```
┌──────────────────────────────────────────────────────┐
│ Run Context                                          │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ source_root │  │ runtime_root │  │ tool_state  │ │
│  │ (code)      │  │ (houmao-     │  │ (tool home, │ │
│  │             │  │  managed)    │  │  login,     │ │
│  │             │  │              │  │  trust)     │ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘ │
│         │                │                 │         │
│         │    ┌───────────┴──────┐          │         │
│         │    │ project_workdir  │          │         │
│         │    │ (launched dir)   │          │         │
│         │    └─────────────────┘          │         │
│         │                                  │         │
│  ┌──────┴──────────────────────────────────┴──────┐  │
│  │ external_prereqs                               │  │
│  │ (credentials, API keys, auth tokens)           │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Main checkout: all roots overlap implicitly         │
│  Clean worktree: each root must be supplied          │
│  → Parser sees failures from ANY missing root        │
└──────────────────────────────────────────────────────┘
```
