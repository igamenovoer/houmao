## ADDED Requirements

### Requirement: Gateway reference pages link to the centralized system-files reference when discussing broader session-root storage
The agent gateway reference documentation SHALL keep gateway-specific contracts, queue semantics, and lifecycle behavior in the gateway subtree while pointing readers to the centralized system-files reference for the broader Houmao filesystem map.

Gateway pages SHALL continue to document gateway-specific artifacts such as `attach.json`, `state.json`, queue state, and event logs, but they SHALL defer the broader relationship between those files and the surrounding runtime-managed session root to the centralized system-files reference when that broader filesystem map is the main topic.

At minimum, the gateway reference SHALL link to the centralized system-files reference when discussing:

- how gateway files are nested under runtime-managed session roots,
- how gateway artifact paths relate to other Houmao-owned root families,
- filesystem-preparation guidance that extends beyond gateway-specific behavior.

#### Scenario: Gateway docs explain local gateway artifacts and link out for the broader runtime tree
- **WHEN** a reader opens the gateway reference to understand attach metadata, state files, or queue artifacts
- **THEN** the gateway docs explain those gateway-specific files directly
- **AND THEN** they point to the centralized system-files reference for the broader runtime-root and session-root filesystem map

#### Scenario: Gateway docs stay focused on gateway behavior instead of duplicating the full filesystem reference
- **WHEN** a maintainer uses the gateway reference to understand queueing, attachability, or recovery behavior
- **THEN** the gateway docs remain focused on gateway semantics
- **AND THEN** they do not need to duplicate the full Houmao-owned filesystem model to explain those gateway behaviors
