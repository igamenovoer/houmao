## MODIFIED Requirements

### Requirement: Specialist credential-source guidance moves under unified agent definition
The unified `houmao-agent-definition` skill SHALL own the credential-source guidance used when creating easy specialists or when `create-agent-fast-forward` creates a specialist.

The existing credential-source modes SHALL remain available under the unified `specialists` and `create-agent-fast-forward` paths:

1. explicit auth values or files;
2. user-directed environment lookup;
3. user-directed directory scan;
4. tool-specific automatic credential discovery.

Credential-source handling SHALL remain scoped to specialist creation or fast-forward flows that create a specialist. Non-create actions SHALL NOT enter credential discovery.

#### Scenario: Fast-forward specialist creation can use auto credentials
- **WHEN** a user asks the `create-agent-fast-forward` workflow to create a Codex, Claude, or Gemini specialist using auto credentials
- **THEN** the unified skill uses the selected tool's credential lookup guidance
- **AND THEN** it keeps that discovery scoped to the specialist creation portion of the fast-forward workflow

### Requirement: Tool-specific credential references are relocated or re-exported
The unified `houmao-agent-definition` skill SHALL provide or reference the Claude, Codex, and Gemini credential kinds and lookup pages needed by specialist creation and `create-agent-fast-forward`.

If `houmao-specialist-mgr` remains as a compatibility wrapper, the wrapper SHALL route to the unified references instead of maintaining a divergent copy.

#### Scenario: Only selected tool reference is loaded
- **WHEN** a user creates a Claude specialist through the unified skill and the active credential-source mode requires lookup guidance
- **THEN** the skill loads only the Claude credential reference
- **AND THEN** it does not also load Codex or Gemini credential references for that request
