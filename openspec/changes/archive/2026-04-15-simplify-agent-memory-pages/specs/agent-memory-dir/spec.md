## REMOVED Requirements

### Requirement: Managed sessions support optional persistent memory through the persist lane
**Reason**: Managed-agent memory is no longer optional persistent storage and no longer supports auto/exact/disabled persist-lane binding.

**Migration**: Each managed agent receives an always-created memo-pages memory root. Operators that need shared durable artifacts SHALL use the launched workdir or explicit project paths outside the managed-agent memory subsystem.

### Requirement: Managed persist binding is discoverable through runtime-backed inspection
**Reason**: There is no managed persist binding to inspect after the memo-pages simplification.

**Migration**: Runtime-backed inspection SHALL report `memory_root`, `memo_file`, and `pages_dir`.
