## Context

`shadow_only` currently models one snapshot with `SurfaceAssessment.availability`, `SurfaceAssessment.activity`, and `SurfaceAssessment.accepts_input`. That model is too lossy for interactive CLI tools such as Claude Code and Codex because one snapshot can simultaneously tell us two different facts:

- the tool is still working, and
- the current surface still allows freeform typing.

Today the provider parsers collect overlapping evidence, but the shared state contract immediately collapses that overlap into one exclusive activity plus one boolean. In practice that means the system cannot represent `working but still typeable`, and runtime readiness/completion logic in `cao_rest.py` is forced to reason over a distorted state.

This change corrects the state contract first. It intentionally does not decide transport-quiescence policy, RxPY adoption, or broader timing refactors. Those later changes should build on a sound state vocabulary instead of trying to patch semantics on top of a lossy model.

## Goals / Non-Goals

**Goals:**

- Replace the shared one-dimensional shadow activity contract with an orthogonal business/input model.
- Preserve `availability` as a separate health/support axis.
- Let provider parsers represent `working + freeform`, `idle + modal`, `awaiting_operator + modal`, and similar combinations without inventing provider-specific hacks.
- Define runtime predicates such as submit readiness and blocked-operator handling from the corrected shared state model.
- Keep this change implementable inside the existing imperative runtime monitor so the state correction stands on its own.

**Non-Goals:**

- Introducing RxPY or any other new timing engine.
- Defining new transport-quiescence timers or revisiting the earlier quiet-window change.
- Changing dialog projection semantics or answer-association responsibilities.
- Reworking `cao_only` mode.

## Decisions

### 1. Replace `activity + accepts_input` with `business_state + input_mode`

The shared `SurfaceAssessment` contract will keep `availability` unchanged and replace the current activity/input pair with:

- `business_state`: `idle | working | awaiting_operator | unknown`
- `input_mode`: `freeform | modal | closed | unknown`

Interpretation:

- `business_state` answers: what is the tool doing with respect to the current turn?
- `input_mode` answers: what kind of operator input, if any, is safe on the active surface?

Representative combinations:

- `idle + freeform`: safe normal prompt
- `working + freeform`: interactive busy surface that is still typeable
- `idle + modal`: slash-command or constrained prompt surface
- `awaiting_operator + modal`: trust/approval/selection prompt
- `awaiting_operator + closed`: login/setup/blocking screen with no freeform prompt
- `unknown + unknown`: supported surface cannot be classified safely

This change removes the assumption that `working` implies non-inputtable.

Alternative considered: keep `activity` and add more booleans such as `prompt_visible` or `generic_input_safe`. Rejected because it preserves the existing ambiguity and creates multiple partially-overlapping flags instead of a clear shared contract.

### 2. Make prompt readiness a derived runtime predicate, not a parser primitive

Provider parsers will no longer treat `ready_for_input` as the primary shared activity value. Instead, runtime derives readiness from the corrected state:

`submit_ready := availability == supported AND business_state == idle AND input_mode == freeform`

This keeps parser ownership simple and prevents the runtime from assuming that any single parser enum is enough to decide submit safety.

Related derived predicates:

- `operator_blocked := availability == supported AND business_state == awaiting_operator`
- `interactive_busy := availability == supported AND business_state == working AND input_mode == freeform`

Alternative considered: keep `ready_for_input` as a first-class parser state and bolt on a second axis beside it. Rejected because it leaves the old one-dimensional state in place and makes the new model internally inconsistent.

### 3. Keep provider `ui_context` as the detailed surface vocabulary

The new shared axes do not replace provider-specific UI detail. Claude and Codex still need `ui_context` values such as:

- Claude: `trust_prompt`, `selection_menu`, `slash_command`, `error_banner`
- Codex: `approval_prompt`, `selection_menu`, `slash_command`, `error_banner`

`ui_context` answers "which UI shape is active," while `business_state` and `input_mode` answer "what is the tool doing" and "what sort of input is allowed."

