## Context

Mailbox skills are currently projected twice: once under the intended visible namespace `skills/mailbox/...` and again under `skills/.system/mailbox/...` as a compatibility mirror. The visible path is already the normative contract across runtime prompts, docs, and agent guidance, while the hidden path exists only because earlier mailbox-skill work tried to preserve a compatibility fallback.

That fallback now creates ongoing cost with no clear product value. Projection code has to duplicate assets, prompt builders have to explain two paths, demo packs stage both trees, and tests and docs keep carrying hidden-path language even though the desired agent behavior is to open `skills/mailbox/...` directly.

## Goals / Non-Goals

**Goals:**
- Make `skills/mailbox/...` the only supported mailbox skill projection surface.
- Remove hidden-path references from runtime-owned mailbox prompts, demo packs, fixture prompts, docs, and specs.
- Simplify mailbox skill projection and demo staging so repo-owned guidance no longer describes a compatibility-only mailbox namespace.

**Non-Goals:**
- Changing mailbox transport behavior, env-var naming, or the live mailbox binding resolver.
- Redesigning non-mailbox `.system` usage elsewhere in the repo.
- Preserving backward compatibility for old prompts, demos, or local homes that still open `skills/.system/mailbox/...`.

## Decisions

### Decision: Mailbox skills are projected only under `skills/mailbox/...`

Mailbox runtime projection will stop creating `skills/.system/mailbox/...` entirely. The source mailbox skill assets remain unchanged, but projection writes only the visible tree.

Rejected alternative:
- Keep the hidden mirror but stop mentioning it. This preserves duplicate artifact generation and leaves an undocumented compatibility surface that future work has to keep around accidentally.

### Decision: Runtime-owned mailbox prompts reference only the visible mailbox skill path

Mailbox prompts in runtime `mail` flows and gateway notifier flows will point only at `skills/mailbox/...`. They will no longer mention `.system` as a possible alternate path.

Rejected alternative:
- Mention both paths but de-emphasize the hidden one. This keeps prompt noise alive and weakens the cleanup by telling agents there are still two valid locations.

### Decision: Demo-pack and fixture-owned mailbox guidance drops hidden-path staging

Repo-owned demo packs and fixture prompts will be updated to stage and reference only `skills/mailbox/...`. Any current code path that uses hidden mailbox trees as an intermediate source will switch to the visible tree or directly to the packaged source assets.

Rejected alternative:
- Keep staging both trees in demos only. That would preserve the wrong contract in the most operator-visible examples and continue masking hidden-path dependencies.

### Decision: This is a direct breaking cleanup, not a phased deprecation

The repo’s current posture favors forward progress over compatibility shims. Since mailbox runtime behavior already treats the visible path as authoritative, this change should remove the hidden mirror outright instead of adding a warning-only transition period.

Rejected alternative:
- Deprecate the hidden path first. That would require keeping the duplicate projection, tests, and docs around for another cycle without solving the contract ambiguity.

## Risks / Trade-offs

- [Old prompts or local scripts may still open `skills/.system/mailbox/...`] → Update all repo-owned prompts and demos in the same change and treat external local breakage as an accepted breaking cleanup.
- [Demo-pack staging currently assumes a hidden-path source in one branch] → Refactor demo staging to use the visible mailbox tree or packaged assets directly, then update regression coverage.
- [Specs and docs may drift if only code changes] → Update the affected main specs and mailbox reference docs in the same change so the archived “compatibility mirror” language no longer looks normative.

## Migration Plan

1. Remove hidden mailbox projection from mailbox runtime support and any helper constants/functions that exist only for that path.
2. Update runtime mail prompts, gateway notifier prompts, demo-pack staging, and fixture prompts to reference only `skills/mailbox/...`.
3. Update tests that assert hidden mailbox files or hidden-path prompt text.
4. Update main OpenSpec specs and mailbox reference docs to remove the compatibility-mirror allowance.

Rollback is straightforward if needed: restore the hidden projection and hidden-path prompt text. No persisted mailbox data migration is involved.

## Open Questions

None.
