# Issue 009: Codex Shadow Post-Completion Oscillation - Historical Progress Lines Keep Finished Turns Active

## Priority
P1 - A finished Codex turn can keep bouncing between active and complete states instead of settling to a stable idle prompt.

## Status
Known as of 2026-03-18.

## Summary

In a live `scripts/demo/cao-dual-shadow-watch/run_demo.sh` session, Codex completed a real prompt, printed a final summary, and returned to a visible prompt surface, but the shadow-watch monitor did not settle. Instead, the monitor kept flipping Codex between active and complete states.

The observed mixed state is internally contradictory:

- `business_state=working`
- `input_mode=freeform`
- `ui_context=normal_prompt`
- `cao_status=completed`
- `readiness_state=waiting`
- `completion_state=in_progress`

That combination means the parser thinks the tool is still working while also claiming the prompt is open and freeform. Once that contradictory observation reaches the monitor, the completion tracker can reset back to `in_progress` even though the user-visible TUI has already finished.

## Reproduction

1. Start the live dual shadow-watch demo with a fresh run root:

```bash
RUN_ROOT="/tmp/cao-dual-shadow-watch-$(date -u +%Y%m%d-%H%M%SZ)"
scripts/demo/cao-dual-shadow-watch/run_demo.sh start --run-root "$RUN_ROOT"
```

2. Inspect the persisted state and attach to the printed Codex and monitor tmux sessions:

```bash
scripts/demo/cao-dual-shadow-watch/run_demo.sh inspect --run-root "$RUN_ROOT" --json
```

3. In the Codex session, submit:

```text
Explain src/projection_demo/formatting.py
```

4. After that turn finishes, submit:

```text
Add a small helper to src/projection_demo/checks.py and explain the diff
```

5. Wait until Codex prints a normal finished-answer summary and test result, then watch the monitor. Instead of settling to stable `completed` and then `ready`, Codex can keep oscillating.

## Inline Evidence

### 1. Finished-looking Codex screen still carried a historical progress line

The live Codex pane had already reached a normal post-answer shape:

```text
• The patch is in place. I'm running the small test file now to make sure the new helper and export behave exactly as intended.

• Ran PYTHONPATH=src pytest -q tests/test_projection_demo.py
  └ ...                                                                      [100%]
    3 passed in 0.01s

• Working (40s • esc to interrupt)

› Run /review on my current changes
```

The important detail is that the screen now contains both:

- a visible idle prompt line: `› Run /review on my current changes`
- an older progress line: `• Working (40s • esc to interrupt)`

### 2. The monitor reset completion after the second prompt landed

The transition stream showed the second prompt correctly resetting completion:

```text
2026-03-18T18:03:37+00:00 codex: cao_status: 'completed' -> 'processing'; business_state: 'idle' -> 'working'; readiness_state: 'ready' -> 'waiting'; completion_state: 'completed' -> 'in_progress'; projection_changed: True -> False
2026-03-18T18:03:38+00:00 codex: cao_status: 'processing' -> 'idle'; business_state: 'working' -> 'idle'; readiness_state: 'waiting' -> 'ready'; completion_state: 'in_progress' -> 'candidate_complete'; projection_changed: False -> True
```

That reset is expected when a new prompt is submitted.

### 3. After the final summary, the state never fully settled

Later samples still showed Codex in a contradictory active state even though the answer had already finished:

```text
cao_status=completed
business_state=working
input_mode=freeform
ui_context=normal_prompt
readiness_state=waiting
completion_state=in_progress
```

The transition stream then kept flipping terminal status instead of reaching a quiet steady state:

```text
2026-03-18T18:04:14+00:00 codex: cao_status: 'processing' -> 'completed'
2026-03-18T18:04:16+00:00 codex: cao_status: 'completed' -> 'processing'
2026-03-18T18:04:16+00:00 codex: cao_status: 'processing' -> 'completed'
2026-03-18T18:04:18+00:00 codex: cao_status: 'completed' -> 'processing'
2026-03-18T18:04:19+00:00 codex: cao_status: 'processing' -> 'completed'
```

## Root Cause

This looks like a concrete Codex manifestation of the broader shadow-parser issues, but the live symptom is specific:

1. `CodexShadowParser._build_surface_assessment()` scans the last `status_tail_lines` as an unordered bag of signals.
2. `_active_prompt_payload()` walks backward until it finds any prompt line, so the bottom prompt `› Run /review on my current changes` still yields `has_idle_prompt=True`.
3. At the same time, `has_processing = any(_is_processing_line(line) for line in tail_lines)` stays true because a historical line like `• Working (40s • esc to interrupt)` is still present in scrollback.
4. `_classify_surface_axes()` combines those booleans into an impossible mixed state:
   - `input_mode="freeform"` and `ui_context="normal_prompt"` from the prompt line
   - `business_state="working"` from the historical progress line
5. The monitor treats any `business_state == "working"` observation as `completion_state="in_progress"`, which can repeatedly reset candidate completion instead of letting the quiet period finish.

So the core bug is not merely "Codex flickered once." The parser is producing a state tuple that violates its own implied surface model.

## Affected Code

- `src/houmao/agents/realm_controller/backends/codex_shadow.py`
  - `_build_surface_assessment()`
  - `_active_prompt_payload()`
  - `_is_processing_line()`
  - `_classify_surface_axes()`
- `src/houmao/demo/cao_dual_shadow_watch/monitor.py`
  - `AgentStateTracker.observe()`
  - `_is_submit_ready()`
  - `_classify_completion_surface()`

## Fix Direction

### A. Make processing detection cursor-aware

Do not let a historical progress line keep the surface in `working` after a later idle prompt is visible. The active surface should be anchored to the current prompt region, not to any matching line in the last 100 lines.

### B. Reject impossible axis combinations

The parser should not emit `business_state="working"` together with `input_mode="freeform"` and `ui_context="normal_prompt"`. If that combination is possible today, it should either be normalized to `idle+freeform` or surfaced as an explicit parser anomaly instead of a normal business state.

### C. Harden the monitor against contradictory parser output

As a defensive layer, the monitor should avoid resetting completion from a sample that claims:

- `business_state="working"`
- while also exposing a prompt-submit-ready surface

That would keep a parser contradiction from turning into visible dashboard oscillation while the parser itself is being tightened.

## Connections

- Concrete live-demo manifestation of `context/issues/known/issue-003-shadow-bag-of-signals-classification.md`
- Reinforces the lifecycle fragility described in `context/issues/known/issue-002-shadow-turn-monitor-imperative-timing.md`
- Related to `context/logs/code-reivew/20260318-shadow-parser-tui-state-detection-review.md`
