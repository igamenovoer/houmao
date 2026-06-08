## Context

TUI tracking is fragile when it starts from code guesses. Kimi Code uses a pi-tui surface with styled editor borders, footer metadata, spinner components, approval panels, and transcript regions. Exact text can drift across Kimi versions and themes, while structural anchors, ANSI styling, timing, and bounded region semantics are more stable.

The current terminal recorder already preserves replay-grade tmux pane snapshots with ANSI escape data through `tmux capture-pane -p -e`. It also has labels and replay output, but its command surfaces are still Claude/Codex-shaped and the current workflow does not require high-rate capture, low-rate derivation, or manual timeline labeling before adding a new detector.

This change makes Kimi TUI state tracking evidence-first. It captures live Kimi sessions, labels state ranges manually, writes Kimi signal design artifacts under the change's context/design/contracts area, then implements and verifies the Kimi shared TUI tracking profile from that evidence.

## Goals / Non-Goals

**Goals:**

- Capture live, logged-in Kimi Code TUI sessions into repo-local `tmp/kimi-tui-tracking/` run roots.
- Preserve ANSI/style data and timing metadata in the replay-grade snapshot stream.
- Capture at about 10 fps and derive about 2 fps streams from the high-rate stream.
- Capture and label at least 5 development sessions and at least 3 held-out test sessions.
- Ensure each captured session spans multiple TUI state changes.
- Investigate Kimi TUI source code before finalizing signal contracts.
- Label Kimi TUI states over sample ranges before detector implementation starts.
- Define Kimi signal contracts in change-local context, design, and contract artifacts.
- Implement the Kimi shared TUI signal profile from minimal stable signals.
- Verify parser/tracker output against labeled 10 fps and 2 fps timelines, including held-out test sessions not used during detector development.
- Update recorder and replay tooling where Kimi support or decimation is missing.

**Non-Goals:**

- Do not implement full Kimi local interactive launch/relaunch support in this change.
- Do not make exact full-sentence matching the primary Kimi detector strategy.
- Do not use `session.cast` as the machine replay source of truth.
- Do not add pi-tui as a Houmao runtime dependency.
- Do not require live Kimi credentials for deterministic unit tests after the corpus is captured.

## Decisions

### Capture first, implement second

The Kimi detector implementation SHALL wait until a labeled capture corpus exists. This corpus is the oracle for the detector and parser work.

The corpus SHALL be split into:

- a development set with at least 5 live Kimi sessions used for signal discovery, detector design, and implementation tuning
- a held-out test set with at least 3 separate live Kimi sessions not used for detector design or implementation tuning

Each session SHALL span multiple state changes. Single-surface snapshots are useful as fixtures, but they are not sufficient evidence for a turn tracker because the hard part is transitions.

The minimum scenario set is:

- idle welcome/editor
- draft editing
- prompt submit, active response, completed response, ready return
- shell/tool approval prompt
- approval rejection
- interrupt during active turn
- footer metadata containing `thinking` while the prompt is otherwise ready

Alternative considered: implement a detector from source-code reading and live-memory notes. That is too likely to encode false assumptions, especially around footer metadata and approval UI.

### Pair live evidence with source-code investigation

The Kimi signal design SHALL inspect the Kimi TUI source before finalizing detector rules. Source investigation should identify which visible anchors come from stable component boundaries, such as editor rendering, footer rendering, spinner components, approval panels, and modal coordinators, and which anchors are accidental wording or theme-dependent presentation.

Live captures answer what actually appears in the terminal. Source code answers why it appears and whether a signal is likely to survive version drift. Neither source is sufficient alone.

Alternative considered: rely only on live captures. That can overfit to incidental text, timing, model output, or the local theme. Source inspection gives the detector a better sense of which signals are structural.

### Use 10 fps as source, derive 2 fps from it

The recorder SHALL capture the authoritative stream at about 10 fps (`0.1` seconds). The low-rate stream SHALL be derived from that stream by selecting frames nearest each `0.5` second boundary. This keeps 10 fps and 2 fps evidence aligned by sample identity and prevents two independent live runs from disagreeing because the model responded differently.

