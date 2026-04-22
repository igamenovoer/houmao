## Context

Current reused-home behavior mixes two different operator stories:

1. "start a fresh launch but keep the old home path"
2. "restart the same logical agent after editing the stored launch profile"

The current specs and code lean toward the first story. They treat `--reuse-home` as a fresh launch against a compatible preserved home, keep it relaunch-distinct, and do not promise default reuse of the previous tmux session name. That clashes with the operator assumptions for profile-backed restart:

- the prior agent is already down,
- the prior tmux session is already gone,
- the stored launch profile may have been edited since the old run,
- the operator wants the preserved home reused in place,
- Houmao-managed projection targets should be refreshed from the updated launch inputs,
- the restarted agent should come back under the same tmux session name when possible,
- the stopped registry record should remain sufficient restart authority without a separate cleanup round.

The change is cross-cutting because it affects CLI contract, predecessor-home resolution, runtime start identity selection, and lifecycle continuity expectations.

## Goals / Non-Goals

**Goals:**
- Define `--reuse-home` as a stopped-agent restart workflow rather than a generic fresh-launch variant.
- Make the current launch inputs authoritative for reprojection onto the preserved home, especially for launch-profile-backed restart after profile edits.
- Make preserved-home compatibility depend on the same CLI tool type rather than frozen specialist or profile settings, so restart can follow updated stored configuration safely.
- Preserve non-destructive in-place projection behavior for Houmao-managed outputs while leaving untouched files alone.
- Use stopped lifecycle metadata as restart authority so operators do not need manual registry cleanup before a reused-home restart.
- Default reused-home restart to the previous tmux session name when the stopped record provides one and the operator does not override it.
- Keep live-owner handling explicit and separate from reused-home restart.

**Non-Goals:**
- Support `--reuse-home` as a live takeover shortcut for still-running agents.
- Redesign ordinary `agents relaunch` semantics for active or stopped sessions outside the reused-home launch path.
- Introduce destructive cleanup into reused-home restart.
- Guarantee cleanup or repair of stale files outside the Houmao-managed projection targets rewritten during restart.

## Decisions

### Decision: Model `--reuse-home` as stopped-agent continuity restart

Reused-home launch will be specified as a restart flow for a stopped logical managed agent, not as a fresh launch that merely happens to reuse a home path.

That means the command contract assumes:
- the prior runtime is already down,
- the prior tmux session is absent,
- the stopped lifecycle record plus preserved manifest/home state are the continuity anchor.

This matches the operator mental model and removes ambiguity about whether `--reuse-home` is supposed to replace a live owner.

Alternatives considered:
- Keep the current "fresh launch on preserved home" model and just document it better: rejected because it still mismatches the intended operator workflow after launch-profile edits.
- Expand reused-home into a hybrid flow that can either restart a stopped agent or force-take over a live one: rejected because it overloads the flag with two different safety models.

### Decision: Current launch inputs overwrite the same Houmao-managed projection targets

For reused-home restart, Houmao will treat the current launch inputs as authoritative and reproject them onto the preserved home before startup.

For launch-profile-backed restart, "current launch inputs" means the currently stored profile state plus any stronger direct CLI overrides. This is what makes profile edits meaningful for the restarted agent without mutating the already stopped historical instance.

For specialist-backed restart, the same rule applies: current specialist-backed launch inputs may differ from the prior run as long as the CLI tool type remains the same. The restart is intended to carry forward logical-agent continuity and preserved-home continuity, not to freeze specialist settings forever.

The overwrite scope remains the Houmao-managed projection surface:
- setup/auth/skills/helper/build-manifest style outputs are rewritten,
- untouched provider-owned or operator-owned files outside those targets remain in place.

Alternatives considered:
- Reuse the old preserved manifest verbatim and ignore stored profile edits: rejected because it defeats the main operator reason to restart from an updated profile.
- Rebuild the entire home destructively: rejected because it contradicts the preserved-home intent.

### Decision: Compatibility is keyed to CLI tool type, not unchanged specialist settings

Reused-home compatibility will require the same managed identity, same runtime root, same preserved-home path availability, and the same CLI tool type as the current launch.

Specialist-backed or profile-backed settings may change between runs. Those changed settings are exactly what the reprojection step is meant to apply onto the preserved home. The safety boundary is the CLI tool type, because provider-owned state inside the preserved home is tool-specific.

Alternatives considered:
- Require the same specialist or unchanged launch-profile contents: rejected because it would wrongly block the intended “edit settings, then restart on the same home” workflow.
- Allow cross-tool reused-home restart: rejected because preserved provider-owned state is not portable across CLI tool types.

### Decision: Reused-home restart defaults to the previous tmux session name

When the stopped lifecycle record exposes the prior tmux session name and the caller does not supply `--session-name`, reused-home restart will request that same tmux session name.

If the caller supplies `--session-name`, that explicit override remains stronger.

If the prior session name is unexpectedly occupied by some other live tmux session, the restart should fail clearly rather than silently choosing a different session name. Silent renaming would break continuity expectations and make debugging harder.

Alternatives considered:
- Always derive a brand-new tmux session name: rejected because it breaks the stated continuity goal.
- Fall back silently to a generated name when the old one is unavailable: rejected because it hides a real operator-visible conflict.

### Decision: Stopped registry state remains the restart anchor and does not require pre-cleanup

Reused-home restart will consume the stopped registry/session metadata directly instead of requiring operators to clean registry state first.

The stopped record already carries the preserved-home and last-session continuity information needed to restart the same logical agent. Cleanup remains a separate artifact-retirement workflow, not a prerequisite for restart.

Alternatives considered:
- Require `agents cleanup session` before every reused-home restart: rejected because it destroys the continuity anchor the restart wants to use.
- Ignore registry state and scan homes directly: rejected because it weakens identity continuity and makes restart resolution less trustworthy.

## Risks / Trade-offs

- Tighter stopped-only semantics may surprise operators who previously treated `--reuse-home` as a generic replacement flag -> Mitigation: update the CLI-facing specs and help text to make live-owner rejection explicit and route takeover use cases to stop-first flows.
- Updated-profile reprojection can leave stale untouched files in the preserved home -> Mitigation: keep the overwrite contract explicit and limited to Houmao-managed projection targets, matching existing keep-stale behavior.
- Prior tmux session-name reuse can fail if another session now occupies that name -> Mitigation: fail clearly and let the operator choose whether to free that name or pass an explicit override.
- Stopped-record continuity depends on registry/session metadata staying intact until restart -> Mitigation: make cleanup non-prerequisite and keep stopped lifecycle metadata as the supported restart source of truth.

## Migration Plan

1. Update CLI contract and validation for `--reuse-home` on `agents launch` and `project easy instance launch` to describe stopped-agent restart semantics.
2. Update predecessor-home resolution so reused-home restart targets stopped continuity records directly, keys compatibility to same CLI tool type, and rejects live-owner usage for this workflow.
3. Update runtime startup identity selection so reused-home restart prefers the previous tmux session name when available and not explicitly overridden.
4. Preserve current non-destructive reprojection behavior onto the reused home, but document that current launch-profile state is the authoritative source for profile-backed restart.
5. Add regression coverage for stopped-record restart, updated-profile reprojection, registry-without-cleanup restart, and same-session-name restoration.

Rollback is spec-and-code local: revert the restart-specific validation and session-name reuse behavior, returning `--reuse-home` to preserved-home fresh launch semantics.

## Open Questions

None at the proposal stage. The intended operator model is now explicit enough to drive implementation.
