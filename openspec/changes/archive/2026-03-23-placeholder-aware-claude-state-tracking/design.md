## Context

The shared tracked-TUI stack currently derives Claude prompt editing state from ANSI-stripped prompt payload text alone. That works for true draft content but fails on newer Claude startup and idle surfaces that render suggestion text inline on the visible `❯` prompt line using styling rather than structural separation. Once ANSI is stripped, the placeholder suggestion looks identical to user-authored draft text, so the official/runtime tracker and live-watch dashboard incorrectly emit `surface.editing_input=yes` until the operator changes the prompt surface.

The shared reducer and public tracked-state vocabulary are already in the right layer. The bug lives inside the Claude detector/profile path. Codex already solved a similar problem by classifying prompt payload rendering from raw SGR state before mapping that result to normalized tracker signals. Claude needs the same class of solution, but its prompt glyphs, styling, and version drift are different enough that it should not reuse Codex behavior wholesale.

## Goals / Non-Goals

**Goals:**
- Make Claude placeholder and suggestion text on the visible prompt line classify as non-editing prompt posture.
- Preserve the public tracked-state vocabulary and reducer contract.
- Keep style-sensitive interpretation profile-owned and version-selectable so future Claude rendering drift can be isolated to Claude detector code.
- Add tests that cover raw ANSI startup-placeholder surfaces and normal draft-entry surfaces.

**Non-Goals:**
- Redesign the shared reducer, turn model, or public tracked-state schema.
- Introduce a cross-app prompt-behavior registry shared between Claude and Codex in this change.
- Depend on host-provided parsed-surface metadata or tmux-specific side channels to detect placeholder state.

## Decisions

### Add Claude prompt-behavior classification on raw prompt rendering
The Claude detector will stop using stripped prompt payload text as the sole source of `editing_input`. Instead, it will derive a Claude prompt-area snapshot from the raw ANSI line and classify the prompt as one of: placeholder, draft, empty, or unknown.

Why:
- The raw ANSI line preserves the only reliable distinction currently visible between startup placeholder text and real draft text.
- The tracker already ingests raw snapshot text, so the detector has the data it needs without widening the public tracker contract.

Alternative considered:
- Keep using stripped prompt text plus phrase matching for known suggestions. Rejected because placeholder phrases can drift across versions and locales, while style is the real differentiator on the observed surface.

### Keep Claude prompt behavior profile-private and version-selectable
Claude prompt classification will live under the Claude tracked-TUI profile implementation and be selected by Claude version family, following the same architectural pattern already used by Codex prompt behavior.

Why:
- Placeholder rendering is drift-prone UI behavior, not shared engine logic.
- Version-selectable prompt variants let maintainers handle future Claude changes by updating one version family or adding a new Claude-specific variant without touching the shared reducer or Codex logic.

Alternative considered:
- Generalize immediately to one shared cross-app prompt-classification subsystem. Rejected for now because the apps use different prompt glyphs, rendering conventions, and fallback semantics, and the immediate bug is scoped to Claude.

### Keep `SurfaceView` generic and add only the raw helpers Claude needs
The implementation may add small raw-line or prompt-area helper methods to `SurfaceView`, but it will not move app-specific placeholder logic into shared surface utilities.

Why:
- Shared helpers should expose raw facts, not encode Claude-specific style rules.
- This keeps the detector testable while avoiding cross-app coupling in low-level utilities.

Alternative considered:
- Teach `SurfaceView.prompt_text()` to suppress styled placeholders generically. Rejected because placeholder semantics are app- and version-specific, and a generic helper cannot safely decide which styled content is a placeholder versus a legitimate draft.

### Prefer conservative fallback behavior on unrecognized prompt rendering
When Claude prompt rendering cannot be classified confidently, the detector should prefer conservative results such as `editing_input=unknown` or `no` rather than asserting `yes` from stripped text alone.

Why:
- The current false positive is more damaging than temporary uncertainty because it distorts idle-ready startup state and pollutes downstream live-watch interpretation.
- Conservative fallback matches the tracker’s broader posture of degrading ambiguous surfaces instead of inventing stronger state than the evidence supports.

Alternative considered:
- Preserve the current `prompt_text => editing=yes` fallback. Rejected because it reintroduces the exact placeholder bug on the next styling drift.

## Risks / Trade-offs

- [Claude styling drifts again in a future version] → Mitigation: keep prompt behavior version-selectable and add a Claude fallback variant that degrades conservatively when rendering is unrecognized.
- [ANSI/style parsing differs between tmux capture shapes] → Mitigation: cover the classifier with raw ANSI unit fixtures taken from current live captures and assert behavior on both placeholder and real-draft examples.
- [Too-conservative fallback hides legitimate draft text in rare render states] → Mitigation: keep the variant logic explicit, test normal typed drafts, and preserve version-specific notes to make misclassification diagnosable.

## Migration Plan

No external migration is required. Implement the detector/profile changes, add regression coverage, and update the relevant tracker specs. If a regression appears after rollout, revert the Claude prompt-behavior selection to the previous detector path while keeping the shared reducer and public schema unchanged.

## Open Questions

- None for the proposal stage. The main architectural choice is to keep placeholder interpretation in Claude profile-owned, version-specific behavior logic, and that is sufficient to begin implementation.