Alternative considered: capture separate 10 fps and 2 fps live runs. That gives realistic cadence but makes manual labels harder to compare because TUI timing and model output differ between runs.

### Keep raw ANSI/style as first-class evidence

The replay-grade stream SHALL preserve ANSI styling. Kimi detector design SHALL prefer structural and style signals over exact strings:

1. explicit input events
2. structural anchors such as editor box, prompt row, activity row, approval panel, and current-turn region
3. style evidence such as focused borders, selected choices, muted footer text, warning/error colors, and plain versus dim prompt payloads
4. temporal evidence such as spinner frame changes, transcript growth, and stable return to ready
5. bounded semantic tokens inside known regions
6. exact strings only as debug notes or final fallback checks

This mirrors the existing Codex and Claude patterns: Codex scopes activity to latest-turn/live-edge regions, and Claude uses raw ANSI styling to distinguish prompt content from suggestions.

### Store signal design artifacts next to the change

The implementation SHALL create change-local artifacts under:

```text
openspec/changes/capture-kimi-tui-signals/context/
openspec/changes/capture-kimi-tui-signals/design/
openspec/changes/capture-kimi-tui-signals/contracts/
```

Those artifacts SHALL summarize captured scenarios, manual state labels, Kimi-specific stable signal choices, and the replay-validation oracle. They are not substitutes for spec requirements; they are the working evidence and design notes used to implement the detector safely.

### Validate public tracked state, not internal detector trivia

Replay validation SHALL compare labels against public tracked-state fields:

- `diagnostics_availability`
- `surface_accepting_input`
- `surface_editing_input`
- `surface_ready_posture`
- `turn_phase`
- `last_turn_result`
- `last_turn_source`

Parser fields such as `business_state`, `input_mode`, and `ui_context` may also be labeled for Kimi approval and modal surfaces, but internal notes and exact matched fragments SHALL remain diagnostic.

Development-set validation SHALL guide implementation. Held-out test-set validation SHALL be the acceptance gate for maintained Kimi tracking behavior.

### Treat Kimi launch support as downstream

This change may launch manual Kimi sessions for capture, but it SHALL not complete the full managed Kimi TUI support story. The active `add-kimi-tui-support` change remains the place for local interactive launch, relaunch, parser integration into public APIs, and docs. After this change lands, that broader change should consume the signal design and labeled corpus instead of inventing Kimi TUI tracking from scratch.

## Risks / Trade-offs

- Kimi may auto-update during capture -> record Kimi CLI version in every run manifest and keep profile decisions version-scoped.
- High-rate sampling may create large artifacts -> store live capture roots under `tmp/` and promote only curated fixtures or reduced samples when needed for committed tests.
- Manual labels can be inconsistent -> use range labels, reviewer notes, and replay comparison reports to catch mismatches before implementation claims success.
- Detector rules can overfit the development corpus -> keep at least 3 labeled sessions held out until acceptance validation.
- Source-code conclusions can drift after Kimi updates -> record source version or commit context and tie each signal contract to observed Kimi CLI versions.
- ANSI styling may vary by theme -> capture enough theme and terminal metadata, then prefer style roles such as dim/plain/selected/focused over specific color numbers where possible.
- Approval rejection can look like a failure but produce a normal assistant response -> label the approval-blocked range separately from the post-rejection outcome.
- Recorder `asciinema` observation may exit early -> make pane snapshots independent enough that recorder sampling can continue or fall back without losing replay-grade evidence.

## Migration Plan

No stored runtime migration is required. Existing terminal recorder runs remain readable. New Kimi runs add Kimi tool identity, high-rate source stream metadata, derived low-rate stream metadata, and richer label expectations.

The broad `add-kimi-tui-support` change should be revised after this change so its Kimi parser/profile tasks depend on the captured signal corpus and contracts.

## Open Questions

- Should curated Kimi fixtures be committed immediately, or should only compact derived fixtures be committed while full high-rate runs stay under `tmp/`?
- Which Kimi themes should be captured for initial style robustness?
- Should the replay validator allow a small transition-boundary tolerance for all fields or only for `turn_phase` changes around submit/complete moments?
