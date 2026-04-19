## Context

The current Codex tracker gets one important thing right already: prompt readiness is a property of the visible composer, not a synonym for success. A prompt-adjacent error can leave the Codex surface genuinely ready for the next input.

The weakness is narrower and more dangerous. The detector still relies on overly narrow terminal-signal matching, especially around red error cells, while newer upstream Codex builds surface failed and retrying turns through multiple visual forms:

- prompt-adjacent red `■ ...` failure blocks,
- prompt-adjacent warning-style `⚠ ...` failed-turn rows, and
- live status-only retry or reconnect surfaces that do not render as terminal history cells.

That mismatch lets some failed or retrying surfaces look like a normal ready return. The tracker can then preserve correct `surface.ready_posture=yes` but still arm the success path incorrectly.

This change is cross-cutting because it affects:

- Codex profile-owned raw-signal classification,
- shared tracker reduction and completion semantics,
- public tracked-state expectations for ready, active, `known_failure`, and degraded context, and
- the versioned-profile contract that governs how drift-prone visible strings should be matched.

## Goals / Non-Goals

**Goals:**

- Preserve truthful prompt readiness when Codex visibly returns to a ready composer after a failed turn.
- Stop warning-only failed-turn surfaces from drifting into success settlement.
- Stop retry or reconnect status surfaces from drifting into ready-return success settlement.
- Keep recoverable compact or server failures distinct from stronger terminal failures by preserving `chat_context=degraded` only for the bounded compact or server family.
- Base Codex failure and retry matching on bounded structural regions and essential semantic tokens rather than exact full-sentence literals.
- Keep ambient or historical warnings outside the bounded current-turn scope from mutating the current turn state.

**Non-Goals:**

- Re-model structured headless Codex app-server errors through the tracked-TUI surface contract.
- Guarantee that every upstream wording drift is detected without adding new fixtures.
- Introduce a new public tracked-state field beyond the existing `surface`, `turn`, `last_turn`, and `chat_context` contract.
- Treat every `⚠` warning as a terminal failure.

## Decisions

### Classify Codex surfaces by bounded visual role before semantic meaning

The detector should not try to answer "what does this sentence mean?" from whole-screen text. It should first answer "what visual role does this bounded block play?"

The design therefore splits Codex error-adjacent matching into four profile-private classes:

1. prompt-adjacent terminal failure block,
2. prompt-adjacent degraded compact or server failure block,
3. live-edge retry or reconnect status, and
4. ambient warning or historical transcript noise.

Prompt-adjacent classes are scoped to the bounded region immediately above the current prompt. Retry status is scoped to the live edge. Ambient or historical warnings remain outside the current-turn contract.

Alternative considered: apply one generic whole-screen error regex. Rejected because it repeats the existing historical-scrollback and warning-noise failure mode.

### Use essential semantic token families, not exact full-string literals

The Codex profile should match drift-prone terminal signals through bounded patterns that require the essential semantics of the surface rather than the exact full sentence.

Examples of essential semantics:

- compact or server degraded family: compact plus one of stream, disconnect, server, or remote semantics,
- terminal overload family: overload or high-load semantics in a prompt-adjacent warning or failure block,
- retry family: reconnect, retry attempt, or stream-recovery semantics in a live status surface.

This still uses concrete token patterns, but the contract is "match the essential family" rather than "match one blessed literal string".

Alternative considered: pin exact upstream snapshot strings in the detector. Rejected because the user-visible wording already drifts across upstream versions and render paths.

### Keep readiness and terminal outcome independent

Prompt readiness continues to come from prompt visibility, overlay state, draft classification, and absence of current active evidence. Terminal failure classification must not override those prompt facts by itself.

For prompt-adjacent terminal failures that leave the prompt visibly ready:

- `surface.accepting_input` stays prompt-derived,
- `surface.editing_input` stays prompt-derived,
- `surface.ready_posture` stays prompt-derived,
- success settlement is blocked, and
- the tracker may publish `known_failure` only for recognized terminal families strong enough to justify that outcome.

Recoverable compact or server failures remain separate: they block success and expose degraded context, but they do not become `known_failure`.

Alternative considered: make every prompt-adjacent failure force `ready_posture=unknown`. Rejected because it would knowingly publish false readiness for surfaces that are actually promptable.

### Retry or reconnect status is active evidence, not terminal evidence

A retry or reconnect status indicates the turn is still in flight or in recovery, even when the prompt area is visible again or partially repainted. The tracker should therefore treat recognized live-edge retry status as active evidence.

That means:

- `turn.phase=active`,
- `success_candidate=false`,
- no terminal `known_failure`, and
- no degraded compact/server context unless a separate prompt-adjacent degraded failure block is present.

Alternative considered: treat retry status as a ready-but-blocked state. Rejected because the existing public lifecycle already models in-flight work as `active`, and adding a pseudo-ready retry posture would complicate consumers without improving operator truth.

### Keep the new classifier profile-private under the versioned profile contract

The classification vocabulary for Codex failure and retry surfaces should remain a profile-private implementation detail. The shared tracker continues to consume normalized booleans and public posture fields.

This lets the Codex profile evolve its token sets and bounded matching logic without widening the shared public state model or creating a new cross-app registry concept.

Alternative considered: add a new shared normalized error-surface enum. Rejected because the current problem can be solved within the existing profile-private detector boundary.

## Risks / Trade-offs

- [Risk] Semantic token families may over-match unrelated warnings. -> Mitigation: require bounded prompt-adjacent or live-edge structural scope plus family-specific token co-occurrence, not free-form whole-screen regexes.
- [Risk] Semantic token families may under-match a new upstream wording drift. -> Mitigation: add detector fixtures from observed upstream surfaces and keep the matcher isolated in profile-private helpers.
- [Risk] Warning-only terminal failures may be misclassified as ambient warnings. -> Mitigation: only upgrade warnings to terminal failures when they are prompt-adjacent and satisfy a recognized terminal family.
- [Risk] Retry status may remain visible while the surface is actually idle. -> Mitigation: scope retry matching to the live edge and let stable ready return win once retry evidence disappears.
- [Risk] Introducing `known_failure` for stronger prompt-ready failures could change downstream expectations. -> Mitigation: restrict `known_failure` to explicitly recognized families and keep degraded compact/server failures on the existing non-success, non-known-failure path.

## Migration Plan

No persisted-data migration is required.

Implementation should proceed in this order:

1. Add profile-private Codex helpers that classify prompt-adjacent terminal failures, prompt-adjacent degraded compact/server failures, and live-edge retry statuses.
2. Update the Codex detector to derive `known_failure`, `current_error_present`, `success_candidate`, `success_blocked`, and `chat_context` from those classes while leaving readiness prompt-derived.
3. Add regression coverage for warning-only failed turns, retry-status surfaces, red terminal failures, degraded compact failures, and historical warning noise.
4. Update tracker-facing docs after the detector behavior is stable.

Rollback is direct: restore the previous narrower Codex failure matching if the new bounded semantic families prove too broad. Because the change does not alter persistence or protocol shape, rollback is code-only.

## Open Questions

None. The initial implementation should start with the observed upstream families already confirmed in the local Codex checkout and extend only when new capture evidence appears.
