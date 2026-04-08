# Issue: Houmao Server Interactive Prompt Turns Do Not Surface Lifecycle Transitions

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P1 - The server-backed shadow-watch demo cannot show active/completing turn state for direct interactive prompting, which is now the main purpose of the demo.

## Status
Diagnosed and fixed in the working tree on 2026-03-19.

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

Dense server-side tracing confirmed the first failing stage: direct interactive tmux prompting never hit the server-owned prompt-submission hook.

`LiveSessionTracker.note_prompt_submission()` in `src/houmao/server/tui/tracking.py` only armed turn-anchored completion monitoring when the server itself recorded a successful prompt submission. That server-owned path existed, but the prompt-and-observe demo drove the tools by direct interactive input in the tmux pane. In that flow, the tracker never received a prompt-submission event, so it stayed in:

- `completion_authority="unanchored_background"`
- `turn_anchor_state="absent"`
- `completion_monitoring_armed=false`

That is why authoritative `candidate_complete` / `completed` never appeared on the original failing path.

The dense trace also confirmed that the fallback unanchored path was too weak for this use case. During visible prompt execution, the parser still reported `business_state=idle` and `input_mode=freeform`, so background reduction alone stayed conservative and flat even while the pane showed real work.

There was a second implementation risk during the fix: a naive "stable ready surface changed" inference rule produced false `candidate_complete` / `completed` turns from idle Claude UI chrome churn. The final fix therefore had to infer anchors only for materially larger ready-surface growth, not for small prompt-area repainting.

## Resolution

The fix has three parts:

1. Add dense, env-gated server-side tracking traces in:
   - `src/houmao/server/app.py`
   - `src/houmao/server/service.py`
   - `src/houmao/server/tui/tracking.py`
   - `src/houmao/server/tracking_debug.py`
2. Add a maintainer-facing automatic repro runner at:
   - `src/houmao/demo/houmao_server_dual_shadow_watch/tracking_debug.py`
   - `scripts/demo/houmao-server-dual-shadow-watch/scripts/tracking_debug.py`
3. Teach `LiveSessionTracker.record_cycle()` to infer a turn anchor for direct interactive prompting when:
   - the previous visible state was stable and submit-ready
   - no active anchor exists
   - the visible projection changed materially enough to look like a real prompt turn rather than ambient UI churn

With that fix in place:

- server `/terminals/{id}/input` still arms `source="terminal_input"` anchors
- direct tmux prompting now arms `source="surface_inference"` anchors
- the direct-tmux path surfaces `candidate_complete` transitions instead of staying flat
- the tighter material-growth guard prevents the earlier false-positive anchors from idle Claude welcome/prompt repainting

## Verification

The dense debug workflow and final fixed evidence are preserved under:

```text
tmp/houmao-server-tracking-debug/20260319-190736
```

Key artifacts:

- `summary/run-summary.json`
- `summary/timeline.md`
- `events/*.ndjson`
- `artifacts/server-input/*`
- `artifacts/direct-tmux/*`

The final summary for that run shows:

- `server-input`
  - `app_input_requests=1`
  - `service_prompt_submission_recorded=1`
  - `turn_anchor_sources=["terminal_input"]`
- `direct-tmux`
  - `app_input_requests=0`
  - `service_prompt_submission_recorded=0`
  - `turn_anchor_sources=["surface_inference"]`

So the original root cause is confirmed, and the fixed direct-tmux path now surfaces a tracked lifecycle transition without regressing into idle UI-churn false positives.

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

Implemented by teaching the tracker to infer a guarded `surface_inference` anchor for direct interactive prompting while preserving the existing `terminal_input` server route.

### C. Strengthen the unanchored fallback

Even without a turn anchor, the tracker should not report `ready` / `inactive` while the visible projection is actively changing and the tool is visibly executing work. At minimum, the fallback path should surface an honest active state or an explicit "unanchored lifecycle" limitation instead of pretending the tool is idle and ready.

### D. Add integration coverage for real interactive turns

Implemented as the automatic tracking-debug workflow plus focused unit tests around:

- debug sink gating and emission
- guarded surface-inference anchoring
- no false-positive inference for small stable ready-surface churn

## Connections

- Breaks the intended purpose of `scripts/demo/houmao-server-dual-shadow-watch/`
- Related to `context/issues/known/issue-002-shadow-turn-monitor-imperative-timing.md` because lifecycle semantics still depend on turn anchoring and timing posture
- The current OpenSpec/demo refactor assumed server-tracked lifecycle was ready to back prompt-and-observe interactive workflows; this issue shows that assumption is incomplete for direct pane-driven prompting
