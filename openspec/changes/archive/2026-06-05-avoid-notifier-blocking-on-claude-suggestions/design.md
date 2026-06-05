## Context

Gateway mail notification for TUI-backed sessions is gated by tracked prompt readiness. For Claude Code, the readiness chain depends on the shared tracker detecting whether the visible prompt payload is a real editable draft or non-editable placeholder content.

The current Claude prompt behavior variant already inspects raw ANSI/SGR styling in the prompt line, but it treats foreground and background color families as neutral. Claude Code can render an auto-suggestion on the prompt line in a darker style than ordinary typed prompt text. When the tracker sees only stripped text, or ignores the distinguishing color style, it can mark that suggestion as `editing_input=yes`. The gateway notifier then defers because `_tui_prompt_not_ready_reasons_locked()` rejects any state with `surface.editing_input != "no"`.

## Goals / Non-Goals

**Goals:**

- Classify Claude Code prompt-line ghost suggestions from raw rendering/style evidence rather than exact suggestion text.
- Preserve safety for real operator drafts: any ordinary typed payload, or a mixed ordinary typed prefix plus styled suggestion suffix, remains editing input.
- Keep the gateway mail notifier free of provider-specific prompt-text heuristics by fixing the tracked readiness signal at the Claude profile boundary.
- Cover the behavior with prompt-behavior, shared tracker, and notifier-readiness tests.

**Non-Goals:**

- Do not change gateway notifier queue, mailbox, interval, or audit semantics.
- Do not add a public API field for suggestion text or expose raw ANSI style data through tracked-state routes.
- Do not make the fallback Claude profile optimistic for unrecognized prompt styling.
- Do not rely on literal suggestion text such as `check mail`.

## Decisions

### Decision: Classify ghost suggestions inside the Claude prompt behavior variant

The implementation should update `src/houmao/shared_tui_tracking/apps/claude_code/signals/prompt_behavior.py` so the Claude `2.1.x` prompt behavior variant can detect a payload rendered wholly in Claude's ghost-suggestion style. That keeps provider-specific rendering rules inside the selected versioned profile, where the existing prompt-behavior contract already places drift-prone prompt interpretation.

Alternative considered: add a gateway notifier exception for prompt text like `check mail`. That would be brittle, provider-specific in the wrong layer, and unsafe when the suggestion wording changes.

### Decision: Treat color evidence as meaningful only for the suggestion classification path

The existing classifier treats foreground/background color SGR as neutral rendering noise. This change should add style facts that can recognize a profile-defined low-contrast or darker foreground payload as ghost-suggestion content when every non-space payload character uses that suggestion style. Ordinary color-only styling for real typed text should continue to be accepted as draft input.

Alternative considered: treat all color-only payloads as placeholders. That would incorrectly allow notifier injection over real drafts when a terminal theme renders typed input with explicit color.

### Decision: Mixed prompt payloads are drafts

If the prompt line contains any ordinary typed payload style, the classifier should report `draft`, even if a suggestion suffix is visible in a darker style. This protects partially typed prompts where Claude displays a completion hint after the operator's typed prefix.

Alternative considered: split typed and suggested spans and expose a new public field. That is more surface area than the notifier needs and would widen the tracked-state API for an internal classification problem.

### Decision: Let notifier readiness consume corrected tracked state

The gateway notifier should keep using the existing prompt-readiness gate. With corrected Claude tracked state, a pure ghost suggestion yields `surface.editing_input=no`, `surface.ready_posture=yes`, and `turn.phase=ready`; notifier enqueueing can proceed when all other gates pass. Real drafts still yield `surface.editing_input=yes`, so notifier polls defer as before.

Alternative considered: bypass readiness for notifier prompts. That would risk overwriting operator input and weaken the safety property that prompt injection only happens when the TUI is submit-ready.

## Risks / Trade-offs

- Misclassifying a real draft as a suggestion could overwrite operator text. Mitigation: require all non-space payload characters to be in the recognized ghost-suggestion style, treat mixed styles as draft, and keep unrecognized styling conservative.
- Claude may change suggestion styling in a future version. Mitigation: keep the behavior variant version-family scoped and add fixtures that make style assumptions explicit.
- Terminal themes may alter color codes. Mitigation: define the style predicate around profile-owned low-contrast/darker suggestion rendering relative to ordinary prompt text fixtures, not literal suggestion words.
- The notifier may still defer while Claude is active or unstable. Mitigation: this change only fixes prompt-suggestion readiness; active-turn and stability gates remain intentionally conservative.

## Migration Plan

No data migration is required. Deploying the tracker change affects newly observed TUI snapshots immediately. Rollback is the previous classifier behavior, which may again defer notifier prompts while styled suggestions are visible.

## Open Questions

None for the first implementation. If Claude introduces several visually distinct suggestion styles, a follow-up can add a new version-family prompt behavior variant with additional fixtures.
