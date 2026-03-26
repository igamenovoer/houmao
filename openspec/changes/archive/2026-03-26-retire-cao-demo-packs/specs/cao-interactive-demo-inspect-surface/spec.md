## REMOVED Requirements

### Requirement: Interactive demo inspect JSON SHALL expose a stable top-level contract
**Reason**: This inspect JSON contract belongs only to the retired CAO interactive demo pack.
**Migration**: Use the maintained Houmao-server interactive demo's inspect surface for supported interactive inspection guidance.

### Requirement: Interactive demo inspect SHALL present an operator-oriented session summary
**Reason**: This human-readable inspect surface is specific to the retired CAO interactive demo.
**Migration**: Use the maintained Houmao-server interactive demo's inspect commands instead of the removed CAO demo inspect flow.

### Requirement: Interactive demo inspect SHALL surface live tool state when available
**Reason**: This live tool-state surface is part of the retired CAO interactive demo's inspect contract.
**Migration**: Use the maintained Houmao-server interactive demo's inspect and state surfaces for supported live-session observation.

### Requirement: Interactive demo inspect SHALL optionally include a best-effort projected output-text tail
**Reason**: The best-effort output-tail contract exists only for the retired CAO interactive demo inspect command.
**Migration**: No direct replacement is required in this retirement change beyond using the maintained Houmao-server interactive demo for active operator walkthroughs.

### Requirement: Interactive demo inspect SHALL resolve terminal-log paths from the effective CAO home
**Reason**: This terminal-log-path rule applies only to the retired interactive CAO demo's CAO-home layout.
**Migration**: Use the maintained Houmao-server interactive demo's log and artifact paths instead of the removed CAO demo path contract.

### Requirement: Interactive demo verification artifacts SHALL preserve the resolved inspect contract
**Reason**: This verification contract belongs only to the retired CAO interactive demo pack.
**Migration**: Use the maintained Houmao-server interactive demo verification flow for supported interactive verification.
