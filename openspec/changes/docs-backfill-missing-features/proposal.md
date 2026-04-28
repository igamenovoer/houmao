## Why

Several recent features shipped without corresponding updates to the `docs/` reference tree. Users relying on the published docs cannot discover degraded/stale agent recovery, symlink safety hardening, or registry durability improvements that are already in the CLI and API. This change backfills those gaps so the docs stay authoritative.

## What Changes

- Add a dedicated docs page for **degraded and stale active tmux-backed managed agent recovery** — covering `probe_tmux_backed_authority()`, the recovery paths for `agents stop` and `agents relaunch`, and the `agents cleanup session --purge-registry` janitor flag.
- Update **session-lifecycle reference** to mention degraded/stale recovery as a first-class lifecycle path alongside normal stop, resume, and relaunch.
- Update **registry discovery-and-cleanup reference** to cover the lifecycle-aware registry behavior introduced for relaunchable agents and the `--purge-registry` flag semantics.
- Update **managed-agent API reference** to reflect the `stale_active_recovery_seconds` attach parameter and the degraded-context notifier policy.
- Update **getting-started overview** and **docs index** cross-references to point at the new material.

## Capabilities

### New Capabilities
- `docs-degraded-stale-recovery`: Reference documentation for probe-first dispatch and recovery of broken active tmux-backed managed agents.

### Modified Capabilities
- `docs-run-phase-reference`: Add degraded/stale recovery to the session-lifecycle narrative and Mermaid diagrams.
- `docs-cli-reference`: Surface `agents cleanup session --purge-registry` and `agents relaunch` recovery behavior in the CLI command descriptions.
- `docs-subsystem-reference`: Update registry and gateway notifier docs to reference recovery-time trust posture and stale-record handling.

## Impact

- `docs/reference/run-phase/session-lifecycle.md`
- `docs/reference/registry/operations/discovery-and-cleanup.md`
- `docs/reference/managed_agent_api.md`
- `docs/reference/cli/houmao-mgr.md` (selective updates, not a full rewrite)
- `docs/getting-started/overview.md`
- `docs/index.md`
- No source code or API changes.
