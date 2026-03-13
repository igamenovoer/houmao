# Contract And Behaviour Difference

## Purpose

This note captures the practical behavior difference between:

- the current `shadow_only` implementation in `src/gig_agents/agents/realm_controller/backends/cao_rest.py`, and
- the proposed contracts in `contracts/claude-state-contracts.md` and `contracts/turn-monitor-contracts.md`.

Claude Code is used as the main example, but the same runtime difference applies to Codex.

## Short Version

The parser-side Claude state vocabulary is mostly unchanged. The major change is runtime semantics:

- current implementation treats `ready_for_input` as actionable immediately,
- proposed contracts treat `ready_for_input` as a candidate that must also become quiet/stable for some window before readiness or completion is accepted.

In other words:

```text
Current:
parser state drives readiness/completion directly

Proposed:
parser state proposes readiness/completion
runtime quiescence confirms it
```

## Current Implementation Summary

Today the runtime does these things:

- readiness returns immediately when `snapshot.surface_assessment.accepts_input` is `true`
- completion returns immediately when `accepts_input=true` and runtime has already seen either:
  - post-submit `working`, or
  - projected-dialog change
- `unknown` becomes `stalled` after one continuous timer, even if the tmux output is still changing

Relevant current code:

- readiness fast-path: `cao_rest.py:940-941`
- completion terminality: `cao_rest.py:391-394`
- unknown-to-stalled timing: `cao_rest.py:432-452`

## Proposed Contract Summary

The new contracts add a runtime-owned quiescence layer:

- `ready_for_input` means “looks ready now,” not “submit now”
- runtime waits for a ready quiet window before submitting
- runtime waits for a completion quiet window before completing
- new transport changes restart those timers
- `unknown` with ongoing transport change is treated as active-but-unclassified, not stalled
- `stalled` means quiet unknown, not merely long unknown

Relevant contract notes:

- Claude parser/runtime boundary: `contracts/claude-state-contracts.md`
- runtime quiescence and lifecycle rules: `contracts/turn-monitor-contracts.md`

## Concrete Examples

Assume these example policy values:

- `ready_quiet_window_seconds = 0.5`
- `completion_quiet_window_seconds = 1.0`
- `unknown_to_stalled_timeout_seconds = 30`

These values are illustrative only; the semantic difference is the important part.

### Example 1: Pre-submit prompt appears ready, but keeps repainting

Timeline:

- `t=0.0`: Claude snapshot shows `❯`; parser says `ready_for_input`, `accepts_input=true`
- `t=0.2`: footer or status text changes
- `t=0.4`: another tmux-visible repaint occurs
- `t=0.9`: no further changes

Current behavior:

- runtime submits immediately at the first poll where `accepts_input=true`

Why:

- readiness path exits immediately on `accepts_input=true`

Proposed contract behavior:

- runtime does not submit at `t=0.0`
- runtime waits until the ready surface has remained quiet for the full ready window
- each new tmux-visible change restarts that countdown

Behavioral meaning:

- current behavior is “ready once”
- proposed behavior is “ready and settled”

### Example 2: Post-submit prompt returns briefly before output fully settles

Timeline:

- `t=0.0`: prompt submitted
- `t=0.2`: Claude shows spinner; parser says `working`
- `t=0.8`: projected dialog changes; response text appears
- `t=1.1`: prompt `❯` returns for one poll
- `t=1.3`: another tmux-visible change arrives
- `t=2.4`: no more changes

Current behavior:

- runtime completes as soon as it sees `accepts_input=true` again, because it already observed progress evidence

Why:

- current completion rule is `ready again` plus (`working_seen` or `projection_changed`)

Proposed contract behavior:

- runtime does not complete at `t=1.1`
- the change at `t=1.3` restarts the completion quiet timer
- completion happens only after progress evidence exists, the surface is ready again, and no further transport change occurs for the full completion quiet window

Behavioral meaning:

- current behavior is “ready again after progress”
- proposed behavior is “ready again after progress and quiet”

### Example 3: Unknown state with visible output churn

Timeline:

- parser stays at `unknown`
- tmux snapshot changes every 2 seconds
- this continues for 40 seconds

Current behavior:

- runtime still enters `stalled` after the unknown timeout expires

Why:

- the current unknown timer is based on elapsed time since unknown began
- it is not reset by ongoing tmux changes

Proposed contract behavior:

- runtime does not enter `stalled` yet
- each new transport change restarts the unknown countdown
- this is treated as active-but-unclassified rather than stalled

Behavioral meaning:

- current behavior says “unknown long enough means stalled”
- proposed behavior says “quiet unknown long enough means stalled”

This is one of the most important behavior changes in the new contract.

### Example 4: Unknown state with a frozen screen

Timeline:

- parser says `unknown`
- tmux snapshot stops changing entirely
- 30 seconds pass

Current behavior:

- runtime enters `stalled`

Proposed contract behavior:

- runtime also enters `stalled`

Behavioral meaning:

- outcome is the same
- the contract definition is tighter:
  - current: `unknown` for long enough
  - proposed: `unknown` and quiet for long enough

### Example 5: Working was seen, but the surface keeps changing after prompt return

Timeline:

- post-submit Claude clearly enters `working`
- prompt later returns
- some footer/progress repaint or response-tail change still occurs after that

Current behavior:

- if runtime has already seen `working`, the prompt returning is enough to complete immediately

Proposed contract behavior:

- prompt return is still not sufficient
- runtime also requires a completion quiet window with no further transport change

Behavioral meaning:

- even the “working was definitely seen” path becomes stricter under the contract
- the contract is explicitly protecting against prompt reappearance before the TUI is actually settled

## Major Semantic Difference

Using Claude as the example, the major semantic difference is not primarily a new parser-state vocabulary.

It is this:

- current implementation is parser-state driven with one projection/baseline progress guard
- proposed contracts are parser-state plus transport-quiescence driven

That shifts the meaning of these runtime decisions:

- readiness: from `accepts_input now` to `accepts_input and quiet`
- completion: from `ready again after progress` to `ready again after progress and quiet`
- stalled: from `unknown for long enough` to `quiet unknown for long enough`

## Practical Consequence

If the current implementation is biased toward fast transitions, the new contract is biased toward stable transitions.

That buys stronger protection against:

- premature submit on a surface that is still repainting,
- premature completion on a prompt that reappears before output settles,
- false `stalled` classification while the TUI is visibly still active.
