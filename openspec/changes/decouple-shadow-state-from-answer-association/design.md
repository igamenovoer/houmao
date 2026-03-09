## Context

The current CAO `shadow_only` path asks the shadow parser stack to do three jobs at once:

1. detect live TUI state from `mode=full`,
2. decide when a submitted turn is complete, and
3. extract the authoritative final answer for the just-submitted prompt.

That coupling is workable only if prompt-to-answer association can be derived reliably from raw tmux scrollback. Our recent Claude baseline-reset investigation showed that this is not a stable contract: the parser can still see valid old answer markers and boundaries in a mutated transcript without being able to prove they were caused by the current submit.

The deeper issue is not Claude concurrency. Claude Code is usually single-threaded from an execution standpoint. The issue is that CAO/tmux gives the runtime a lossy, cumulative, snapshot-based observation surface rather than structured turn events. That makes provider-owned state parsing tractable, but generic prompt-to-answer association inherently heuristic.

At the same time, the current runtime/result surface expects one `output_text` value for a completed `shadow_only` turn, and the current runtime already contains `_ShadowLifecycleTracker` for unknown→stalled handling. That means this change must do two things explicitly instead of hand-waving them: remove the misleading `output_text` expectation from shadow-mode results, and define how a real `TurnMonitor` evolves the existing lifecycle tracker instead of creating a second overlapping mechanism.

## Goals / Non-Goals

**Goals:**
- Separate provider-owned TUI state/projection from caller-owned answer association.
- Make the core shadow parser contract stable and versionable around supported output families, state assessment, and dialog projection.
- Freeze concrete value-object shapes for `SurfaceAssessment` and `DialogProjection` so provider implementations do not drift.
- Move turn completion logic into a runtime layer that reasons over parser state transitions rather than parser-owned answer extraction.
- Provide callers with projected dialog content and transcript slices they can use for their own answer association logic.
- Clarify how runtime `TurnMonitor` behavior relates to the existing `_ShadowLifecycleTracker` lifecycle logic.
- Keep `cao_only` behavior unchanged.

**Non-Goals:**
- Guarantee a generic, parser-owned "final answer for the current prompt" for CAO TUI sessions.
- Solve all caller-specific answer extraction heuristics in this change.
- Remove CAO/tmux support or replace it with a structured provider protocol.
- Make headless backends follow the same output contract as TUI shadow mode.

## Contract Documents

This design is paired with three contract notes:

- `contracts/claude-state-contracts.md`
- `contracts/codex-state-contracts.md`
- `contracts/turn-monitor-contracts.md`

Those documents define provider-specific state detection and the runtime lifecycle contract in more detail than the capability deltas.

## Decisions

### 1. Split the shadow parser contract into frozen surface-assessment and dialog-projection models

The shared shadow parser interface will stop centering `extract_last_answer()` as the core success path. Instead, the parser contract will produce two stable artifacts from a snapshot:

- `SurfaceAssessment`: provider-owned state detection
- `DialogProjection`: normalized dialog-oriented text with TUI chrome removed

Both artifacts will be `@dataclass(frozen=True)` value objects, following the same style as `ShadowParserMetadata`.

The shared base shape for `SurfaceAssessment` is:

```python
CommonUiContext = Literal["normal_prompt", "selection_menu", "unknown"]

@dataclass(frozen=True)
class SurfaceAssessment:
    availability: Availability
    activity: Activity
    accepts_input: bool
    ui_context: CommonUiContext
    parser_metadata: ShadowParserMetadata
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
```

Provider-specific subclasses refine the context vocabulary and add evidence fields:

```python
ClaudeUiContext = Literal[
    "normal_prompt",
    "selection_menu",
    "slash_command",
    "trust_prompt",
    "error_banner",
    "unknown",
]

CodexUiContext = Literal[
    "normal_prompt",
    "selection_menu",
    "approval_prompt",
    "error_banner",
    "unknown",
]

@dataclass(frozen=True)
class ClaudeSurfaceAssessment(SurfaceAssessment):
    ui_context: ClaudeUiContext
    evidence: tuple[str, ...] = ()

@dataclass(frozen=True)
class CodexSurfaceAssessment(SurfaceAssessment):
    ui_context: CodexUiContext
    evidence: tuple[str, ...] = ()
```

