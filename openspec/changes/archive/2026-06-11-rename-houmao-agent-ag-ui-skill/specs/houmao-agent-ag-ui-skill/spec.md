## REMOVED Requirements

### Requirement: Houmao packages a `houmao-agent-ag-ui` system skill
**Reason**: The old public skill identity is replaced by `houmao-interop-ag-ui`.

**Migration**: Install, invoke, document, and select `houmao-interop-ag-ui` instead. Treat `houmao-agent-ag-ui` as a retired projection that normal system-skill install and sync flows may remove.

### Requirement: Skill provides a validated authoring workflow
**Reason**: The workflow is preserved under the renamed `houmao-interop-ag-ui` skill capability.

**Migration**: Use the validated authoring workflow in `houmao-interop-ag-ui`.

### Requirement: Skill documents endpoint selection without guessing
**Reason**: Endpoint-selection guidance is preserved under the renamed `houmao-interop-ag-ui` skill capability.

**Migration**: Use the endpoint-selection guidance in `houmao-interop-ag-ui`.

### Requirement: Skill enforces safe GUI payload guidance
**Reason**: GUI payload safety guidance is preserved under the renamed `houmao-interop-ag-ui` skill capability.

**Migration**: Use the GUI payload safety guidance in `houmao-interop-ag-ui`.

### Requirement: Skill explains reconnect-aware publish results
**Reason**: Publish-result interpretation is preserved under the renamed `houmao-interop-ag-ui` skill capability.

**Migration**: Use the publish-result guidance in `houmao-interop-ag-ui`.

### Requirement: Skill prefers agent-addressed GUI targets for Houmao workbench use
**Reason**: Agent-addressed GUI target guidance is preserved under the renamed `houmao-interop-ag-ui` skill capability.

**Migration**: Use the agent-addressed target guidance in `houmao-interop-ag-ui`.

### Requirement: Skill explains active-thread fallback publishing
**Reason**: Active-thread fallback publishing guidance is preserved under the renamed `houmao-interop-ag-ui` skill capability.

**Migration**: Use the active-thread fallback guidance in `houmao-interop-ag-ui`.

### Requirement: Skill explains active GUI selection to users and agents
**Reason**: Active GUI selection guidance is preserved under the renamed `houmao-interop-ag-ui` skill capability.

**Migration**: Use the active GUI selection guidance in `houmao-interop-ag-ui`.
