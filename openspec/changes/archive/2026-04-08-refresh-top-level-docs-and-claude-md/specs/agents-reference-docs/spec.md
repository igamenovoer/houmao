## REMOVED Requirements

### Requirement: Runtime-managed agent reference documentation is organized under a dedicated subtree

**Reason**: The `docs/reference/agents/` subtree duplicated material already covered by `docs/reference/run-phase/`, `docs/reference/system-files/`, and `docs/reference/cli/` after the April 2026 project-overlay and launch-profile refactors. A dedicated subtree is no longer the right shape for runtime-managed agent reference content.

**Migration**: Read `docs/reference/run-phase/session-lifecycle.md` for lifecycle coverage, `docs/reference/run-phase/backends.md` for backend model coverage, `docs/reference/cli/houmao-mgr.md` for the CLI surface, and `docs/reference/system-files/agents-and-runtime.md` for runtime-owned filesystem layout. Project-aware resolution now lives at `docs/reference/system-files/project-aware-operations.md`.

### Requirement: Runtime-managed agent reference documentation separates contracts, operations, and internals

**Reason**: The contracts/operations/internals split is no longer the organizing axis for runtime-managed agent reference content now that the relevant material is distributed across `run-phase/`, `system-files/`, and `cli/`.

**Migration**: Contracts guidance is covered by `docs/reference/run-phase/backends.md` and `docs/reference/cli/houmao-mgr.md`; operations guidance is covered by `docs/reference/run-phase/session-lifecycle.md`; internals guidance is covered by `docs/reference/system-files/agents-and-runtime.md`.

### Requirement: Runtime-managed agent reference pages combine intuitive explanations with exact technical detail

**Reason**: This quality bar is inherited by the current run-phase, system-files, and CLI reference trees, which already carry first-time-reader framing alongside exact technical detail. It is no longer anchored to the retired `docs/reference/agents/` subtree.

**Migration**: The same quality bar continues to apply to `docs/reference/run-phase/`, `docs/reference/system-files/`, and `docs/reference/cli/` pages under their own capability specs (`docs-run-phase-reference`, `system-files-reference-docs`, `docs-cli-reference`).

### Requirement: Important runtime-managed agent procedures include embedded Mermaid sequence diagrams

**Reason**: The Mermaid-sequence-diagram requirement is inherited by `docs-run-phase-reference` and related specs where procedures are now documented.

**Migration**: Any procedure that previously needed a sequence diagram in `docs/reference/agents/` now belongs in the relevant run-phase or CLI reference page and continues to carry the sequence-diagram expectation under that spec.

### Requirement: Agent contract documentation covers the implemented runtime-managed public surfaces

**Reason**: Public contract coverage for runtime-managed sessions now lives in `docs/reference/run-phase/backends.md`, `docs/reference/run-phase/session-lifecycle.md`, and `docs/reference/cli/houmao-mgr.md`.

**Migration**: Read those pages for session targeting, control surface semantics, session manifest concepts, discovery bindings, and the runtime-versus-gateway boundary.

### Requirement: Agent operational documentation covers session lifecycle and message-passing modes

**Reason**: Session lifecycle, message-passing modes, and raw control-input posture are now owned by `docs/reference/run-phase/session-lifecycle.md`, `docs/reference/cli/agents-gateway.md`, and `docs/reference/cli/agents-mail.md`.

**Migration**: Read those pages for start/resume/stop flows, gateway capability publication, synchronous-versus-queued posture, and the current support boundary for raw control input.

### Requirement: Agent internal documentation explains runtime state management and recovery boundaries

**Reason**: Runtime state persistence, discovery publication, and recovery boundaries are now owned by `docs/reference/system-files/agents-and-runtime.md` and the system-files reference tree.

**Migration**: Read `docs/reference/system-files/index.md` and `docs/reference/system-files/agents-and-runtime.md` for runtime-owned storage layout, manifest persistence rules, and cleanup boundaries.

### Requirement: Runtime-managed agent reference pages identify the source materials they reflect

**Reason**: Source-mapping continues to apply to the successor reference pages under their own specs (`docs-run-phase-reference`, `system-files-reference-docs`, `docs-cli-reference`). It is no longer anchored to the retired `docs/reference/agents/` subtree.

**Migration**: The successor pages carry their own source-mapping expectations under their own specs.

### Requirement: Runtime-managed agent reference pages introduce terminology clearly

**Reason**: Terminology introduction expectations continue to apply to the successor reference pages under their own specs.

**Migration**: The successor pages under `docs/reference/run-phase/`, `docs/reference/system-files/`, and `docs/reference/cli/` introduce the relevant terminology in their own content.

### Requirement: Agent reference pages defer the broader Houmao filesystem map to the centralized system-files reference

**Reason**: There are no agent reference pages left to defer to system-files — the agent subtree is retired and the canonical filesystem map already lives under `docs/reference/system-files/`.

**Migration**: Read `docs/reference/system-files/index.md` and its linked pages directly for the cross-subsystem filesystem inventory and operator preparation guidance.
