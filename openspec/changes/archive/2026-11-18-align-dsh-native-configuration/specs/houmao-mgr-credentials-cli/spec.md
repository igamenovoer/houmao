# houmao-mgr-credentials-cli Specification

## MODIFIED Requirements

### Requirement: Project credentials are selected through the project command group
Project-backed credential management SHALL be exposed through:

```text
houmao-mgr project [--project-dir <dir>] credentials <tool> list|get|add|set|rename|remove|login
```

`project credentials` SHALL use the selected project overlay supplied by the `project` command group. It SHALL NOT expose `--project`, `--agent-def-dir`, or direct native-agent root selectors.

At minimum, the project credential family SHALL expose Houmao-owned tool lanes for:

- `claude`
- `codex`
- `gemini`
- `dsh`

#### Scenario: Explicit project directory selects project credentials
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project --project-dir /repo credentials claude list`
- **THEN** the command manages credentials in `/repo/.houmao`
- **AND THEN** it does not require a top-level `credentials --project` wrapper

#### Scenario: Project credentials reject direct native target options
- **WHEN** an operator runs `houmao-mgr project credentials codex list --agent-def-dir /tmp/agents`
- **THEN** the command fails as an unsupported option
- **AND THEN** the diagnostic does not imply that project credentials can directly target native-agent roots

#### Scenario: Project credentials expose the DSH lane
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project --project-dir /repo credentials dsh list`
- **THEN** the command lists DSH credentials stored in `/repo/.houmao` without requiring direct native-agent root flags

## ADDED Requirements

### Requirement: DSH credential commands persist endpoint and API-key roles

DSH `add|set` SHALL accept `--adapter`, `--api-key`, `--base-url`, `--api-key-env`, and `--base-url-env`. The bundle SHALL store distinct endpoint and API-key environment names as roles beside `vars.env`. `set` and its `--clear-api-key` or `--clear-base-url` options SHALL use the saved names when name flags are omitted. `get` SHALL redact the API-key value by role.

#### Scenario: Endpoint-only pi-ai bundle stores the endpoint role
- **WHEN** an operator runs `houmao-mgr project credentials dsh add --name local-sglang --adapter pi-ai --base-url http://127.0.0.1:14888/v1`
- **THEN** the bundle records `OPENAI_BASE_URL` as its endpoint role and stores the URL in `vars.env`
- **AND THEN** the bundle contains no API-key value or launcher placeholder

#### Scenario: Custom API-key name is redacted by role
- **WHEN** an operator runs `houmao-mgr project credentials dsh add --name custom-local --adapter pi-ai --base-url http://127.0.0.1:14888/v1 --base-url-env SGLANG_BASE_URL --api-key synthetic-value --api-key-env SGLANG_AUTH`
- **AND WHEN** the operator inspects the credential with `houmao-mgr project credentials dsh get --name custom-local`
- **THEN** the stored credential names `SGLANG_BASE_URL` as the endpoint and `SGLANG_AUTH` as the API key
- **AND THEN** `get` reports the API-key name and presence with the value redacted and preserves non-secret endpoint metadata

#### Scenario: Updates and clearing use the recorded roles
- **WHEN** a DSH bundle has custom names and an operator updates the endpoint value or clears the API key without repeating its environment name
- **THEN** the command updates or clears the value for the corresponding stored role
- **AND THEN** the bundle preserves its other entries

#### Scenario: Reserved runtime environment variable names are rejected
- **WHEN** an operator passes a reserved runtime or process name, a non-POSIX identifier, or the same name for both roles
- **THEN** the credential command fails before writing credential state and names the rejected variable
