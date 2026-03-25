## MODIFIED Requirements

### Requirement: `houmao-server` exposes a native headless launch and stop API
For Houmao-managed headless agents, `houmao-server` SHALL expose Houmao-owned lifecycle routes that do not depend on CAO session or terminal creation.

At minimum, the native headless lifecycle surface SHALL include:

- `POST /houmao/agents/headless/launches`
- `POST /houmao/agents/{agent_ref}/stop`

`POST /houmao/agents/headless/launches` SHALL accept a resolved runtime launch request for a native headless agent.

In v1, that launch request SHALL require at minimum:

- `tool`
- `working_directory`
- `agent_def_dir`
- `brain_manifest_path`

That request MAY include optional identity and prompt-provenance hints such as:

- `role_name`
- `agent_name`
- `agent_id`

When `role_name` is omitted, `null`, or otherwise intentionally absent, `houmao-server` SHALL treat that launch as a valid brain-only launch and SHALL use an empty system prompt.

The raw HTTP launch contract SHALL NOT rely on pair-style convenience fields such as `provider`, `agent_source`, or installed profile name as its normative launch shape.

Validation failures such as missing required resolved launch fields or conflicting launch-input combinations SHALL return HTTP `422`.

When a headless launch succeeds, `houmao-server` SHALL return the managed-agent identity plus server-owned manifest and session-root pointers for the launched headless agent.

Native headless launch SHALL NOT require or depend on creating a child-CAO session or terminal first.

`POST /houmao/agents/{agent_ref}/stop` SHALL stop a managed headless agent through the Houmao-owned headless lifecycle rather than through CAO terminal-stop semantics.

#### Scenario: Native headless launch creates a managed agent without CAO terminal identity
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` for a Claude headless agent
- **THEN** `houmao-server` launches that headless agent through a Houmao-owned headless path
- **AND THEN** the returned managed-agent identity does not require a CAO `terminal_id`

#### Scenario: Native headless launch accepts resolved runtime inputs with optional role metadata
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` with `tool`, `working_directory`, `agent_def_dir`, and `brain_manifest_path`
- **THEN** `houmao-server` validates that request as a native headless launch request
- **AND THEN** a successful response returns the tracked-agent identity plus manifest and session-root pointers for the launched headless agent

#### Scenario: Brain-only native headless launch uses an empty system prompt
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` without `role_name`
- **THEN** `houmao-server` accepts that launch as a brain-only launch
- **AND THEN** the launched agent uses an empty system prompt instead of failing role validation

#### Scenario: Convenience-only launch shape is rejected with validation semantics
- **WHEN** a caller submits `POST /houmao/agents/headless/launches` using only convenience fields such as `provider` or `agent_source` without the required resolved runtime inputs
- **THEN** `houmao-server` rejects that request with HTTP `422`
- **AND THEN** the raw server launch contract remains native and explicit rather than convenience-shaped

#### Scenario: Native headless stop does not use terminal-stop compatibility routes
- **WHEN** a caller submits `POST /houmao/agents/{agent_ref}/stop` for a managed headless agent
- **THEN** `houmao-server` stops that agent through the Houmao-owned headless lifecycle
- **AND THEN** the caller does not need to treat the headless agent as a fake CAO terminal to stop it
