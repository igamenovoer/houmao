## Context

The current Houmao prompt-policy model was introduced when the system primarily needed one way to request startup-prompt suppression: `operator_prompt_mode = unattended`. Everything else fell into a bucket called `interactive`, and omission also defaulted to that same pass-through behavior. Over time that leaked into declarative presets (`launch.prompt_mode`), direct build inputs (`BuildRequest.operator_prompt_mode`), resolved manifests (`launch_policy.operator_prompt_mode`), launch-policy requests/provenance, runtime diagnostics, CLI help text, tests, and docs.

That model is now actively misleading. The real distinction is not "interactive" versus "unattended"; it is "force unattended launch policy" versus "leave provider startup as-is." For Houmao's main users, who primarily run automated managed sessions, unattended should be the normal default rather than the explicit special case.

Because the old vocabulary propagates across construction, runtime, schemas, and documentation, this is not a narrow `project easy` tweak anymore. The historical change id stays the same, but the actual design scope is one repository-wide semantic cleanup that preserves the current key paths while replacing the mode vocabulary and default behavior consistently.

## Goals / Non-Goals

**Goals:**

- Keep existing key names such as `launch.prompt_mode`, `BuildRequest.operator_prompt_mode`, and `launch_policy.operator_prompt_mode`.
- Replace the allowed mode vocabulary repository-wide with `unattended` and `as_is`.
- Make omitted prompt policy resolve to unattended rather than pass-through.
- Define `as_is` precisely as "no unattended injection and no launch-policy strategy resolution."
- Keep `project easy specialist create` aligned with the new default by persisting unattended unless the operator passes `--no-unattended`.
- Keep high-level and low-level authoring surfaces, build manifests, runtime launch planning, provenance, and docs internally coherent.

**Non-Goals:**

- Renaming the existing key paths to a different field name such as `force_unattended`.
- Preserving `interactive` as a long-term supported policy value.
- Backward-compatibility shims that silently reinterpret `interactive` forever.
- Changing the strategy registry's core purpose from unattended-only launch-policy declarations to a generic pass-through policy registry.
- Implementing unrelated `project easy instance launch --launch-env` work in the same change.

## Decisions

### Decision: Keep key names, but replace the mode vocabulary everywhere with `unattended|as_is`

The repository will keep existing key paths:

- declarative preset YAML at `launch.prompt_mode`
- direct build inputs at `BuildRequest.operator_prompt_mode`
- resolved brain manifest at `launch_policy.operator_prompt_mode`
- launch-policy request/provenance fields such as `requested_operator_prompt_mode`

But the allowed mode values across those seams will become:

- `unattended`
- `as_is`

`interactive` will be removed from the canonical model instead of preserved as a hidden synonym.

Rationale:

- The current key names are already broadly wired through the system and changing them would create unnecessary structural churn.
- The misleading part is the value vocabulary and default semantics, not the key nesting.
- Using the same values across declarative, build, manifest, and runtime seams preserves conceptual integrity.

Alternative considered:

- Rename the public key to `launch.force_unattended` while leaving internals on `interactive|unattended`.
  Rejected because it creates a split-brain model where external config says one thing and runtime diagnostics still say another.

### Decision: `as_is` means explicit pass-through with no unattended strategy work

`as_is` will mean:

- do not resolve unattended launch-policy strategy compatibility
- do not mutate runtime-owned provider state for no-prompt startup
- do not synthesize unattended CLI args
- launch the provider with its normal raw posture

This mode is not a promise that the launch is "interactive" in a human-facing sense. It is strictly a statement that Houmao should leave startup behavior alone.

Rationale:

- The automation-oriented default should be named positively (`unattended`) and the opt-out should describe what Houmao actually does (`as_is`).
- This wording scales across TUI and headless surfaces without implying UI modality.

Alternative considered:

- Keep using `interactive` as the pass-through label.
  Rejected because it keeps confusing transport/UI posture with launch-policy intent.

### Decision: Omitted prompt policy resolves to unattended

When prompt policy is omitted in preset YAML or direct build inputs, the system will resolve that omission to unattended behavior before writing the resolved brain manifest and before runtime launch-policy evaluation.

Authoring surfaces that create new presets should prefer writing the explicit default `launch.prompt_mode: unattended` rather than relying on omission to convey the default implicitly.

Rationale:

