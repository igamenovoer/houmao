## 1. CLI Surface And Input Normalization

- [x] 1.1 Add `--force [keep-stale|clean]` parsing and validation to `houmao-mgr agents launch`, with bare `--force` defaulting to `keep-stale`.
- [x] 1.2 Add the same launch-owned force option to `houmao-mgr project easy instance launch` and forward it without persisting into specialist or easy-profile state.
- [x] 1.3 Extend launch request and runtime input models to carry a normalized managed force mode independent of reusable profile config.

## 2. Runtime Takeover Orchestration

- [x] 2.1 Resolve fresh live predecessor ownership by managed identity and fail clearly when a conflict exists without force takeover.
- [x] 2.2 Implement `keep-stale` takeover sequencing that stops the predecessor, reuses the predecessor-managed home, and leaves untouched stale artifacts alone.
- [x] 2.3 Implement `clean` takeover sequencing that stops the predecessor and removes predecessor-owned replaceable runtime artifacts before replacement launch.
- [x] 2.4 Surface explicit post-takeover failure reporting without automatic rollback to the predecessor session.

## 3. Brain Construction And Cleanup Boundaries

- [x] 3.1 Extend brain-home construction to support explicit managed-home policies `keep-stale` and `clean` for targeted managed homes.
- [x] 3.2 Update runtime cleanup and mailbox-support helpers so `clean` removes only predecessor-owned replaceable artifacts while preserving shared mailbox state and operator-owned paths.
- [x] 3.3 Ensure replacement manifests and related runtime metadata are rewritten correctly for reused managed homes under both force modes.

## 4. Validation And Documentation

- [x] 4.1 Add unit tests for CLI parsing, bare-force defaulting, explicit mode selection, invalid values, and non-persistence into launch or easy profiles.
- [x] 4.2 Add runtime and integration tests for no-force conflict failure, identity-targeted takeover, tmux-name non-targeting, `keep-stale`, `clean`, and non-rollback behavior.
- [x] 4.3 Update launch and easy-instance CLI documentation to describe force modes, cleanup boundaries, and operator responsibility for stale artifacts under `keep-stale`.
