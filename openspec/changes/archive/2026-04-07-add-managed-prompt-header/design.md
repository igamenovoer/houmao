## Context

Managed launch already has one effective-prompt pipeline:

1. load the role prompt from the selected role package,
2. apply any launch-profile-owned prompt overlay,
3. hand the resulting prompt to backend-specific injection planning,
4. persist enough build and runtime metadata for later relaunch and resume.

That pipeline is used by local managed launch, easy-lane delegated launch, runtime relaunch, and the compatibility launch projection that generates provider-facing profiles from role content. Today it has no first-class managed-runtime prelude, so agents can launch without any explicit awareness that they are Houmao-managed or which Houmao-owned interfaces are authoritative for Houmao-specific work.

The new behavior needs to be cross-cutting but still predictable. It must not turn into a second bootstrap prompt that is replayed separately from the role prompt, and it must give operators a clean opt-out because promptless or minimal roles are still valid workflows in this repository.

## Goals / Non-Goals

**Goals:**
- Add one default-on Houmao-managed prompt header for managed launch flows.
- Keep the header general and stable: mention Houmao management, the managed identity, bundled Houmao guidance, and `houmao-mgr` as the canonical direct interface without naming specific packaged guidance entries.
- Make the header part of the effective launch prompt before backend-specific role injection so runtime resume and relaunch stay coherent.
- Support explicit disable and force-enable controls at operator-facing launch surfaces, with reusable launch-profile storage for the profile-backed lanes.
- Keep local managed launch, easy launch, relaunch, and compatibility-generated launch prompts on one shared composition contract.

**Non-Goals:**
- Rewriting the prompt of already-running joined sessions.
- Introducing a new list of prompt-named packaged guidance entries into the managed header.
- Adding a new raw `houmao-server` API knob in this change for every compatibility or native launch path.
- Making the system-wide default configurable beyond the change-defined default-on behavior.

## Decisions

### 1. Treat the managed header as part of the effective launch prompt

The managed header will be composed into the effective launch prompt rather than sent as an unrelated extra bootstrap message.

Composition order:

1. source role prompt
2. launch-profile prompt overlay resolution (`append` or `replace`)
3. managed prompt header prepend when enabled
4. backend-specific prompt injection

Rationale:
- Houmao already has one prompt-composition seam. Reusing it keeps relaunch, resume, and compatibility launch behavior aligned.
- Applying the managed header after overlay resolution means profile-owned `replace` overlays cannot silently remove the Houmao-owned managed prelude.
- Backends continue to see one prompt payload, which avoids special-case bootstrap replay logic.

Alternatives considered:
- Send the managed header as a separate first-turn bootstrap message. Rejected because it creates replay ambiguity and diverges from the existing launch-profile overlay contract.
- Prepend the managed header before overlay resolution. Rejected because profile-owned `replace` would erase the managed header.

### 2. Use a tri-state managed-header policy with launch-time override precedence

The managed-header policy will resolve through three states:

- `inherit` (`null` in stored launch-profile state): use the system default
- `enabled`
- `disabled`

Resolution order:

1. explicit one-shot launch override
2. stored launch-profile policy when present
3. system default (`enabled`)

Operator-facing CLI:
- direct launch and easy-instance launch get `--managed-header` and `--no-managed-header`
- explicit launch-profile add/set get `--managed-header`, `--no-managed-header`, and `--clear-managed-header`
- easy-profile create gets `--managed-header` and `--no-managed-header`

Rationale:
- The user asked for an explicit disable path, and launch-time override is the least surprising way to provide it.
- Reusing launch-profile storage lets the profile-backed lanes keep reusable birth-time policy with the rest of launch configuration.
- `inherit` preserves forward compatibility if Houmao later adds a configurable global default.

Alternatives considered:
- Boolean-only storage with no inherit state. Rejected because it bakes the current system default into every stored profile and makes future default changes harder.
- Launch-time flag only with no stored launch-profile policy. Rejected because profile-backed launch is explicitly the reusable birth-time configuration lane.

### 3. Resolve managed identity before rendering the header and persist structured header metadata

Header rendering will happen only after managed identity resolution has settled on the effective managed name and id. The rendered header will use the same canonical managed identity that the launch result and registry publish.

The build manifest will persist:
- the final effective launch prompt in `inputs.role_prompt_text` for managed launches,
- structured managed-header metadata sufficient for inspection and relaunch decisions, including version, resolved enabled state, and the rendered identity fields.