- Houmao's main operator posture is automation-first.
- This gives the repo one clear default instead of treating no-prompt startup as a niche opt-in.
- Explicit writing of the default reduces ambiguity for inspection and diff review.

Alternative considered:

- Keep omission as pass-through and only rename `interactive` to `as_is`.
  Rejected because it preserves the old default behavior that is causing the current surprise.

### Decision: `project easy` specializes the new default through explicit authored config, not runtime injection

`project easy specialist create` will persist explicit unattended posture by default in the specialist launch payload and generated preset. `--no-unattended` will persist explicit `as_is`.

`project easy instance launch` remains a thin wrapper that reads and honors stored specialist semantics. It will not add a second runtime-only defaulting rule.

Rationale:

- Reusable startup posture belongs to the reusable specialist object.
- This keeps first launch, relaunch, inspection, and low-level preset editing aligned.

Alternative considered:

- Have `project easy instance launch` treat omission as unattended while leaving specialist config silent.
  Rejected because it would hide reusable semantics in a per-instance wrapper and diverge from low-level preset-backed launch behavior.

### Decision: Runtime manifests and provenance adopt the same semantic vocabulary

Resolved brain manifests and typed runtime provenance will use the same `unattended|as_is` vocabulary rather than translating back into `interactive|unattended`.

That means:

- manifest `launch_policy.operator_prompt_mode` stores `unattended` or `as_is`
- launch-policy request metadata records `unattended` or `as_is`
- typed provenance remains a strategy-only structure and therefore is only present when unattended strategy resolution actually happened

Rationale:

- Runtime diagnostics should reflect the same intent model operators configured.
- Translating `as_is` back to `interactive` internally would keep the misleading vocabulary alive in exactly the places people inspect during debugging.

Alternative considered:

- Keep internal runtime/manifests on `interactive|unattended` and map `as_is -> interactive`.
  Rejected because it lowers implementation cost at the price of long-term conceptual inconsistency.

### Decision: This change is intentionally breaking for explicit `interactive` policy values

The repository will not preserve `interactive` as an accepted long-term declarative/build/runtime policy value. Existing repo-owned presets, tests, and docs will be updated to the new vocabulary as part of this refactor.

Rationale:

- The repository is under active unstable development and already allows breaking cleanup when the new design is clearer.
- Carrying `interactive` as a compatibility synonym would prolong the same ambiguity this change is meant to remove.

Alternative considered:

- Accept both `interactive` and `as_is` indefinitely.
  Rejected because it weakens the cleanup and forces every parser, validator, and doc surface to explain two names for the same pass-through behavior.

## Risks / Trade-offs

- [Risk] Silent preset omission changing from pass-through to unattended may cause existing launches to fail closed on unsupported tool/version pairs.
  → Mitigation: document the behavior break clearly, provide `as_is` as the explicit opt-out, and update repo-owned presets/examples in the same change.

- [Risk] The refactor touches many seams at once: parser, builder, runtime, schemas, CLI help, tests, fixtures, and specs.
  → Mitigation: keep the key names stable and focus the cleanup on one semantic dimension: mode values and default behavior.

- [Risk] Removing `interactive` immediately may break local untracked presets owned by developers.
  → Mitigation: treat this as an explicit breaking change under the repository's unstable-development policy rather than carrying a lingering compatibility alias.

- [Risk] Review overlap with the active `project easy instance launch --launch-env` change could blur ownership of launch semantics.
  → Mitigation: keep this change scoped to prompt-policy semantics and defaulting, while the launch-env change remains about per-instance runtime environment overlays.

## Migration Plan

- Update repo-owned preset fixtures, tests, docs, and OpenSpec artifacts from `interactive|unattended` semantics to `as_is|unattended`.
- Change parser/build/runtime validation to reject explicit `interactive` values and accept `as_is|unattended`.
- Change omitted prompt policy to resolve as unattended at construction time and for preset-backed launch flows.
- Update high-level authoring surfaces to emit explicit unattended defaults for newly created artifacts.
- Because this is an unstable-development repository, no backward-compatibility shim is required for persisted explicit `interactive` values; those artifacts should be rewritten to `as_is`.

## Open Questions

- Whether `specialist list` should surface a compact launch-policy summary remains optional. The core semantic cleanup only requires inspection surfaces to stop hiding the stored policy.
