## Context

The mail ping-pong gateway demo builds participant brain homes from tracked recipes and then launches managed headless agents from the generated brain manifests. The tracked initiator and responder recipes already declare `launch_policy.operator_prompt_mode: unattended`, and the downstream launch-plan pipeline already knows how to consume that manifest field and apply provider-specific launch policy.

The current demo build path drops that field before calling `build_brain_home`. The resulting manifest therefore falls back to `interactive`, the launch plan records an interactive prompt-mode request, and launch-policy provenance is absent in the live managed-headless manifest. That means the demo is not exercising the intended unattended launch posture before kickoff begins.

## Goals / Non-Goals

**Goals:**
- Preserve the tracked recipe operator prompt mode when the demo pack builds participant brain homes.
- Keep the brain manifest as the source of truth for launch posture so the existing launch-plan pipeline applies unattended policy automatically.
- Add regression coverage that detects drift between tracked recipe launch intent and the actual live launch posture used by the demo pack.

**Non-Goals:**
- Redesign mailbox skill discovery or mailbox prompt wording in this change.
- Introduce a new headless launch API field just for the demo pack.
- Change the default meaning of omitted operator prompt mode for unrelated callers.

## Decisions

### Decision: Preserve operator prompt mode at brain-build time

The demo pack should pass `recipe.operator_prompt_mode` into `BuildRequest` when building participant homes.

Rationale:
- The recipe already owns this launch intent.
- `build_brain_home` already persists that intent into the runtime brain manifest.
- the launch-plan pipeline already reads the manifest field and applies unattended launch policy when present.

Alternative considered:
- Override launch posture later during `HoumaoHeadlessLaunchRequest`.
  Rejected because it duplicates launch intent outside the tracked recipe/manifest contract and bypasses the existing manifest-driven launch-policy path.

### Decision: Verify both build-time and live-launch posture

Regression coverage should check both:
- the generated brain manifest launch policy field, and
- the live managed-headless launch metadata or provenance after startup.

Rationale:
- a manifest-only assertion would miss later drift in the launch-plan or managed-launch path;
- a live-only assertion would make it harder to localize whether the drift started during build or during launch.

Alternative considered:
- Assert only that a tool-specific settings file or CLI arg appears.
  Rejected because the stable contract is operator prompt mode and launch-policy provenance, not one provider-specific side effect.

### Decision: Keep omitted mode behavior unchanged outside this demo path

This change should preserve the existing fallback to interactive posture when no recipe operator prompt mode is declared.

Rationale:
- the bug is specific to the demo pack failing to pass a tracked field it already has;
- changing global defaults would broaden scope and risk unrelated callers.

## Risks / Trade-offs

- [Mailbox issues may still remain after this fix] → Mitigation: rerun the interactive kickoff after the prompt-mode fix and treat any remaining mailbox-skill or approval problems as a separate change.
- [Other build paths may have the same omission] → Mitigation: keep this change scoped to the mail ping-pong demo pack, then follow up with a broader audit only if other callers show the same drift.
- [Provider launch policy details can evolve by tool version] → Mitigation: assert stable launch-policy provenance and requested operator prompt mode rather than overfitting tests to one concrete CLI arg or one config-file patch.

## Migration Plan

1. Update the demo brain-build path to pass through the tracked recipe operator prompt mode.
2. Extend the demo startup tests to assert the generated manifest preserves unattended mode.
3. Extend live-startup or inspect-oriented demo tests to assert the launched participants expose unattended launch-policy provenance when the tracked recipe requests it.
4. Refresh README or demo-facing notes only if they surface launch posture explicitly.

## Open Questions

- None for this scoped fix. If kickoff still fails after unattended posture is preserved, mailbox-skill invocation should be handled as a separate follow-up.
