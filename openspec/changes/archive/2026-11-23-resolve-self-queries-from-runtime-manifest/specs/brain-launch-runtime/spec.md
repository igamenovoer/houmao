# Spec Delta

## ADDED Requirements

### Requirement: Session manifests publish effective agent metadata for runtime queries
Managed runtime publication SHALL record the effective agent metadata and observation bindings needed by supported queries in the session manifest. Queries SHALL use those fields for agent metadata. Live observations SHALL use the runtime authorities identified by the manifest.

#### Scenario: Launch publishes query-ready metadata
- **WHEN** Houmao publishes a managed session after launch, join, or relaunch
- **THEN** its manifest supplies the effective identity, mode, backend, native home and surface, execution binding, and applicable observation and control locators
- **AND THEN** publication keeps credentials and raw provider environment values in their private runtime locations

#### Scenario: Runtime observation is unavailable
- **WHEN** a valid session manifest exists and an observation source cannot provide current evidence
- **THEN** the query preserves the manifest-backed agent details and reports the observation as unavailable or unknown according to the command contract

### Requirement: Agent definitions serve launch planning
Houmao SHALL use the agent definition directory for launch and relaunch planning. Existing session inspection and live control SHALL use its verified manifest and committed runtime artifacts.

#### Scenario: Definition changes after launch
- **WHEN** an agent definition changes or becomes inaccessible after its managed session is running
- **THEN** supported runtime queries use the session's published effective metadata
- **AND THEN** supported live control uses the session's already-committed runtime inputs

#### Scenario: An agent is explicitly relaunched
- **WHEN** an authorized relaunch needs to resolve launch inputs from the agent definition
- **THEN** launch planning can access the definition directory and publish the resulting metadata for that runtime generation

## MODIFIED Requirements

### Requirement: Runtime publishes manifest-first stable discovery pointers and live gateway bindings separately
When the runtime makes a tmux-backed session gateway-capable, it SHALL publish `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_ID` into the session environment. These stable discovery pointers SHALL also locate the session for tmux-backed relaunch. The runtime or gateway lifecycle SHALL publish bindings for a running gateway instance separately.

#### Scenario: Session start publishes manifest-first stable discovery pointers
- **WHEN** the runtime starts a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_ID`
- **AND THEN** those bindings identify the session even when no gateway instance is running
- **AND THEN** runtime discovery succeeds with the definition-directory environment variable absent

#### Scenario: Live gateway attach publishes active gateway bindings
- **WHEN** the runtime or lifecycle command attaches a live gateway instance to a gateway-capable tmux-backed session
- **THEN** the tmux session environment contains `HOUMAO_AGENT_GATEWAY_HOST`, `HOUMAO_AGENT_GATEWAY_PORT`, `HOUMAO_GATEWAY_STATE_PATH`, and `HOUMAO_GATEWAY_PROTOCOL_VERSION`
- **AND THEN** those bindings identify the currently running gateway instance

## REMOVED Requirements

### Requirement: Name-addressed tmux-backed session control SHALL recover `agent_def_dir` from session environment
**Reason**: A launched session's effective runtime metadata and control locators belong to its manifest. The definition directory supplies inputs when launching a session.

**Migration**: Use the existing name selector to locate the runtime manifest and resolve the requested live operation from that manifest. Resolve definition inputs during an explicit launch or relaunch.
