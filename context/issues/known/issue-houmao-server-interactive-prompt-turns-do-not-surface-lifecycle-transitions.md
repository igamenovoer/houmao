# Issue: Houmao Server Interactive Prompt Turns Do Not Surface Lifecycle Transitions

## Priority
P1 - The server-backed shadow-watch demo cannot show active/completing turn state for direct interactive prompting, which is now the main purpose of the demo.

## Status
Known as of 2026-03-19.

## Summary

In a live `scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh` interactive session, direct prompts submitted to the Claude pane visibly executed and produced real side effects, but the server-tracked lifecycle surface stayed flat.

The tracker did react at the visible-state layer:

- `stability.stable` flipped to `false` during the turn
- the parsed projection captured the new prompt and output
- the longer turn wrote a real `notes.txt` file in the demo project

But the operator-facing lifecycle never advanced beyond the startup posture:

- `operator_state.status=ready`
- `operator_state.readiness_state=ready`
- `operator_state.completion_state=inactive`
- `lifecycle_authority.completion_authority=unanchored_background`
- `lifecycle_authority.turn_anchor_state=absent`

`recent_transitions` also stayed stuck at the original startup transitions, so the monitor had no turn-level lifecycle event to show.

This means the server is currently tracking visible projection change, but not the actual interactive turn lifecycle that the demo now exists to demonstrate.

## Reproduction

1. Stage the interactive demo workflow:

```bash
scripts/demo/houmao-server-dual-shadow-watch/autotest/run_autotest.sh case-interactive-shadow-validation
```

2. Attach to the Claude tmux session printed by the case, or inject input into that pane.

3. Submit a short prompt:

```text
Reply with the single word READY and stop.
```

4. Observe that the Claude pane replies, and inspect the server-tracked state:

```bash
scripts/demo/houmao-server-dual-shadow-watch/run_demo.sh inspect --run-root "$RUN_ROOT" --json
```

5. Submit a longer prompt with a concrete side effect:

```text
Create a file named notes.txt containing exactly 20 numbered lines. Each line must be a different short sentence about test repeatability. After writing the file, reply with DONE and nothing else.
```

6. Observe that the pane shows active work and `notes.txt` is created, but the server-tracked lifecycle still remains `ready` / `inactive` / `unanchored_background`.

## Captured Run

The failing interactive run captured during investigation is:

```text
.agent-automation/hacktest/houmao-server-dual-shadow-watch-demo/runs/20260319-182212/case-interactive-shadow-validation
```

Useful local evidence from that run:

- `artifacts/baseline-inspect.json`
- `demo-run/monitor/samples.ndjson`
- `demo-run/monitor/transitions.ndjson`
- `demo-run/projects/claude/notes.txt`

## Inline Evidence

### 1. The transition stream never moved beyond startup

The captured `demo-run/monitor/transitions.ndjson` only recorded the initial Claude and Codex startup transitions:

```text
2026-03-19T18:22:24+00:00 claude: transport_state/process_state/parse_status/operator_status/readiness_state/surface_*
2026-03-19T18:22:32+00:00 codex: transport_state/process_state/parse_status/operator_status/readiness_state/surface_*
```

No later transition was emitted for either interactive Claude prompt.

### 2. The short prompt broke visible stability but not lifecycle posture

At `2026-03-19T18:23:36+00:00`, the Claude sample showed the prompt in the parsed surface and `stability.stable=false`, but lifecycle remained flat:

```text
completion_authority=unanchored_background
turn_anchor_state=absent
status=ready
readiness_state=ready
completion_state=inactive
business_state=idle
stable=false
```

So the tracker knew the visible surface had changed, but still did not surface an active turn.

### 3. The longer prompt completed a real file-writing task while lifecycle stayed flat

At `2026-03-19T18:29:05+00:00`, the Claude sample already contained:

```text
Reply with the single word READY and stop.
READY
Create a file named notes.txt ...
Write(notes.txt)
Wrote 20 lines to notes.txt
DONE
commit this
```

