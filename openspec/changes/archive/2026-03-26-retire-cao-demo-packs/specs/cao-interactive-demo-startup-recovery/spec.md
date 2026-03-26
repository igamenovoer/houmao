## REMOVED Requirements

### Requirement: Interactive demo defaults SHALL be repository-root anchored
**Reason**: This requirement only existed to constrain startup behavior for the retired CAO interactive demo pack.
**Migration**: No direct replacement is required for the removed CAO demo. Maintained interactive guidance now lives under the Houmao-server interactive demo workflow.

### Requirement: Interactive demo default startup SHALL provision a per-run trusted home and git worktree
**Reason**: This startup-layout contract applied only to the retired CAO interactive demo pack.
**Migration**: Use the maintained Houmao-server interactive demo's run-root contract instead of the removed CAO demo layout.

### Requirement: Interactive demo startup SHALL force-replace the verified local loopback CAO server during agent recreation
**Reason**: This requirement exists only because the retired demo owned a fixed standalone CAO server on one loopback port.
**Migration**: Use the maintained Houmao-server interactive demo, which provisions a demo-owned `houmao-server` authority rather than replacing a fixed standalone CAO server.

### Requirement: Verified fixed-loopback CAO replacement SHALL continue across known launcher configs
**Reason**: The known-config replacement behavior is specific to the retired CAO demo's launcher-recovery path.
**Migration**: No replacement is needed because the maintained Houmao-server interactive demo does not depend on this standalone-launcher recovery contract.

### Requirement: Interactive demo wrapper scripts SHALL accept a consistent `-y` contract
**Reason**: The wrapper flag contract applies only to the retired interactive CAO demo scripts.
**Migration**: No direct replacement is required for the removed wrappers.

### Requirement: Interactive demo startup SHALL reset canonical tutorial state to a fresh-run baseline
**Reason**: This fresh-run reset behavior exists only for the retired CAO interactive tutorial flow.
**Migration**: Use the maintained Houmao-server interactive demo's own startup and cleanup flow instead of the removed CAO tutorial state-reset contract.
