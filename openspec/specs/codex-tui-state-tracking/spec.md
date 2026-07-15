# codex-tui-state-tracking Specification

## Purpose
Define the interactive Codex TUI tracked-state profile and signal semantics used by the shared tracked-TUI core.
## Requirements
### Requirement: Codex TUI tracking is limited to the interactive Codex screen surface
The repository SHALL model Codex interactive tracked-TUI behavior under a dedicated `codex_tui` app family whose input is raw captured screen text from the interactive Codex TUI surface.

That capability SHALL be limited to the interactive TUI case that requires raw snapshot parsing and keyboard-style interaction. It SHALL NOT treat structured headless Codex control modes such as `codex app-server` or prompt-oriented Codex CLI execution as part of the Codex tracked-TUI surface contract.

#### Scenario: Interactive Codex TUI is tracked from raw screen snapshots
- **WHEN** a host captures raw interactive Codex pane snapshots from tmux or a replay artifact
- **THEN** the standalone tracker resolves Codex through the `codex_tui` tracked-TUI capability
- **AND THEN** state reduction is based on those raw interactive TUI snapshots

#### Scenario: Structured headless Codex modes stay outside tracked-TUI scope
- **WHEN** a repo-owned flow uses a structured Codex control mode with an upstream machine contract rather than raw interactive screen snapshots
- **THEN** that flow does not require the `codex_tui` tracked-TUI capability for its state semantics
- **AND THEN** the tracked-TUI subsystem does not re-model that headless contract through screen-scraping rules

### Requirement: Codex TUI single-snapshot signals come from current visible surface facts
The `codex_tui` profile SHALL derive its single-snapshot facts from the current visible surface only.

At minimum, the profile SHALL be able to recognize:
- agent-turn-backed activity rows,
- in-flight tool or command transcript cells,
- blocking operator-interaction overlays,
- exact interruption surfaces,
- steer-resubmission handoff surfaces,
- prompt-adjacent terminal failure surfaces for the current turn, including red error-style blocks and warning-style failure blocks recognized from bounded structure plus essential semantic tokens,
- recoverable degraded chat-context evidence when a prompt-adjacent terminal failure matches the compact/server degraded family through bounded compact/server semantics rather than an exact full-sentence literal,
- live-edge retry or reconnect status surfaces as current active evidence when they match bounded recovery semantics for the current turn, and
- ready-composer posture, including prompt-area `editing_input` semantics derived through a version-selected prompt behavior variant.

Agent-turn-backed activity rows, in-flight tool cells, prompt-adjacent terminal failure evidence, recoverable degraded chat-context evidence, and live-edge retry or reconnect status SHALL be derived from bounded current-turn surface regions near the prompt or live edge rather than from arbitrary historical transcript rows preserved in scrollback above the current turn.

Historical Codex running rows, tool transcript cells, terminal failure blocks, warning rows, or retry text outside those bounded current-turn regions SHALL NOT by themselves produce current single-snapshot active evidence, current-error evidence, `known_failure`, or recoverable degraded chat-context evidence.

Current prompt-adjacent terminal failure evidence SHALL block success settlement for the current turn, but it SHALL NOT by itself force `surface.accepting_input`, `surface.editing_input`, `surface.ready_posture`, or the resulting prompt-ready posture away from the current prompt-area facts.

Recognized warning-style prompt-adjacent terminal failures MAY produce `known_failure` when the selected Codex profile identifies a bounded terminal failure family strong enough to justify that outcome.

Live-edge retry or reconnect status SHALL block success settlement and SHALL count as active-turn evidence while that bounded current-turn recovery surface remains visible.

Recoverable degraded chat-context evidence SHALL remain distinct from prompt readiness, successful completion, and `known_failure`. A snapshot MAY be prompt-ready and also have recoverable degraded chat context.

Prompt-adjacent terminal failures that do not match the compact/server degraded family SHALL NOT produce recoverable degraded chat-context evidence.

Ambient warnings that do not belong to a bounded prompt-adjacent terminal failure block or bounded live-edge retry surface SHALL NOT by themselves produce current-error evidence, `known_failure`, active evidence, or degraded chat-context evidence.

That prompt behavior variant SHALL consume prompt-area snapshot content derived from the raw interactive surface rather than stripped prompt text alone.

The prompt behavior variant MAY use style, layout, text, or other prompt-local evidence to recognize placeholder presentation, and the repository SHALL NOT require one specific prompt-classification mechanism as the stable contract.

