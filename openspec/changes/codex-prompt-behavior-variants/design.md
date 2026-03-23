## Context

The shared tracked-TUI subsystem already has a version-aware profile registry, but Codex currently resolves through a single `builtin` detector profile while prompt editing detection lives in detector-local placeholder heuristics. The current implementation works for today's prompt rendering, but it ties Codex `editing_input` semantics to one concrete mechanism instead of a stable behavior boundary.

The prompt area is exactly the kind of surface region that drifts across Codex releases: placeholder copy can change, placeholder styling can change, and special flows can reuse the same composer with different placeholder behavior. The shared tracker engine should not need to know how any of those variants work. It should continue to consume normalized signals, while Codex-specific prompt interpretation stays inside the selected Codex profile.

Observed Codex version metadata is already available to the live-watch/demo pack, and the shared registry already supports closest-compatible profile resolution. This change uses that existing versioned-profile architecture instead of creating a parallel ad hoc selector for prompt behavior.

## Goals / Non-Goals

**Goals:**

- Introduce a Codex prompt behavior boundary that classifies prompt-area snapshots through version-selected behavior variants rather than detector-local placeholder literals.
- Keep the shared tracker engine and public tracker state contract unchanged; only normalized Codex signals should cross the profile boundary.
- Allow prompt behavior variants to use style, layout, text, or other prompt-local evidence without forcing one mechanism to become the permanent design contract.
- Make upstream prompt-render drift explicit and conservative by allowing variants to return an unrecognized/unknown classification with debugging notes.
- Establish an initial Codex version-family split that can grow over time, starting from a validated `codex-cli 0.116.x` family (`minimum_supported_version=(0, 116, 0)`) plus a fallback path.

**Non-Goals:**

- Redesigning Codex active/interrupted/success settlement rules outside prompt-area interpretation.
- Requiring rich terminal-cell parsing for the whole surface; this change is limited to the prompt-area classification boundary.
- Defining every future Codex prompt behavior family up front.
- Changing the shared tracker reducer or public state fields for this change alone.

## Decisions

- Introduce a profile-owned prompt behavior variant interface for Codex.
  - The Codex profile will first extract a prompt-area snapshot object from the raw surface by refactoring the current `build_prompt_context()` seam rather than inventing a second unrelated prompt parser. That snapshot should preserve more than one stripped prompt line when raw prompt-local evidence matters, for example raw prompt line, stripped prompt line, prompt payload text, and bounded raw/stripped prompt-region lines around the active prompt.
  - V1 should model this boundary with frozen dataclass value objects plus a narrow `Protocol`, not Pydantic models or a new ABC hierarchy:
    ```python
    PromptKind = Literal["placeholder", "draft", "empty", "unknown"]

    @dataclass(frozen=True)
    class PromptAreaSnapshot:
        prompt_visible: bool
        prompt_index: int | None
        raw_prompt_line: str | None
        stripped_prompt_line: str | None
        payload_text: str | None
        raw_prompt_region_lines: tuple[str, ...]
        stripped_prompt_region_lines: tuple[str, ...]

    @dataclass(frozen=True)
    class PromptClassification:
        kind: PromptKind
        prompt_text: str | None
        notes: tuple[str, ...] = ()

    class CodexPromptBehaviorVariant(Protocol):
        @property
        def variant_name(self) -> str: ...

        def classify(self, snapshot: PromptAreaSnapshot) -> PromptClassification: ...
    ```
  - A `CodexPromptBehaviorVariant` then classifies that prompt-area snapshot into a coarse result such as `placeholder`, `draft`, `empty`, or `unknown`, plus optional debug metadata.
  - Rationale: this isolates prompt interpretation from the rest of the Codex detector and prevents future placeholder logic changes from leaking into shared state reduction.
  - Alternative considered: keep prompt classification inside `ready.py` as a set of helper functions. Rejected because it preserves the current coupling between prompt semantics and one detector implementation.

- Use version-selected Codex detector profiles, and let each selected profile own one prompt behavior variant instance.
  - The shared registry already supports closest-compatible version resolution. Codex should stop presenting itself as one undifferentiated `builtin` profile and instead expose at least one concrete version family plus a conservative fallback.
  - V1 will register one concrete Codex family with `minimum_supported_version=(0, 116, 0)` plus one fallback profile for missing or older/unvalidated versions.
  - The selected Codex profile will own a profile-private prompt behavior variant instance. The prompt behavior variant is not a second shared registry entry; the shared engine should only see the selected detector profile identity.
  - The prompt behavior variant should remain a separate composable object on the selected profile rather than being expressed as an inheritance-only override on a detector subclass. The detector registrations remain version-visible, but the varying prompt logic is injected into one shared Codex detector implementation.
  - Rationale: this keeps profile versioning and prompt behavior versioning aligned, which makes drift diagnosis and replay evidence easier to interpret.
  - Alternative considered: keep one Codex detector profile and add an internal prompt-variant selector hidden behind `builtin`. Rejected because it weakens observability and makes it harder to tell which behavior family made a classification.