The shared base shape for `DialogProjection` is:

```python
@dataclass(frozen=True)
class DialogProjection:
    raw_text: str
    normalized_text: str
    dialog_text: str
    head: str
    tail: str
    projection_metadata: ProjectionMetadata
    anomalies: tuple[ShadowParserAnomaly, ...] = ()
```

Provider-specific subclasses refine projection metadata and evidence:

```python
@dataclass(frozen=True)
class ClaudeDialogProjection(DialogProjection):
    evidence: tuple[str, ...] = ()

@dataclass(frozen=True)
class CodexDialogProjection(DialogProjection):
    evidence: tuple[str, ...] = ()
```

`SurfaceAssessment` captures state facets rather than a single answer-centric status. The shared design target is:

- `availability`: whether the surface is usable/supported
- `activity`: whether the tool is ready, working, blocked, or unknown
- `ui_context`: a small common base vocabulary plus provider-specific subtype extensions
- `accepts_input`: whether the terminal currently looks safe for prompt submission

`DialogProjection` should preserve essential dialog ordering while removing provider-specific chrome such as ANSI sequences, prompt glyph-only lines, spinners, footer noise, and other non-dialog scaffolding.

Alternative considered:
- Keep the current API and simply weaken answer extraction to "best effort."
Why not:
- It leaves the impossible guarantee in the core parser contract.
- Callers still treat the returned answer as authoritative even when it is only heuristic.

### 2. Move turn completion into a runtime `TurnMonitor` that evolves `_ShadowLifecycleTracker`

Turn completion for `shadow_only` will no longer mean "parser extracted a prompt-associated final answer." Instead, runtime will own a `TurnMonitor`-style state machine that combines:

- pre-submit readiness from `SurfaceAssessment`,
- post-submit surface transitions,
- transcript/projection change observation, and
- blocking/error states such as waiting-user-answer or unsupported output.

This keeps the parser focused on "what does this snapshot look like?" while runtime answers "has the submitted turn reached a terminal lifecycle point?"

`TurnMonitor` is not intended to sit beside `_ShadowLifecycleTracker` as a second lifecycle implementation. It is the runtime-owned evolution of that logic:

- `_ShadowLifecycleTracker`'s current unknown→stalled timeout semantics remain part of the runtime contract.
- The new `TurnMonitor` adds submit-aware lifecycle semantics on top of that foundation.
- Implementation may absorb `_ShadowLifecycleTracker` directly into `TurnMonitor` or keep it as an internal helper, but the architectural contract is a single runtime lifecycle mechanism.

The default terminality rule is:

- after submit, a turn becomes success-terminal only when the surface returns to `ready_for_input` and runtime has observed either:
  - `evt_projection_changed` after submit, or
  - any post-submit `working` state.

This protects the fast-return edge case where the surface may look idle again before a poll captures `working`, while still avoiding stale terminal projections.

Alternative considered:
- Keep `completed` as a parser state that implies answer association.
Why not:
- `completed` in the current design smuggles causality guarantees into snapshot parsing.
- Once transcript anchors are lost, the parser cannot justify that implication generically.

### 3. Introduce a caller-facing projected-dialog API for `shadow_only`

For `shadow_only` results, runtime will expose projected dialog content and transcript slices instead of treating parser-owned answer text as authoritative. The design target is that callers can access at least:

- full projected dialog text,
- head slice,
- tail slice,
- raw/normalized snapshot diagnostics, and
- parser/runtime provenance metadata.

This can appear in event payloads and/or result models, but the core runtime contract will expose `dialog_projection` and `surface_assessment` as first-class fields. `output_text` will be removed from the `shadow_only` result surface rather than preserved as a compatibility alias, because keeping it would continue to imply answer authority that the new contract explicitly rejects.