If the prompt remains visible but the selected prompt behavior variant cannot confidently distinguish placeholder presentation from real draft input, the `codex_tui` profile SHALL expose `editing_input=unknown` for that current snapshot rather than manufacturing `editing_input=yes` or `editing_input=no`.

The single-snapshot layer SHALL NOT require host parser metadata as input.

#### Scenario: Agent-turn-backed activity row counts as current active evidence
- **WHEN** the current Codex TUI snapshot shows an agent-turn-backed running row or in-flight tool cell for the live latest-turn region
- **THEN** the `codex_tui` profile exposes active-turn evidence from that current surface
- **AND THEN** the shared tracker can classify the current turn as active without requiring a separate host parser contract

#### Scenario: Historical running row outside the live edge does not count as current active evidence
- **WHEN** the tmux-backed Codex snapshot still contains a historical `• Working (... esc to interrupt)` row above the current prompt-ready live region
- **AND WHEN** that historical row is outside the current live latest-turn surface
- **THEN** the `codex_tui` profile does not expose current single-snapshot active evidence from that historical row alone
- **AND THEN** the tracker does not keep the current turn active solely because that stale transcript row remains in scrollback

#### Scenario: Blocking overlay degrades posture without manufacturing a terminal result
- **WHEN** the current Codex TUI snapshot shows an approval modal, request-user-input modal, MCP elicitation, or app-link suggestion overlay
- **THEN** the `codex_tui` profile exposes a blocking interactive surface for that snapshot
- **AND THEN** the shared tracker does not manufacture success, interruption, or known-failure from that overlay alone

#### Scenario: Terminal failure block without known-family evidence blocks success without becoming known-failure
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent terminal failure block that does not match a recognized known-failure family
- **THEN** the `codex_tui` profile exposes current-error evidence for that current turn
- **AND THEN** the shared tracker blocks success for that turn without emitting `known_failure` from that signal alone

#### Scenario: Warning-style terminal failure near prompt preserves readiness and blocks success
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent warning-style failure block that matches a recognized bounded terminal-failure family
- **AND WHEN** the current prompt is visible, accepting input, not editing input, and not blocked by an overlay
- **THEN** the `codex_tui` profile preserves prompt-ready surface facts for that snapshot
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile does not require an exact full-sentence warning literal to recognize that failure family

#### Scenario: Live-edge retry status remains active instead of prompt-ready success
- **WHEN** the current Codex TUI snapshot shows a bounded live-edge retry or reconnect status surface for the current turn
- **THEN** the `codex_tui` profile exposes active-turn evidence for that current turn
- **AND THEN** the profile blocks success candidacy while that retry surface remains visible
- **AND THEN** the tracker does not treat that surface as a prompt-ready successful return solely because a prompt line is also visible

#### Scenario: Historical failure or warning outside the bounded current-turn scope does not count
- **WHEN** the tmux-backed Codex snapshot contains an old failure block, warning row, or compact/server-error text in scrollback above the current prompt-ready live region
- **AND WHEN** the bounded prompt-adjacent and live-edge regions do not contain a current failure or retry surface
- **THEN** the `codex_tui` profile does not expose current-error evidence, `known_failure`, active evidence, or recoverable degraded chat-context evidence from that historical text alone
- **AND THEN** the tracker does not block prompt-ready posture solely because a long transcript still shows an old error above the current turn

#### Scenario: Ambient warning does not mutate current turn state
- **WHEN** the current Codex TUI snapshot contains a visible warning row that does not belong to the bounded prompt-adjacent terminal failure block and does not belong to the bounded live-edge retry surface
- **THEN** the `codex_tui` profile does not expose current-error evidence, `known_failure`, or active evidence from that warning alone
- **AND THEN** the tracker preserves the current turn decision from stronger current-turn evidence instead of treating the warning as terminal by default

#### Scenario: Terminal failure without compact or server semantics does not degrade chat context
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent terminal failure surface that does not match the compact/server degraded family
- **THEN** the `codex_tui` profile does not expose recoverable degraded chat-context evidence
- **AND THEN** gateway policy cannot require a context reset solely from that terminal failure

#### Scenario: Ready composer after terminal failure remains prompt-ready
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent terminal failure surface and a stable ready composer that accepts input with no draft editing
- **AND WHEN** the current surface has no active-turn evidence or blocking overlay
- **THEN** the `codex_tui` profile preserves prompt-ready surface facts for that snapshot
- **AND THEN** the shared tracker does not report the surface as non-ready solely because the previous visible turn contains an error

