## Context

Managed launch currently produces one effective prompt by flat string composition: launch-profile overlay is resolved onto the source role prompt, the managed header is prepended, and the resulting text is passed unchanged into backend-specific role injection. That works for today's managed header and profile overlay behavior, but it leaves no maintained way to add launch-only prompt guidance for one invocation and it makes multi-part prompt structure implicit rather than explicit.

This change crosses the launch CLI layer, brain construction, runtime relaunch/resume behavior, and compatibility prompt generation. The design needs to preserve the existing provider contract that backends receive one opaque prompt string while giving Houmao a structured way to render and persist prompt sections.

## Goals / Non-Goals

**Goals:**
- Add one-shot launch-only appendix input to maintained managed launch surfaces.
- Render the effective launch prompt as one structured envelope rooted at `<houmao_system_prompt>`.
- Preserve current managed-header policy resolution and launch-profile overlay semantics.
- Keep backend role-injection methods unchanged by delivering one final rendered prompt string.
- Persist enough secret-free layout metadata for relaunch, resume, and compatibility prompt generation to reuse the same prompt contract.

**Non-Goals:**
- Adding stored prompt appendix fields to reusable launch profiles in this change.
- Introducing a new backend-specific injection mode or provider-side XML protocol.
- Parsing rendered prompt tags back into structured data at runtime.
- Redesigning managed-header policy precedence or launch-profile overlay storage.

## Decisions

### 1. Introduce a section-based Houmao prompt composer

Houmao will move from ad hoc string concatenation to a dedicated prompt-composition layer that resolves prompt sections first and renders them last.

The rendered prompt will be rooted at `<houmao_system_prompt>`. Inside that envelope, Houmao will use readable section tags:
- `<managed_header>`
- `<prompt_body>`
- `<role_prompt>`
- `<launch_profile_overlay>`
- `<launch_appendix>`

Only the top-level tag is Houmao-prefixed. Inner tags stay generic to keep the rendered prompt readable.

Alternative considered: extending the current flat concatenation helper with more marker blocks. Rejected because it would keep prompt structure implicit and make later additions harder to reason about and test.

### 2. Keep backend role injection unchanged

Backends will continue to receive one final rendered prompt string through the existing role-injection methods (`native_developer_instructions`, `native_append_system_prompt`, `bootstrap_message`, `cao_profile`).

This change is therefore a prompt-rendering change, not a provider-launch protocol change. Providers do not need to understand the section tags; they only receive the final text.

Alternative considered: adding a dedicated launch-appendix bootstrap step or new injection method. Rejected because it would create backend drift and break the existing invariant that the effective launch prompt is composed before backend injection.

### 3. The new appendix is one-shot and append-only

Maintained launch surfaces will accept launch-only appendix input through:
- `--append-system-prompt-text`
- `--append-system-prompt-file`

Those options are mutually exclusive. They affect only the current launch and are not stored back into launch profiles, easy profiles, or role sources.

The appendix is append-only in this change. Houmao will not add a launch-time `replace` mode because launch-profile overlay already covers reusable append/replace behavior and a second replace surface would make precedence harder to understand.

### 4. Composition preserves current overlay semantics

Prompt-body resolution will follow this order:
1. Source role prompt
2. Launch-profile overlay resolution
3. Launch appendix append

Rendering will then wrap the result into the structured envelope:
- `<managed_header>` first when enabled
- `<prompt_body>` second when body content exists

Within `<prompt_body>`, section order will be:
1. `<role_prompt>` when the source role still participates
2. `<launch_profile_overlay>` when present
3. `<launch_appendix>` when present

If launch-profile overlay mode is `replace`, Houmao will omit `<role_prompt>` entirely rather than retaining an inactive copy. That preserves current effective-prompt semantics and avoids misleading prompt text.

### 5. Persist both the rendered prompt and secret-free layout metadata

New builds will continue to persist the final rendered prompt text as the launch-authoritative prompt body. In addition, brain construction will persist secret-free layout metadata under a Houmao-owned manifest key such as `inputs.houmao_system_prompt_layout`.

That metadata should record at minimum:
- layout version
- whether the structured layout was used
- rendered section kinds in order
- section attributes that are safe to persist, such as overlay mode or section source labels

Existing managed-header metadata can remain as its own secret-free manifest payload; the new layout metadata complements it rather than replacing it.

Alternative considered: persisting only the rendered prompt text. Rejected because relaunch/debug/inspection loses explicit section provenance and future prompt evolution becomes harder to inspect safely.

### 6. New launches use the new layout; older manifests remain relaunchable

For newly built manifests, relaunch, resume, and compatibility prompt generation should reuse the persisted rendered prompt contract and layout metadata.

For older manifests that lack the new layout metadata, Houmao should keep the current fallback posture: use persisted rendered prompt text when available and otherwise recompute with legacy managed-header rules as needed. This avoids a migration requirement for existing live or archived sessions.

## Risks / Trade-offs

- [Rendered XML-like tags may look noisy to the model] → Keep tags stable, few, and semantically obvious; avoid deeply nested or provider-specific markup.
- [User-supplied appendix text could itself contain tag-looking content] → Treat rendered markup as one-way presentation only; Houmao should never parse the final prompt text back into structured data.
- [Layout metadata could drift from the final prompt if multiple composition paths exist] → Route managed local launch, easy delegated launch, compatibility prompt generation, and resume fallback through one shared composer.
- [Another launch-time prompt surface could confuse operators alongside reusable profile overlays] → Make the appendix explicitly one-shot and append-only, and document that reusable append/replace behavior still belongs to launch profiles.

## Migration Plan

No external migration is required.

Implementation rollout:
1. Add the shared structured composer and layout metadata model.
2. Wire the composer into native managed launch, easy delegated launch, compatibility generation, and relaunch/resume.
3. Add the new CLI options and validation on the maintained launch surfaces.
4. Update tests and prompt-composition reference docs.

Rollback posture:
- Older code can continue to rely on persisted final prompt text.
- If the new layout metadata is ignored, the final rendered prompt still remains launch-authoritative for newly built sessions.

## Open Questions

None. The change intentionally keeps launch-time appendix semantics narrow: one-shot, append-only, structured render, and no new backend protocol.
