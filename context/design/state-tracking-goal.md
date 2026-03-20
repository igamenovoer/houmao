# TUI state tracking goal

Here is what we really want to track.

## Foundational observable state

These are the lowest-level facts we can observe from the live TUI surface. Higher-level turn state must be built on top of these facts rather than replacing them.

- Is the TUI accepting user input?
  Meaning: if the user types now, the text will land in the prompt-input area.
  Note: accepting input does not necessarily mean the TUI is idle. Some TUIs may accept prompt edits while an earlier turn is still in flight.

- Is the user actively editing the prompt-input area?
  Meaning: the prompt-input area is changing from user control.
  Note: for tmux-backed sessions, `send-keys` also counts as user input.

- Is the TUI visibly in a ready posture?
  Meaning: the surface looks ready to accept immediate submit for the next turn.
  Note: this is a visible-surface fact, not a claim that no background work exists anywhere in the tool.

- Is there an explicit interruption signal visible?
  Meaning: the surface shows that the active turn was interrupted by the user or by an equivalent stop action.

- Is there an explicit known-failure signal visible?
  Meaning: the surface shows an error, disconnection, unsupported state, or other specifically recognized failure pattern that prevents the turn from completing normally.
  Note: failure modes are not fully stable across tools and versions. Unmatched failure-like surfaces do not automatically become a dedicated failure state; they fall back to `turn_unknown`.

- Is the visible surface changing?
  Meaning: the prompt area, scrolling dialog area, tool transcript area, or other visible TUI region changed between observations.
  Important: a visible change does not automatically have a known cause. The user may hit `Tab`, `Left`, `Right`, or trigger repaint or other UI-local churn. Surface change is evidence, not automatic lifecycle meaning.

## Turn-processing state

These states are inferred over time from the observable facts above. We do not maintain a separate command-processing model. Anything submitted through the TUI is treated as one turn lifecycle.

- `turn_ready`
  Meaning: the visible surface indicates the next submit would be accepted immediately.

- `turn_active`
  Meaning: the tracker has enough evidence that a submitted turn is in flight.
  Active-turn evidence may include:
  - scrolling dialog content growth
  - tool transcript or tool-call region changes that look turn-related
  - explicit activity strings or banners
  - visible progress or spinner signals

- `turn_unknown`
  Meaning: the tracker cannot safely classify the current posture as `turn_ready` or `turn_active`, and it cannot safely claim a supported terminal outcome.
  Note: ambiguous menus, selection boxes, permission prompts, tool-owned popups, slash-command UI, and version-specific interactive surfaces fall here unless stronger evidence supports another state.

- Did the active turn end in one of these terminal outcomes?
  - `turn_success`
    Meaning: the turn reached a stable ready posture after post-submit activity and any required settle window.
  - `turn_interrupted`
    Meaning: the turn was interrupted by the user or by an equivalent stop action.
  - `turn_known_failure`
    Meaning: the turn ended in a specifically recognized failure mode captured by supported TUI string matching or another strong tool-specific signal.

## Important constraints

- We do not distinguish chat turns from slash commands.
  Reason: a prompt shaped like `/<command-name>` is not a reliable discriminator. It may be a built-in command, a user-defined subcommand that sends a predefined prompt, or a typo that the TUI forwards literally to the model.

- We do not publish a dedicated operator-handoff state.
  Reason: menus, selection boxes, permission prompts, and similar interactive UI are tool-specific and unstable across versions. Unless stronger evidence exists, they collapse into `turn_unknown`.

- We do not publish a generic catch-all failure outcome.
  Reason: many failure-looking TUI surfaces are unstable, partial, or version-specific. Only specifically recognized failure signatures become `turn_known_failure`; unmatched cases collapse into `turn_unknown`.

- Progress bars, spinners, and similar activity signals are supporting evidence only.
  If such a signal is visible, that is strong evidence that a turn is active.
  If no such signal is visible, that does not mean no turn is active.

- Generic surface change is not a known-cause signal by default.
  Unexplained UI churn may update diagnostics or visible-surface state without advancing turn lifecycle state.

- Turn state should be inferred from a combination of:
  - prompt-area changes
  - scrolling dialog-content changes
  - explicit visible strings or signs
  - stable return to ready posture
  - ReactiveX-driven timing for settle and degraded-visibility behavior