#### Scenario: Placeholder presentation does not count as editing
- **WHEN** the selected Codex prompt behavior variant classifies the visible prompt area as placeholder presentation
- **THEN** the `codex_tui` profile reports `editing_input=no`
- **AND THEN** visible placeholder text is not treated as a user draft only because it appears in the prompt area

#### Scenario: Real draft input remains editing even when text matches a known placeholder phrase
- **WHEN** the selected Codex prompt behavior variant classifies the visible prompt area as real user draft input
- **THEN** the `codex_tui` profile reports `editing_input=yes`
- **AND THEN** that result does not depend on whether the stripped draft text happens to equal one previously known placeholder string

#### Scenario: Dynamic placeholder text does not require a stable literal list
- **WHEN** Codex uses different placeholder wording within a supported prompt behavior family
- **THEN** the selected prompt behavior variant can still classify that prompt area as placeholder presentation
- **AND THEN** the `codex_tui` capability does not require the stable tracker contract to enumerate every placeholder literal

#### Scenario: Unrecognized prompt presentation yields unknown editing state
- **WHEN** the selected Codex prompt behavior variant cannot confidently distinguish placeholder presentation from real draft input for the current visible prompt area
- **THEN** the `codex_tui` profile reports `editing_input=unknown`
- **AND THEN** the tracker preserves that ambiguity for drift investigation instead of manufacturing a placeholder or draft conclusion

### Requirement: Prompt-adjacent compact errors are recoverable degraded context
The `codex_tui` profile SHALL classify a current prompt-adjacent compact/server terminal failure surface as recoverable degraded-context evidence rather than mandatory reset evidence.

When the current prompt-adjacent compact/server terminal failure surface is present, the profile SHALL expose current-error evidence for the current turn and SHALL prevent success candidacy for that surface.

When the current prompt-adjacent compact/server terminal failure surface is present and the current composer facts otherwise indicate prompt readiness, the profile SHALL preserve prompt readiness instead of forcing the input surface to unknown or active solely because of that error.

The profile SHALL derive this compact/server degraded classification from the bounded prompt-adjacent prompt region and from the essential compact/server semantics carried by that failure surface. It SHALL NOT require an exact full-sentence literal to classify the compact/server degraded family.

The profile SHALL NOT classify old compact/server failure text from arbitrary historical scrollback as current degraded-context evidence.

The profile SHALL NOT use a public state name that implies mandatory reset for this recoverable condition.

#### Scenario: Compact or server failure near prompt keeps promptable degraded state
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent terminal failure surface whose bounded text carries the essential compact/server degraded semantics
- **AND WHEN** the prompt is visible, accepting input, not editing input, not blocked by an overlay, and has no current active-turn evidence
- **THEN** the `codex_tui` profile exposes current-error evidence for the current turn
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile preserves prompt-ready input posture for downstream tracked-state reduction
- **AND THEN** the profile exposes recoverable degraded-context evidence without requiring a context reset

#### Scenario: Historical compact or server failure does not degrade current prompt state
- **WHEN** a Codex TUI snapshot contains an older compact/server failure surface in long scrollback above the current prompt area
- **AND WHEN** the bounded prompt-adjacent region near the current prompt does not contain that compact/server degraded family
- **THEN** the `codex_tui` profile does not expose degraded-context evidence from that historical failure
- **AND THEN** the profile does not expose current-error evidence solely because that historical failure remains visible

#### Scenario: Prompt-adjacent terminal failure without compact or server semantics remains a failure blocker only
- **WHEN** the current Codex TUI snapshot shows a prompt-adjacent terminal failure surface that does not match the compact/server degraded family
- **THEN** the `codex_tui` profile exposes terminal failure evidence for the current turn
- **AND THEN** the profile blocks success candidacy for that turn
- **AND THEN** the profile does not expose recoverable compact/server degraded-context evidence

### Requirement: Codex TUI temporal inference uses a sliding recent-snapshot window
The `codex_tui` profile SHALL be allowed to derive temporal hints from a sliding time window over recent snapshots rather than relying only on adjacent-snapshot comparison.

That temporal inference SHALL support Codex-specific cases where the visible running row may disappear while streamed answer content continues to grow.

