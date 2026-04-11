## REMOVED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-loop-relay` system skill
**Reason**: The relay-only packaged skill is replaced by the generic loop graph planner, `houmao-agent-loop-generic`.

**Migration**: Rename the asset directory, skill metadata, catalog key, and docs/spec references to `houmao-agent-loop-generic`; do not keep `houmao-agent-loop-relay` as a current installable alias.

#### Scenario: Relay skill name is retired
- **WHEN** a maintainer inspects the current packaged system-skill catalog after this change
- **THEN** `houmao-agent-loop-relay` is not listed as a current installable skill
- **AND THEN** `houmao-agent-loop-generic` is listed as the replacement loop graph planner

### Requirement: The authoring lane formulates user intent into an explicit relay loop plan
**Reason**: Relay-only authoring is too narrow for the new loop-planning layer, which must decompose user intent into pairwise and relay components.

**Migration**: Use `houmao-agent-loop-generic` authoring guidance to create typed generic loop plans. A pure relay request migrates to a generic plan with one `relay` component.

#### Scenario: Pure relay plans migrate to generic components
- **WHEN** a user asks for a relay-only plan after this change
- **THEN** the generic planner may produce a plan with one `relay` component
- **AND THEN** the plan is still owned by `houmao-agent-loop-generic` rather than `houmao-agent-loop-relay`

### Requirement: The authored plan includes a Mermaid relay graph that distinguishes routing from supervision
**Reason**: Relay-only graph rendering no longer covers mixed pairwise/relay communication graphs.

**Migration**: Use `houmao-agent-loop-generic` graph rendering, which distinguishes typed pairwise components, relay components, component dependencies, result-return paths, supervision, completion, and stop.

#### Scenario: Relay graph rendering migrates to typed generic graph rendering
- **WHEN** a mixed pairwise/relay plan needs a rendered graph
- **THEN** `houmao-agent-loop-generic` renders typed components and result-return paths
- **AND THEN** the graph is not constrained to relay handoff lanes only

### Requirement: The operating lane treats the user agent as outside the loop and places liveness on the master or origin
**Reason**: The operating lane is retained but generalized under `houmao-agent-loop-generic` so one root owner can supervise typed pairwise and relay components.

**Migration**: Use `houmao-agent-loop-generic` `start`, `status`, and `stop` guidance. Relay-only runs migrate to generic plans with a relay component and the same root-owner control-plane boundary.

#### Scenario: Relay run control migrates to generic run control
- **WHEN** a user asks to start, inspect, or stop a formerly relay-only run shape
- **THEN** the request routes through `houmao-agent-loop-generic` operating guidance
- **AND THEN** the user agent remains outside the execution loop after the root owner accepts the run
