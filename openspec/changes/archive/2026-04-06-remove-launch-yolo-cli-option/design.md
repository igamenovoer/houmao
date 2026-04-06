## Context

Houmao currently has two overlapping ways to influence launch autonomy on managed local launches:

- the resolved `launch.prompt_mode` contract, which already distinguishes `unattended` from `as_is`
- a separate Houmao CLI `--yolo` flag on `agents launch` and `project easy instance launch`, which only suppresses Houmao's own workspace trust confirmation

That split creates an inconsistent operator model. `launch.prompt_mode` already feeds the runtime and launch-policy system, where `as_is` means no launch policy is applied and `unattended` allows provider-specific no-prompt posture to be enforced. The extra Houmao `--yolo` flag sits outside that model, causes easy-launch commands to fail unless callers remember a redundant bypass flag, and introduces a second launch-time control surface that is not stored in presets or specialists.

This change is cross-cutting because the flag appears in:

- the native `houmao-mgr agents launch` CLI
- the higher-level `houmao-mgr project easy instance launch` CLI
- system-skill guidance, docs, demos, manual smoke flows, and many tests

It also requires care not to conflate Houmao's launch-surface `--yolo` with provider-owned autonomy controls such as Gemini `--approval-mode=yolo` or compatibility-adapter command lines that still use a provider's own `--yolo` spelling.

## Goals / Non-Goals

**Goals:**

- Remove the user-facing Houmao `--yolo` option from managed local launch surfaces.
- Remove Houmao's own pre-launch workspace trust confirmation from those launch surfaces.
- Make `launch.prompt_mode` the only Houmao-level contract that determines whether launch is raw (`as_is`) or no-prompt/fully automated (`unattended`).
- Preserve existing provider/runtime launch-policy ownership for unattended startup.
- Update docs, tests, demos, and skills so they stop telling operators to pass `--yolo` to Houmao launch commands.

**Non-Goals:**

- Changing the stored `launch.prompt_mode` vocabulary or defaults.
- Redefining provider-specific unattended strategies that already own their no-prompt launch surfaces.
- Removing provider-owned `yolo` semantics from downstream tools or compatibility adapters.
- Rewriting archived OpenSpec change history just to scrub historical `--yolo` references.

## Decisions

### 1. Remove the Houmao launch-surface `--yolo` option entirely

`houmao-mgr agents launch` and `houmao-mgr project easy instance launch` will no longer accept `--yolo`.

Rationale:

- the flag is not part of the durable preset or specialist contract
- it duplicates behavior that operators already expect from `launch.prompt_mode`
- the repository explicitly allows breaking changes, so keeping a misleading compatibility alias is lower value than making the contract explicit

Alternatives considered:

- Keep `--yolo` as a hidden no-op alias.
  Rejected because it preserves misleading documentation and lets callers keep depending on a control surface that should no longer exist.
- Reinterpret `--yolo` as a shortcut for `unattended`.
  Rejected because launch autonomy belongs to preset/specialist state, not to an ad hoc launch-time flag layered on top.

### 2. Remove Houmao's pre-launch workspace trust prompt instead of conditioning it on prompt mode

The managed local launch path currently asks for Houmao-owned workspace trust before resolving the preset's effective prompt mode. This change removes that prompt rather than moving it later and suppressing it only for unattended launches.

Rationale:

- moving the prompt later would still preserve a second Houmao-owned launch control plane
- unconditional removal keeps the launch path aligned with the existing runtime contract: `unattended` may apply maintained no-prompt provider posture, `as_is` stays raw
- the launch code becomes simpler because the shared local launch helper no longer needs trust-confirmation plumbing

Alternatives considered:

- Keep the prompt only for `as_is`.
  Rejected because `as_is` is already defined as "no launch policy is applied," not "Houmao asks for a second confirmation before provider startup."
- Keep the prompt only for some providers.
  Rejected because the prompt is Houmao-owned behavior, while provider trust/posture behavior is already modeled downstream.

### 3. Treat `launch.prompt_mode` as the sole Houmao-level autonomy contract

After this change:

- `unattended` continues to allow maintained provider launch-policy strategies to apply owned no-prompt or full-autonomy posture
- `as_is` continues to bypass those unattended strategy mutations and leaves provider approval posture to the user or provider defaults

Rationale:

- this matches the existing launch-policy documentation and runtime manifests
- it keeps specialist and preset semantics aligned across direct launch and project-easy launch
- it gives operators one durable place to express autonomy intent

Alternatives considered:

- Introduce a second explicit launch-autonomy field just for local launches.
  Rejected because the system already has `launch.prompt_mode`, and a second field would recreate the same ambiguity in a new form.

### 4. Keep provider-owned `yolo` behavior untouched

This change only removes Houmao's CLI-level `--yolo`. It does not change:

- Gemini unattended strategy injection of `--approval-mode=yolo`
- provider-hook canonicalization of provider launch args
- compatibility-provider commands that use the provider's own `--yolo` argument

Rationale:

- those surfaces are tool-specific behavior owned by provider contracts and unattended strategy registries
- removing them would be a separate behavior change with different semantics and risk

Alternatives considered:

- Remove all visible `yolo` strings everywhere for consistency.
  Rejected because identical spelling does not mean identical contract. Houmao's CLI option and provider-owned approval settings are different surfaces.

## Risks / Trade-offs

- [Breaking existing launch scripts] → Update docs, demos, tests, and manual flows in the same change; document that callers must simply stop passing `--yolo`.
- [Operators lose an explicit Houmao trust acknowledgment step] → Keep the contract centered on prompt mode and provider controls; `as_is` still preserves provider-owned prompts and defaults.
- [Confusion between removed Houmao `--yolo` and retained provider-owned `yolo` semantics] → Call out the distinction explicitly in specs and user docs.
- [Easy-launch behavior may look different to users who relied on `--yolo` as a required incantation] → Update project-easy docs to state that stored specialist launch posture already owns autonomy and no separate bypass flag exists.

## Migration Plan

1. Remove `--yolo` from the native and project-easy managed launch CLI surfaces and delete the shared Houmao trust-confirmation plumbing.
2. Update the relevant OpenSpec launch contracts so the public CLI no longer documents or requires the flag.
3. Update all first-party docs, skills, demos, manual smoke flows, and tests to stop passing `--yolo` to Houmao launch commands.
4. Communicate the behavioral migration plainly: if callers previously passed `--yolo`, they now omit it; if they want provider-controlled prompting, they store or select `launch.prompt_mode: as_is`.

Rollback, if needed, is straightforward code reintroduction because no persistent data migration is involved.

## Open Questions

None.
