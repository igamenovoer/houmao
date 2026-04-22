## REMOVED Requirements

### Requirement: Managed local fresh launch can rebuild current launch inputs onto a preserved home
**Reason**: `--reuse-home` is no longer specified as a fresh launch variant. The updated contract treats it as restart of one stopped logical managed agent using preserved-home continuity metadata.
**Migration**: Use ordinary launch without `--reuse-home` when the operator wants a brand-new home. Use `--reuse-home` only for stopped-agent restart on a compatible preserved home.

### Requirement: Reused-home fresh launch remains non-destructive and relaunch-distinct
**Reason**: The updated contract keeps non-destructive reprojection but removes the "fresh-launch and relaunch-distinct" framing. Reused-home now intentionally restores stopped-agent continuity, including default reuse of the prior tmux session name when available.
**Migration**: Treat reused-home as stopped-agent restart continuity. Keep live takeover, destructive cleanup, and unrelated relaunch paths as separate workflows.

## ADDED Requirements

### Requirement: Managed local reused-home launch restarts one stopped logical agent on its preserved home
When a local managed launch explicitly requests reused-home mode, the runtime SHALL resolve one compatible stopped preserved managed home for the current managed identity from local lifecycle metadata before provider startup.

A preserved home SHALL be considered compatible only when all of the following are true:

- it belongs to the same managed identity selected for the current launch,
- it was recorded under the same local runtime root,
- it belongs to the same CLI tool type as the current launch,
- its preserved home path still exists on disk,
- its continuity metadata describes a stopped local managed-agent instance rather than a fresh live owner.

When compatible reused-home restart succeeds, the runtime SHALL rebuild the current launch's Houmao-managed setup projection, auth projection, skill projection, system-skill installation, launch helper, and build manifest onto that preserved home instead of allocating a new home id.

For profile-backed restart, the current stored launch-profile inputs together with any stronger direct CLI overrides SHALL be the authoritative source for that reprojection.

For specialist-backed restart, updated specialist-derived launch inputs MAY differ from the prior run and SHALL still be eligible for reused-home restart as long as the same CLI tool type is preserved.

The runtime SHALL preserve provider-owned or operator-owned files outside the paths that the reprojection explicitly rewrites.

The runtime SHALL use the stopped lifecycle record plus preserved manifest/home metadata as restart authority for the same logical managed agent and SHALL NOT require separate registry cleanup before restart.

When no compatible stopped preserved home exists, the runtime SHALL fail explicitly and SHALL NOT silently fall back to allocating a brand-new home.

#### Scenario: Stopped predecessor home is rebuilt for updated profile-backed restart
- **WHEN** stopped local managed agent `reviewer` preserves runtime home `/runtime/homes/codex-home-1`
- **AND WHEN** the current stored launch profile for `reviewer` has been updated since the prior run
- **AND WHEN** a new local managed launch resolves the same managed identity `reviewer`
- **AND WHEN** that launch explicitly requests reused-home mode
- **THEN** the runtime rebuilds current Houmao-managed launch material onto `/runtime/homes/codex-home-1`
- **AND THEN** the runtime does not allocate a new home id for that restart
- **AND THEN** the updated current launch-profile inputs govern the rewritten Houmao-managed projection targets
- **AND THEN** the restart does not require prior registry cleanup

#### Scenario: Updated specialist settings still allow reused-home restart when tool type stays the same
- **WHEN** stopped local managed agent `reviewer` preserves runtime home `/runtime/homes/codex-home-1`
- **AND WHEN** the current specialist-backed launch inputs for `reviewer` have changed since the prior run
- **AND WHEN** the current launch still resolves CLI tool type `codex`
- **AND WHEN** a new local managed launch resolves the same managed identity `reviewer` and explicitly requests reused-home mode
- **THEN** the runtime treats `/runtime/homes/codex-home-1` as compatible preserved-home restart authority
- **AND THEN** the updated current specialist-backed inputs are projected onto that preserved home before startup

#### Scenario: Missing compatible preserved home fails without fresh-home fallback
- **WHEN** a local managed launch explicitly requests reused-home mode
- **AND WHEN** no compatible stopped preserved home can be resolved for the selected managed identity
- **THEN** the runtime fails the launch clearly
- **AND THEN** it does not silently allocate a brand-new runtime home

### Requirement: Managed local reused-home restart preserves non-destructive continuity boundaries
Reused-home restart SHALL require the prior runtime to already be down. If a fresh live owner still exists for the same managed identity, the reused-home restart path SHALL fail rather than standing that owner down implicitly.

Reused-home restart SHALL remain non-destructive. It SHALL overwrite only the Houmao-managed projection targets selected by the current launch inputs and SHALL NOT introduce destructive `clean` semantics into this workflow.

When the stopped lifecycle metadata carries a prior tmux session name and the caller does not supply an explicit tmux session-name override, the runtime SHALL request restart using that same tmux session name.

When the caller supplies an explicit tmux session-name override, that override SHALL win over the stopped record's prior tmux session name.

If the prior tmux session name is currently occupied by another live tmux session and no stronger explicit override is supplied, the runtime SHALL fail clearly rather than silently choosing a different tmux session name.

Provider-local history that remains in the preserved home MAY stay available after startup through the preserved home, but the continuity contract for this change is the stopped logical managed agent plus its preserved home and session identity rather than automatic cleanup or silent session renaming.

#### Scenario: Live owner blocks reused-home restart
- **WHEN** a fresh live predecessor already owns managed identity `reviewer`
- **AND WHEN** a replacement local managed launch explicitly requests reused-home mode
- **THEN** the runtime rejects the reused-home restart
- **AND THEN** it does not implicitly stand down that live owner as part of the reused-home workflow

#### Scenario: Reused-home restart restores the prior tmux session name by default
- **WHEN** stopped local managed agent `reviewer` carries prior tmux session name `HOUMAO-reviewer-1700000000000`
- **AND WHEN** a replacement local managed launch explicitly requests reused-home mode without a stronger session-name override
- **AND WHEN** no live tmux session currently occupies `HOUMAO-reviewer-1700000000000`
- **THEN** the runtime starts the restarted agent using tmux session name `HOUMAO-reviewer-1700000000000`

#### Scenario: Occupied prior tmux session name fails clearly
- **WHEN** stopped local managed agent `reviewer` carries prior tmux session name `HOUMAO-reviewer-1700000000000`
- **AND WHEN** a different live tmux session currently occupies `HOUMAO-reviewer-1700000000000`
- **AND WHEN** a replacement local managed launch explicitly requests reused-home mode without a stronger session-name override
- **THEN** the runtime fails clearly
- **AND THEN** it does not silently generate a different tmux session name for that reused-home restart