Head and tail slices are defined over normalized projected dialog, not over raw CAO `mode=full` text.

Alternative considered:
- Preserve `output_text` as a compatibility alias to projected dialog text.
Why not:
- It keeps the old ambiguity alive under a new name and invites callers to keep treating projected dialog as the prompt answer.

### 4. Make answer association an explicit optional layer

Prompt-to-answer association becomes a separate layer above the core shadow parser/runtime lifecycle. This layer may use:

- prompt-specific expected output formats,
- structured sentinels or tags,
- diff/suffix heuristics over projected dialog,
- task-specific regexes, or
- application-specific semantic validation.

The runtime will not represent this layer as the core shadow parser contract, but this change will ship one small concrete helper so the boundary is real rather than theoretical:

- `TailRegexExtractAssociator(n, pattern)` accepts projected dialog text,
- limits the search window to the last `n` characters, and
- returns the regex match (or `None`) from that tail window.

Alternative considered:
- Omit any explicit associator boundary and let callers improvise.
Why not:
- The same heuristic problem would be repeated ad hoc without a named extension point.

### 5. Keep provider versioning and unsupported-format rules in the core parser

This change narrows the parser contract, but it does not weaken it. Provider-owned logic will still own:

- versioned preset selection,
- supported output-family detection,
- explicit unsupported-format failures,
- state detection,
- dialog projection boundaries, and
- projection metadata/anomalies.

This preserves the strongest part of the current design: version-aware understanding of provider TUI surfaces.

Alternative considered:
- Push almost everything to callers.
Why not:
- State detection and TUI normalization are exactly the parts that benefit from centralized provider knowledge.

## Risks / Trade-offs

- [Breaking callers that read `output_text`] → Mitigation: make the break explicit in the runtime contract, surface first-class `dialog_projection` / `surface_assessment`, and ship `TailRegexExtractAssociator` as the named extraction escape hatch.
- [Turn completion logic becomes more complex in runtime] → Mitigation: keep the turn-monitor layer explicit and diagnostics-rich rather than hiding completion heuristics inside parser methods.
- [Callers may implement weak answer associators] → Mitigation: document association as heuristic/caller-owned and provide examples/patterns rather than overstating guarantees.
- [Provider-specific surface-state vocabularies may drift] → Mitigation: keep state facets version-bound and allow provider-specific `ui_context` values with explicit unknown/unsupported handling.
- [Codex scope may feel broader than Claude's immediate pain point] → Mitigation: align the shared shadow-parser API now so Claude and Codex do not diverge further, while allowing provider-specific rollout details.

## Migration Plan

1. Add delta specs for the shared shadow-parser stack, provider parser contracts, runtime result contract, and the new dialog-projection capability.
2. Introduce frozen shared/base models for `SurfaceAssessment` and `DialogProjection`, plus provider-specific subclasses and caller-visible projection slices.
3. Refactor shadow parser implementations so provider logic returns state/projection artifacts instead of authoritative answer extraction.
4. Refactor `shadow_only` CAO runtime flow to use a runtime `TurnMonitor`, absorb/evolve `_ShadowLifecycleTracker`, and surface `dialog_projection` / `surface_assessment` payloads on completion.
5. Remove shadow-mode `output_text` from the runtime result surface and document the break.
6. Add the optional associator protocol plus `TailRegexExtractAssociator`.
7. Update docs and tests so they validate projected dialog/state semantics rather than final-answer extraction semantics.

Rollback strategy:
- Because this is a breaking contract change, rollback would mean restoring the current `shadow_only` answer-extraction API surface, `output_text` behavior, and associated parser methods. The migration should therefore keep parser/state/projection changes isolated enough to revert together if adoption stalls.

## Open Questions

- Should CAO `tail` mode be surfaced directly as part of the projection API, or should runtime derive tail/head slices only from normalized projected dialog?