- Keep the prompt behavior variant contract behavior-oriented rather than mechanism-oriented.
  - The stable contract is that the variant receives prompt-area snapshot content and returns a prompt classification. It is not constrained to brightness checks, placeholder string matching, or any other single technique.
  - The initial variant for the current Codex family may still use style/brightness evidence where that is the strongest available discriminator, but future variants may use any prompt-local evidence that remains robust.
  - Rationale: this preserves flexibility for upstream drift while still making the detector structure explicit.
  - Alternative considered: standardize the contract around style signatures only. Rejected because it would force future Codex support back through the same narrow assumption if upstream rendering evolves.

- Degrade unfamiliar prompt presentation conservatively and surface variant diagnostics.
  - If the selected prompt behavior variant cannot confidently distinguish placeholder presentation from real draft input while the prompt remains visible, the Codex profile will emit `editing_input=unknown` rather than manufacturing `yes` or `no`.
  - The profile should emit notes that include the selected detector/variant identity and an unrecognized-prompt marker so live-watch, fixtures, and replay debugging can show what drifted.
  - Rationale: false certainty is worse than temporary ambiguity for a drift-prone TUI region.
  - Alternative considered: default any visible prompt payload to `draft`. Rejected because it recreates the current sticky `editing=yes` failure mode when placeholder rendering changes.

- Cover the boundary with raw ANSI fixtures rather than stripped-text-only tests.
  - Prompt behavior variants should be validated with representative raw prompt-area fixtures for idle placeholder, typed draft, disabled input, dynamic placeholder flows, and unrecognized prompt presentation.
  - In this change, "disabled input" means the current Codex composer state where the prompt remains visible but input is disabled. Upstream currently renders this by dimming the prompt glyph and using the disabled-placeholder branch in `chat_composer.rs`; that case belongs in design/verification coverage because it is prompt-visible but not a user draft.
  - Verification work should migrate the existing prompt tests that currently couple directly to `_CODEX_PLACEHOLDER_TEXTS` and `_normalize_prompt_text()` so they instead validate behavior through the new prompt behavior boundary.
  - Rationale: the whole point of this change is to preserve freedom to use prompt-local rendering evidence when needed.

## Risks / Trade-offs

- [Risk] More Codex profile/variant classes increase maintenance overhead.
  - Mitigation: keep the interface narrow, start with one concrete version family plus fallback, and grow only when real drift appears.

- [Risk] Conservative `unknown` classifications may temporarily reduce dashboard certainty after an upstream Codex change.
  - Mitigation: prefer explicit notes and targeted fixture updates over silently wrong `editing=yes` results.

- [Risk] Version selection may still be missing or malformed in some flows.
  - Mitigation: keep a conservative fallback Codex profile whose prompt behavior variant is explicitly labeled as fallback and favors ambiguity over false positives.

- [Risk] Prompt behavior may drift independently of other Codex signals, creating profile proliferation.
  - Mitigation: allow one profile family to own small internal behavior variants if needed later, but keep version identity visible at the selected profile boundary first.

## Migration Plan

1. Refactor the existing `build_prompt_context()` extraction seam into a Codex prompt-area snapshot model plus a prompt behavior variant interface/result model inside the Codex tracker package.
2. Split Codex detector registration into an initial concrete `0.116.x` family (`minimum_supported_version=(0, 116, 0)`) plus a fallback profile, and wire each selected profile to its profile-private prompt behavior variant.
3. Move `editing_input` derivation to use the prompt behavior result instead of detector-local placeholder literal logic, with prompt-visible unrecognized presentation mapping to `editing_input=unknown` plus notes.
4. Add ANSI-backed unit fixtures and replay/live-watch assertions that verify placeholder, draft, disabled-input, and unknown classifications, and migrate existing prompt tests that currently assert the legacy placeholder heuristic directly.
5. Expose selected Codex detector/variant notes in debugging output so future prompt drift is visible in live runs.

Rollback strategy:

- Temporarily collapse Codex back to the fallback profile or reintroduce the previous prompt heuristic while a new version-family variant is authored and validated.

## Open Questions

- None for this v1 change. Future Codex prompt-render drift may require additional version-family profiles or variant implementations, but the boundary and initial decisions are fixed by this design.
