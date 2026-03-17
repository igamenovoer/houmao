## ADDED Requirements

### Requirement: Agent reference pages defer the broader Houmao filesystem map to the centralized system-files reference
The runtime-managed agent reference documentation SHALL point readers to the centralized system-files reference when the topic is the broader Houmao-owned filesystem layout rather than agent-specific lifecycle or control behavior.

Agent reference pages SHALL keep the artifact details needed to explain runtime-managed session behavior, but they SHALL NOT act as the only long-form source for the broader Houmao root map, launcher-root relationship, or cross-subsystem storage-preparation guidance.

At minimum, the agent reference SHALL link to the centralized system-files reference when discussing:

- runtime root and session-root placement,
- generated homes and generated manifests,
- workspace-local job directories,
- filesystem-preparation guidance that extends beyond one runtime-managed agent page.

When agent reference pages mention default runtime-managed storage locations, they SHALL use current root terminology and SHALL NOT present legacy temporary example paths as the default runtime root.

#### Scenario: Agent docs link out for the broader root and job-directory model
- **WHEN** a reader uses the runtime-managed agent reference to understand where generated homes, session roots, or workspace-local job directories live
- **THEN** the agent docs provide enough local context to explain the agent behavior
- **AND THEN** they point the reader to the centralized system-files reference for the broader Houmao filesystem model and operator preparation guidance

#### Scenario: Agent docs stay focused on runtime-managed agent behavior
- **WHEN** a reader opens an agent reference page for session targeting, interaction-path behavior, or runtime-owned state responsibilities
- **THEN** that page remains focused on runtime-managed agent behavior
- **AND THEN** it does not need to duplicate the full cross-subsystem filesystem map to stay understandable

#### Scenario: Agent docs do not present legacy example roots as current defaults
- **WHEN** a reader opens an agent-oriented reference page that mentions where generated homes, manifests, or runtime-managed sessions live by default
- **THEN** the page uses current default-root terminology
- **AND THEN** any retained temporary-path examples are clearly examples or explicit override paths rather than implied defaults
