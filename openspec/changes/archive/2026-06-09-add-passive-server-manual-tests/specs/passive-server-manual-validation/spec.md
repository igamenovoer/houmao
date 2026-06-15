## ADDED Requirements

### Requirement: Manual lifecycle validation script
Houmao SHALL provide a manual passive-server lifecycle validation script under `tests/manual/` that starts `houmao-passive-server serve` as a subprocess on a free local port with isolated Houmao roots.

The script SHALL verify the real HTTP service identity and current-instance metadata, including `GET /health`, `GET /houmao/server/current-instance`, and an empty `GET /houmao/agents` response before any records are seeded. The script SHALL request graceful shutdown through `POST /houmao/server/shutdown` or otherwise terminate the subprocess cleanly during cleanup.

#### Scenario: Passive server starts and reports health
- **WHEN** an operator runs the lifecycle manual script from the repository
- **THEN** the script starts a passive-server subprocess, waits for `/health`, verifies the service identifies as `houmao-passive-server`, verifies current-instance metadata, and exits with a PASS marker after cleanup

### Requirement: Manual registry discovery validation script
Houmao SHALL provide a manual passive-server registry discovery validation script under `tests/manual/` that uses isolated Houmao roots, at least one real tmux session, and strict managed-agent registry records.

The script SHALL publish at least one fresh active registry record whose tmux session exists and at least one record that must not be listed because its session is absent or stale. The script SHALL query `GET /houmao/agents` and `GET /houmao/agents/{agent_ref}` to verify list, resolve-by-id, resolve-by-name, and not-found behavior using the passive server's real HTTP surface.

#### Scenario: Discovery lists only live registry-backed agents
- **WHEN** an operator runs the registry discovery manual script from the repository on a host with tmux
- **THEN** the script verifies that the passive server lists the fresh tmux-live agent with GUI-relevant fields and excludes stale or dead registry records

### Requirement: Manual gateway proxy validation script
Houmao SHALL provide a manual passive-server gateway proxy validation script under `tests/manual/` that uses an isolated registry record with live gateway coordinates and a fake local gateway implementing the route shapes under test.

The script SHALL verify that passive-server discovery reports `has_gateway` for the seeded agent. The script SHALL verify that `GET /houmao/agents/{agent_ref}/gateway` proxies the fake gateway status response and that `POST /houmao/agents/{agent_ref}/gateway/requests` forwards a `submit_prompt` payload to the fake gateway.

#### Scenario: Passive server resolves discovered gateway target
- **WHEN** an operator runs the gateway proxy manual script from the repository
- **THEN** the script verifies passive-server discovery marks the seeded agent as gateway-backed and confirms the gateway status and request-submission routes are forwarded through the passive server

### Requirement: Manual scripts isolate state and clean up owned resources
Each passive-server manual validation script SHALL isolate Houmao runtime, registry, mailbox, and job roots from the developer's ambient Houmao state. Each script SHALL clean up subprocesses, fake servers, temporary directories, and tmux sessions that it creates.

#### Scenario: Manual validation avoids ambient Houmao state
- **WHEN** a passive-server manual validation script runs
- **THEN** it sets isolated child-process roots and does not require or mutate the operator's active global Houmao registry, runtime, mailbox, or job directories
