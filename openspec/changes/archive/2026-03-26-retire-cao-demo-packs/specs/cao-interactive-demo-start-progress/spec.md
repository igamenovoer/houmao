## REMOVED Requirements

### Requirement: Interactive demo startup SHALL emit operator-visible progress breadcrumbs
**Reason**: This progress-output contract belongs only to the retired CAO interactive demo pack.
**Migration**: Use the maintained Houmao-server interactive demo for supported startup behavior and operator guidance.

### Requirement: Interactive demo startup SHALL emit periodic waiting feedback during session launch readiness
**Reason**: This waiting-feedback requirement was defined only for the retired CAO interactive demo startup flow.
**Migration**: No direct replacement is required in this retirement change beyond using the maintained Houmao-server interactive workflow.

### Requirement: Interactive demo startup progress SHALL preserve the machine-readable success payload contract
**Reason**: This machine-readable startup payload contract is tied only to the retired CAO interactive demo.
**Migration**: Use the maintained Houmao-server interactive demo's CLI contract instead of the removed CAO demo startup surface.
