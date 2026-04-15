## REMOVED Requirements

### Requirement: Launch profiles may store optional persist-lane intent
**Reason**: Launch profiles no longer store managed persist-lane intent.

**Migration**: Remove `persist_dir`, `persist_disabled`, and `persist_binding` from profile storage and projection. Memory pages are always resolved from the launched agent id and selected overlay.

### Requirement: Launch-profile persist-lane intent participates in launch precedence
**Reason**: There is no persist-lane precedence after persist binding is removed.

**Migration**: Direct launch and profile launch both use the simplified managed memory default. Use explicit project paths outside launch-profile memory configuration for artifacts or shared data.