The profile SHALL prefer degrading certainty when the recent snapshot window is too sparse or ambiguous rather than manufacturing active or successful turn outcomes from insufficient evidence.

#### Scenario: Hidden status row does not hide an active answering turn
- **WHEN** recent ordered Codex TUI snapshots within the current sliding window show continued latest-turn transcript growth
- **AND WHEN** the visible running row is absent in the newest snapshot
- **THEN** the `codex_tui` profile may still expose temporal active-turn evidence for the shared tracker
- **AND THEN** the tracker does not require a visible running row on every active Codex turn

#### Scenario: Sparse recent window degrades temporal inference
- **WHEN** the recent Codex TUI snapshot window is too sparse or inconsistent to support confident temporal inference
- **THEN** the `codex_tui` profile degrades that temporal evidence rather than manufacturing a stronger lifecycle conclusion
- **AND THEN** the shared tracker may remain in `unknown` posture until stronger evidence appears

### Requirement: Codex TUI success is a stable ready return after prior turn authority
The `codex_tui` profile SHALL treat successful completion as a stable return to ready posture after prior armed turn authority.

That prior armed turn authority MAY come from either an explicit input event or prior stronger active-turn evidence that armed the shared tracker through surface inference.

A visible `Worked for ...` separator MAY contribute supporting evidence, but it SHALL NOT be required for successful completion.

Current overlays, exact interruption surfaces, current prompt-adjacent terminal failure surfaces, or live-edge retry or reconnect status SHALL block success settlement for the current turn.

#### Scenario: Stable ready return settles success without a Worked-for marker
- **WHEN** the current Codex TUI surface returns to a ready composer posture after prior turn authority
- **AND WHEN** that ready posture remains stable for the configured settle window without current blockers
- **THEN** the shared tracker may settle the turn as `success`
- **AND THEN** the `codex_tui` capability does not require a visible `Worked for ...` separator to do so

#### Scenario: Exact interruption overrides ready-return success
- **WHEN** the current Codex TUI surface matches the exact interruption pattern and shows the ready composer again
- **THEN** the shared tracker records `interrupted` for the completed turn
- **AND THEN** the same ready-return surface is not settled as `success`

#### Scenario: Initial idle ready posture does not settle success
- **WHEN** the Codex TUI shows a ready composer posture without prior armed turn authority for the current turn
- **THEN** the shared tracker does not settle that posture as `success`
- **AND THEN** the tracker waits for explicit input or stronger active-turn evidence before treating a later ready return as a completion signal

### Requirement: Codex degraded diagnostics use Codex-scoped error types
When the `codex_tui` profile recognizes a bounded prompt-adjacent compact/server degraded failure surface, it SHALL expose structured degraded-context diagnostic metadata in addition to `chat_context=degraded`.

That diagnostic metadata SHALL identify Codex as the owning CLI tool and SHALL use Codex-scoped degraded error type labels for Codex-specific classifications.

Codex degraded error type labels SHALL NOT be treated as a shared cross-tool enum. Other CLI tool profiles SHALL NOT reuse Codex labels unless they are explicitly reporting a Codex TUI surface.

The only degraded error type value that MAY be shared across CLI tool profiles is `unknown`.

The `codex_tui` profile SHALL keep deriving these diagnostics only from bounded prompt-adjacent current-turn compact/server error surfaces, not from arbitrary historical scrollback.

#### Scenario: Codex stream-disconnect compact error gets Codex label
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface reports a remote compact stream-disconnect style failure
- **THEN** the `codex_tui` profile exposes `chat_context=degraded`
- **AND THEN** the degraded diagnostic identifies the owning CLI tool as Codex
- **AND THEN** the degraded error type uses a Codex-scoped label such as `codex_remote_compact_stream_disconnected`

#### Scenario: Codex context-length compact error gets Codex label
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface reports that compact input exceeds the model context window
- **THEN** the `codex_tui` profile exposes a Codex-owned degraded diagnostic
- **AND THEN** the degraded error type uses a Codex-scoped label such as `codex_remote_compact_context_length_exceeded`

#### Scenario: Codex unsupported parameter compact error gets Codex label
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface reports an unsupported compact request parameter
- **THEN** the `codex_tui` profile exposes a Codex-owned degraded diagnostic
- **AND THEN** the degraded error type uses a Codex-scoped label such as `codex_remote_compact_unknown_parameter`

