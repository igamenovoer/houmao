## Context

`houmao-mgr project easy specialist create` currently persists prompt, auth, skill, and generated preset state, but it hardcodes an empty launch payload. That leaves easy-created specialists with no stored `launch.prompt_mode`, so later `project easy instance launch` builds an interactive brain manifest even on tool/backend pairs where Houmao already maintains unattended startup support.

That gap is especially visible for Claude Code and Codex on the normal easy TUI launch path. The runtime and launch-policy registry already know how to resolve unattended startup for maintained versions, but the higher-level easy authoring path fails to request that posture. The result is a misleading high-level workflow: the "easy" specialist path still drops operators into onboarding, trust, or approval prompts unless they manually edit low-level preset files.

The important ownership boundary is that prompt posture is part of reusable specialist semantics, not per-instance runtime ephemera. The catalog already has a first-class `launch_payload` field and the compatibility projection already renders that payload into preset YAML, so the system has a natural persistence seam for this behavior.

## Goals / Non-Goals

**Goals:**

- Make easy-created specialists default to unattended startup posture when the selected tool's maintained easy launch path supports it.
- Add an explicit specialist-creation opt-out flag named `--no-unattended`.
- Persist the chosen posture as specialist configuration in the catalog and generated preset, not as ad hoc runtime injection during instance launch.
- Keep `project easy instance launch` thin by having it honor the stored specialist launch payload.
- Surface the stored launch posture through specialist inspection so operators can see the effective config.

**Non-Goals:**

- Adding a generic `--prompt-mode` flag to `project easy specialist create` in this change.
- Injecting or overriding prompt mode directly on `project easy instance launch`.
- Backfilling or mutating existing specialists automatically.
- Expanding unattended support to tool/backend pairs that do not already have maintained launch-policy coverage.
- Folding the separate `project easy instance launch --launch-env` proposal into this change.

## Decisions

### Decision: Persist unattended default on the specialist, not on the launched instance

`project easy specialist create` will decide the default startup posture and persist it in the catalog-backed specialist `launch_payload`, which then renders into the generated preset's `launch.prompt_mode`.

`project easy instance launch` will continue to delegate to the existing managed-agent launch flow and will not inject or rewrite prompt mode at runtime.

Rationale:

- Prompt posture is part of the reusable specialist contract.
- Persisting it on the specialist keeps first launch, relaunch, and inspection aligned.
- The catalog and preset projection already provide the right persistence seam.

Alternative considered:

- Inject unattended behavior from `project easy instance launch`.
  Rejected because it hides reusable startup semantics in a per-instance wrapper and makes specialist inspection incomplete or misleading.

### Decision: Supported easy-created TUI specialists default to unattended, with `--no-unattended` as the opt-out

`project easy specialist create` will default to unattended for supported tools and will accept `--no-unattended` to persist explicit interactive startup instead.

The opt-out will write explicit interactive posture rather than omitting launch payload entirely.

Rationale:

- Easy is the higher-level operator path and should prefer the maintained no-prompt startup contract when available.
- Explicit interactive storage makes operator intent inspectable and avoids conflating legacy "no stored launch payload" artifacts with deliberate opt-out.

Alternative considered:

- Keep the default interactive and ask users to opt into unattended manually.
  Rejected because it preserves the current surprising behavior and forces low-level preset edits for the common happy path.

### Decision: Tool scope is conditional on maintained unattended support

This change will default only tools whose maintained easy-launch path already supports unattended startup through Houmao's launch-policy contract.

In the current tree that means:

- Claude easy specialists default to unattended on the interactive raw-launch path.
- Codex easy specialists default to unattended on the interactive raw-launch path.
- Gemini easy specialists do not receive unattended injection from this change.

Rationale:

- Claude and Codex already have maintained unattended launch-policy support on the relevant surfaces.
- Gemini is currently headless-only in `project easy instance launch`, and this change should not synthesize a startup posture that the maintained runtime contract does not cover.

Alternative considered:

- Apply unattended defaults uniformly to every easy-created specialist.
  Rejected because unsupported tool/backend pairs would fail unexpectedly and blur the boundary between maintained and aspirational support.

### Decision: Specialist inspection should expose stored launch posture

`project easy specialist get` will report the persisted launch payload, and the compatibility preset generated for the specialist will continue to render the same payload under `launch`.

Rationale:

- If unattended is part of specialist config, operators need a direct inspection path.
- The current `specialist get` payload already reports other specialist semantics and generated artifacts; launch posture belongs in that same view.

Alternative considered:

- Persist launch posture silently and require operators to inspect the preset YAML manually.
  Rejected because it undermines the high-level easy UX and hides part of the specialist contract.

## Risks / Trade-offs

- [Risk] Default unattended posture may fail closed for a supported tool if the installed version drifts outside the maintained strategy range.
  → Mitigation: preserve existing fail-closed launch-policy behavior and provide `--no-unattended` as the escape hatch.

- [Risk] Existing specialists created before this change will keep their legacy silent launch payload and therefore continue launching interactively unless updated.
  → Mitigation: document that this is a forward-looking default for newly created specialists and keep manual low-level preset editing available.

- [Risk] The active `project easy instance launch --launch-env` change also touches launch semantics, creating review overlap.
  → Mitigation: keep responsibilities separate: prompt mode remains specialist-owned config; launch env remains per-instance runtime input.

## Migration Plan

- No mandatory data migration is required.
- Newly created easy specialists will persist explicit launch prompt mode according to the new default/opt-out rules.
- Existing specialists remain valid and unchanged.
- Operators who want existing specialists to adopt the new behavior can recreate them or edit the generated preset through the low-level project surfaces.
- Rollback is low risk because `launch.prompt_mode` is already part of the canonical preset schema; the system can stop defaulting it without invalidating persisted specialists.

## Open Questions

- Whether `project easy specialist list` should surface a compact launch summary in addition to `specialist get` is still optional. This change only requires `specialist get` to expose the stored launch posture clearly.