This separation matters because different UI contexts can map to the same shared contract:

- Claude trust prompt and Codex approval prompt both map to `awaiting_operator + modal`
- Claude slash-command and Codex slash-command both map to `idle + modal`

Alternative considered: encode all readiness/blocking meaning directly in `ui_context`. Rejected because runtime would become provider-specific again and lose the benefit of a shared parser contract.

### 4. Reframe runtime lifecycle around derived predicates over the new axes

`TurnMonitor` and shadow-mode readiness/completion logic should be updated to consume the corrected state model using derived predicates instead of the old `accepts_input` boolean.

For this change:

- prompt submission is allowed only on `submit_ready`,
- completion requires post-submit progress evidence plus a return to `submit_ready`,
- explicit operator-blocked surfaces fail the active turn with a blocked-surface error,
- active modal-but-not-blocked surfaces such as slash-command remain non-ready without being treated as operator-blocked failures,
- unknown/stalled handling remains imperative and continues to key off unknown business/availability classification, while `input_mode=unknown` by itself keeps the surface non-ready without automatically forcing a stalled transition.

This lets runtime distinguish:

- `working + freeform`: busy but typeable
- `idle + modal`: not ready yet, but not a hard blocked error
- `awaiting_operator + modal|closed`: blocked and requires operator intervention

Alternative considered: change only the parser contract and leave runtime semantics expressed in terms of `accepts_input`. Rejected because the main value of the new state model is lost if runtime still collapses everything back to one boolean gate.

### 5. Roll out the contract correction before any quiescence refactor

The earlier quiescence work exposed a real problem, but the root issue is the shared state vocabulary. This change intentionally stabilizes the state model first and leaves timer/quiescence mechanics for a follow-on change.

That sequencing keeps the next quiescence design cleaner:

- timers can later target `submit_ready` or `completion_ready`,
- restart semantics can be defined over meaningful predicates,
- the repository avoids combining a contract rewrite with a programming-model rewrite in the same implementation wave.

Alternative considered: revise the quiescence change in place to include the new state model. Rejected because it would mix a shared contract rewrite, provider contract rewrite, and timing-engine choice into one larger and harder-to-review change.

## Risks / Trade-offs

- [Caller-facing payload change for `surface_assessment`] -> Mitigation: mark the change as breaking, document the new axes clearly, and add helper derivations in docs/tests so downstream code can migrate from `ready_for_input`/`accepts_input`.
- [Some provider surfaces remain ambiguous between `modal` and `closed`] -> Mitigation: keep `unknown` available on the input axis and require providers to prefer `unknown` over unsafe inference.
- [Runtime logic still needs follow-on quiescence work] -> Mitigation: define `submit_ready` and `operator_blocked` now so a later timing refactor can build on stable predicates.
- [Requirement churn across shared, provider, and runtime specs] -> Mitigation: update all affected specs in the same change so the contract stays internally consistent.

## Migration Plan

1. Update the shared shadow parser contract and documentation to introduce `business_state` and `input_mode`.
2. Update Claude and Codex parser requirements and implementations to map provider evidence onto the new shared axes.
3. Update runtime shadow readiness/completion/blocking logic to consume derived predicates over the new fields instead of `accepts_input`.
4. Refresh unit tests, parser fixtures, and runtime lifecycle tests to cover mixed-state surfaces such as `working + freeform` and `idle + modal`.
5. Land any future quiescence/timer work as a follow-on change that targets the corrected state model.

Rollback strategy: because this change is internal to shadow parsing/runtime contracts, the project can revert to the previous `activity + accepts_input` model if migration proves too disruptive.

## Open Questions

- Should the runtime payload keep a temporary derived compatibility field such as `submit_ready` for one transition period, or should callers migrate directly to `business_state` and `input_mode`?
- For provider startup/login/setup screens that are clearly non-ready but not yet pattern-complete, should the preferred fallback be `awaiting_operator + closed` or `unknown + closed` until provider evidence becomes stronger?