The created file is real:

```text
.agent-automation/hacktest/houmao-server-dual-shadow-watch-demo/runs/20260319-182212/case-interactive-shadow-validation/demo-run/projects/claude/notes.txt
```

It contains 20 lines, verified with:

```text
wc -l .../notes.txt
20 .../notes.txt
```

But the same sample still reported:

```text
completion_authority=unanchored_background
turn_anchor_state=absent
status=ready
readiness_state=ready
completion_state=inactive
projection_changed=false
```

That is an incorrect lifecycle summary for a turn that visibly ran, wrote a file, and completed.

## Root Cause

The likely root cause is a turn-anchor gap in server tracking for direct interactive prompting.

`LiveSessionTracker.note_prompt_submission()` in `src/houmao/server/tui/tracking.py` only arms turn-anchored completion monitoring when the server itself records a successful prompt submission. That server-owned path exists, but the prompt-and-observe demo currently drives the tools by direct interactive input in the tmux pane. In that flow, the tracker never receives a prompt-submission event, so it remains in:

- `completion_authority="unanchored_background"`
- `turn_anchor_state="absent"`
- `completion_monitoring_armed=false`

That explains why authoritative `candidate_complete` / `completed` never appear.

What remains unresolved is why the unanchored path also failed to surface a meaningful active-turn signal. During visible prompt execution, the tracker still reported `business_state=idle` and `status=ready`, even though the pane showed prompt handling and file writing. So there are likely two issues:

1. direct interactive prompting does not arm the server-owned turn anchor
2. the fallback unanchored reduction is too weak or too incorrect for live prompt-and-observe use

## Affected Code

- `src/houmao/server/tui/tracking.py`
  - `LiveSessionTracker.note_prompt_submission()`
  - `LiveSessionTracker.record_cycle()`
  - `LiveSessionTracker._reduction_from_current_snapshots()`
  - `LiveSessionTracker._current_lifecycle_authority()`
  - `_build_operator_state()`
- `src/houmao/server/service.py`
  - `note_prompt_submission()`
- `src/houmao/server/app.py`
  - server-owned input path that records prompt submissions when input flows through the server API

## Fix Direction

### A. Decide the supported contract for the demo

If `houmao-server-dual-shadow-watch` is meant to show server-tracked states while Claude/Codex are interactively prompted, then direct interactive prompting must produce honest lifecycle state. The current "visible change only, lifecycle stays ready/inactive" posture is not sufficient.

### B. Ensure interactive prompt submission reaches the tracker

One of these needs to happen:

- route demo prompt submission through a server-owned input path that calls `note_prompt_submission()`
- add a demo/runtime helper that explicitly records prompt submission when the operator sends a turn into the live pane
- or teach the tracker to infer a turn anchor from direct interactive prompt submission when operating in shadow-watch mode

### C. Strengthen the unanchored fallback

Even without a turn anchor, the tracker should not report `ready` / `inactive` while the visible projection is actively changing and the tool is visibly executing work. At minimum, the fallback path should surface an honest active state or an explicit "unanchored lifecycle" limitation instead of pretending the tool is idle and ready.

### D. Add integration coverage for real interactive turns

The current server tests cover the prompt-submission API path, but the failing demo path is direct interactive prompting. Add an integration test that:

- starts the live demo
- submits a real prompt through the supported interactive path
- asserts that at least one non-startup lifecycle transition is emitted

## Connections

- Breaks the intended purpose of `scripts/demo/houmao-server-dual-shadow-watch/`
- Related to `context/issues/known/issue-002-shadow-turn-monitor-imperative-timing.md` because lifecycle semantics still depend on turn anchoring and timing posture
- The current OpenSpec/demo refactor assumed server-tracked lifecycle was ready to back prompt-and-observe interactive workflows; this issue shows that assumption is incomplete for direct pane-driven prompting
