## Context

`add-houmao-mgr-cleanup-commands` introduced `houmao-mgr admin cleanup registry` with two distinct stale-classification modes for tmux-backed records:

- lease-only cleanup by default
- optional local tmux probing through `--probe-local-tmux`

Operationally, that default is too weak for a local maintenance command. A host-local registry cleanup that leaves lease-fresh dead tmux records behind still presents obviously stale `live_agents/` entries after the operator has already chosen to clean the local registry. The recent dry-run confirmed that behavior directly: plain cleanup preserved records as "lease remains fresh", while the same command with local tmux probing would remove all remaining entries because none of their owning tmux sessions still existed locally.

This follow-up change is intentionally narrow. It refines the default registry-cleanup contract without changing runtime publication, lease duration, or the broader grouped cleanup tree.

## Goals / Non-Goals

**Goals:**

- Make local tmux liveness probing the default stale-classification mode for tmux-backed registry cleanup.
- Replace the opt-in probe flag with an opt-out `--no-tmux-check`.
- Keep `--dry-run` semantics unchanged so operators can preview tmux-probe-based removals safely.
- Keep registry cleanup local-only and scoped to local host visibility.
- Update docs and tests so the default behavior and opt-out path are explicit.

**Non-Goals:**

- Change registry publication or lease-refresh logic.
- Change cleanup behavior for malformed or expired records.
- Add remote or server-backed registry cleanup APIs.
- Expand tmux probing to non-tmux registry records.
- Preserve the old `--probe-local-tmux` flag for compatibility in this unstable-development phase.

## Decisions

### Decision 1: Default registry cleanup to local tmux probing for tmux-backed records

`houmao-mgr admin cleanup registry` will enable local tmux liveness probing by default. For tmux-backed records:

- if the record is malformed or expired beyond the grace period, it remains removable as before
- if the record is lease-fresh and the owning tmux session is absent locally, it becomes removable by default
- if the record is lease-fresh and the owning tmux session exists locally, it remains preserved

Non-tmux records keep the existing lease-based behavior because there is no tmux session to probe.

Rationale:

- The command is explicitly local maintenance over local registry state.
- A lease-fresh dead tmux record is operationally stale for same-host discovery and cleanup.
- The default should match what operators mean by "clean up stale registry state" on the current host.

Alternatives considered:

- Keep lease-only cleanup as the default: rejected because it leaves obviously dead local tmux records behind and requires operators to remember an extra flag for the more useful local behavior.
- Remove lease-based checks entirely and rely only on tmux probing: rejected because malformed or expired records still need direct stale classification even when tmux probing is unavailable or irrelevant.

### Decision 2: Replace `--probe-local-tmux` with `--no-tmux-check`

The registry cleanup CLI contract will flip from opt-in probing to opt-out probing:

- default mode: probe tmux locally for tmux-backed records
- opt-out mode: `--no-tmux-check`

The compatibility alias `houmao-mgr admin cleanup-registry` will inherit the same new flag contract.

Rationale:

- The user intent is to make tmux checking normal behavior, not an advanced option.
- An explicit skip flag better communicates that lease-only cleanup is the exceptional path.

Alternatives considered:

- Keep both flags and let them conflict: rejected because it adds avoidable CLI ambiguity.
- Keep `--probe-local-tmux` while changing the default: rejected because the flag name would become misleading once probing is already enabled.

### Decision 3: Keep payload reporting centered on effective probing state

The cleanup result payload will continue to expose whether probing occurred, but the CLI option name no longer drives the meaning. The output should communicate the effective mode, not force consumers to reconstruct it from a negative CLI flag.

Rationale:

- Downstream tooling and tests benefit from a positive effective-mode signal.
- The behavioral change is the default, not the JSON structure.

Alternatives considered:

- Rename all JSON fields to `skip_tmux_check`: rejected because the CLI opt-out spelling is not the most useful machine-readable state representation.
- Remove probing state from the payload entirely: rejected because dry-run output should explain why a fresh record was removable or preserved.

## Risks / Trade-offs

- [Risk] A tmux visibility gap could classify a live session as stale when the local process cannot see the owning tmux server. → Mitigation: keep `--no-tmux-check` as an explicit opt-out for lease-only behavior.
- [Risk] Operators used to lease-only cleanup may see more removals than before. → Mitigation: keep `--dry-run` intact and document the new default clearly.
- [Risk] The flag rename could break local habits or scripts. → Mitigation: this repository is in unstable development, and the new default/flag pair is simpler than preserving both opt-in and opt-out forms.

## Migration Plan

1. Change registry cleanup defaults in the native CLI to probe tmux by default and expose `--no-tmux-check`.
2. Update registry cleanup classification logic so lease-fresh tmux-backed records are removed by default when their owning tmux session is absent locally.
3. Update dry-run tests, help-surface tests, and operator docs to reflect the new default.
4. Keep `houmao-mgr admin cleanup-registry` as the command-path compatibility alias, but apply the new default and opt-out flag there as well.

## Open Questions

No open questions remain for this proposal.