#### Scenario: Unclassified Codex compact error uses unknown
- **WHEN** the current Codex TUI prompt-adjacent terminal failure surface matches compact/server degraded semantics but no Codex-specific error type classification applies
- **THEN** the `codex_tui` profile exposes recoverable degraded chat-context evidence
- **AND THEN** the degraded error type is `unknown`

#### Scenario: Historical Codex compact error has no current diagnostic
- **WHEN** a Codex TUI snapshot contains a historical compact/server error above the current prompt-adjacent region
- **AND WHEN** the bounded current prompt-adjacent region has no compact/server degraded failure surface
- **THEN** the `codex_tui` profile does not expose a current Codex degraded diagnostic from the historical text
- **AND THEN** gateway automation cannot select context recovery from that historical text alone

### Requirement: Codex delegated work remains active until the parent turn settles
For a maintained Codex 0.144.x TUI profile, visible GPT-5.6 multi-agent or collaboration activity SHALL count as current-turn active evidence. A parent turn SHALL remain active while delegated agents are running, waiting on current collaboration work, or reporting current progress, even if the editor frame remains visible.

The tracker SHALL report ready only after delegation activity has settled and the current surface satisfies the normal stable ready-return contract. Missed short-lived delegation frames at lower capture rates SHALL not create an impossible state sequence or a false successful completion before later active evidence.

#### Scenario: Running delegated agents keep the turn active
- **WHEN** the current Codex surface reports one or more delegated agents still running
- **THEN** tracked state remains active
- **AND THEN** the visible editor does not alone make the surface prompt-ready

#### Scenario: Sparse replay remains semantically valid
- **WHEN** a lower-rate replay skips one intermediate delegation transition
- **THEN** the resulting tracked sequence remains consistent with the observed later activity and stable ready return
- **AND THEN** the tracker does not emit an irreversible false terminal result between those observations

### Requirement: Codex current pending-input panes are active-turn evidence
The Codex 0.144 tracked-TUI profile SHALL recognize current pending-steer, rejected-steer, and queued-follow-up sections rendered by the upstream pending-input preview.

The section headers `Messages to be submitted after next tool call`, `Messages to be submitted at end of turn`, and `Queued follow-up inputs` SHALL be treated as non-response current-turn cells. A current section SHALL contribute active evidence and SHALL prevent `surface.ready_posture=yes` even when the ordinary status row is hidden.

Historical pending-input text followed by a later completed assistant response SHALL NOT by itself keep a settled prompt active.

#### Scenario: Pending steer does not hide the working row
- **WHEN** a current Codex surface shows a working row followed by `Messages to be submitted after next tool call`
- **THEN** the pending-input header does not terminate the working-row scan as if it were an assistant response
- **AND THEN** the profile reports the turn as active and non-ready

#### Scenario: Pending steer remains busy while status row is hidden
- **WHEN** a current Codex surface shows a pending-input section while streamed assistant output is growing and the working row is temporarily hidden
- **THEN** the pending-input section independently keeps the current turn active

#### Scenario: Settled historical pending input does not remain active
- **WHEN** a later completed assistant response and clean current prompt supersede historical pending-input text
- **THEN** the historical section alone does not block current ready posture

### Requirement: Codex retry and list-selector activity is bounded to current source-backed surfaces
The Codex tracked-TUI profile SHALL recognize current reconnect activity from the maintained source-backed reconnect status family and SHALL NOT classify arbitrary prose or command descriptions containing `retry` as stream activity.

The profile SHALL treat a current model or list selector with a selection title or rows and the current `Press enter to confirm or esc to go back` footer as a blocking overlay. Historical selector titles or footers outside the current bounded interactive region SHALL NOT block a later prompt.

#### Scenario: Reconnect status is active
- **WHEN** the current Codex status surface displays `Reconnecting... 2/5` or the maintained equivalent reconnect status
- **THEN** the profile reports stream-retry active evidence and blocks ready-return success

#### Scenario: Retry prose is not activity
- **WHEN** current visible prose or a slash-command description contains the word `retry`
- **AND WHEN** no current reconnect status surface exists
- **THEN** the profile does not report stream-retry active evidence from that prose

#### Scenario: Model selector blocks prompt readiness
- **WHEN** the current Codex surface shows `Select Model and Effort` and the list-selection confirmation footer
- **THEN** the profile reports a blocking interactive surface
- **AND THEN** it does not classify the selected `› 1.` row as a submit-ready prompt draft