Rationale:
- The header must not present a different identity from the runtime registry.
- Persisting the final prompt keeps relaunch deterministic for launches created after this change.
- Persisting structured header metadata makes debugging and future migrations easier than treating the header as an opaque text mutation.

Alternatives considered:
- Render the header directly from raw CLI input before identity normalization. Rejected because the header could drift from the published managed identity.
- Persist only the final prompt string. Rejected because it makes later reasoning about why a header exists or how it was decided much harder.

### 4. Recompute on relaunch when older manifests lack managed-header metadata

New managed launches will persist the final effective launch prompt and managed-header metadata. Older manifests created before this change will not have that data.

For relaunch of older managed manifests:
- if persisted effective launch prompt and managed-header metadata exist, relaunch reuses them;
- otherwise relaunch recomputes the managed header using the current managed identity plus the change-defined default-on policy.

Rationale:
- `agents relaunch` remains a managed launcher and should not silently miss the managed header forever just because the original manifest predates the change.
- Older manifests had no way to opt out, so default-on recomposition is consistent with the new product default.

Alternatives considered:
- Preserve older relaunch behavior forever when metadata is missing. Rejected because it produces long-lived drift between fresh launch and relaunch.

### 5. Keep compatibility-generated launch prompts on the same helper, but defer raw API knobs

The compatibility launch projection that currently derives provider-facing profile prompts from the raw resolved role prompt will switch to the same managed-prompt composition helper used by local launch.

This change will not add a new raw `houmao-server` request field for managed-header control. Operator-facing CLI launchers are the supported opt-out surface in this change.

Rationale:
- Using the same helper avoids drift between local managed launch and compatibility-generated profiles.
- Deferring raw API knobs keeps the scope focused on the operator-facing launcher behavior the user asked for.

Alternatives considered:
- Leave compatibility projection unchanged. Rejected because it would create two different managed-launch prompt contracts.
- Add raw API knobs immediately. Rejected for scope control; the user asked for launcher behavior, not an API expansion.

### 6. Keep the header short and policy-like

The rendered managed header will:
- identify the agent as Houmao-managed,
- include managed name and id,
- tell the agent to prefer bundled Houmao guidance for Houmao-related workflows,
- state that `houmao-mgr` is the canonical direct interface to the Houmao system,
- direct the agent toward supported manifests, runtime metadata, and service interfaces rather than unsupported probing,
- avoid naming individual packaged guidance entries.

Rationale:
- The instruction needs to stay stable even when packaged guidance families are renamed or reorganized.
- A short policy header reduces token cost and avoids oversteering normal domain work.

## Risks / Trade-offs

- [Promptless managed roles stop being effectively promptless by default] → Provide explicit `--no-managed-header` and profile-owned disable policy, and document that as the supported escape hatch.
- [Longer effective prompt increases token cost] → Keep the header short, fixed-structure, and free of package-name inventories.
- [Operator confusion about precedence between source role, prompt overlay, and managed header] → Document the exact composition order in the launch-profiles guide and CLI reference.
- [Compatibility launch can now differ from older stored profile expectations] → Reuse one shared helper and record structured header metadata so behavior is inspectable.
- [Easy lane has create-time profile storage but no easy-profile patch command] → Support stored policy on easy-profile create and one-shot override on easy-instance launch; defer any easy-profile patch expansion to a separate change.

## Migration Plan

1. Add one optional launch-profile storage field for managed-header policy with `null` meaning inherit.
2. Default absent policy to enabled during launch resolution.
3. Update managed launch builders to always persist the final effective launch prompt and managed-header metadata for new launches.
4. Update relaunch to reuse persisted metadata when present and to recompute with default-on behavior for older manifests that lack the new metadata.
5. Update compatibility launch projection to derive provider-facing prompts from the same managed-prompt composition helper.
6. Update launch-profile and CLI docs together with the implementation so the new precedence and opt-out behavior are discoverable.

Rollback:
- The new launch-profile field is optional, so older code can ignore it safely.
- If the feature must be disabled in a follow-up, Houmao can stop composing the managed header while leaving stored `null/true/false` launch-profile policy values inert until a later cleanup.

## Open Questions

- None for this change. A future follow-up may add raw `houmao-server` launch-surface controls if automation needs the same managed-header opt-out outside the operator-facing CLI.
