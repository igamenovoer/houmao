# Session Lifecycle

Module: `src/houmao/agents/realm_controller/runtime.py` — High-level session runtime orchestration.

The session lifecycle covers starting, interacting with, resuming, and stopping agent sessions. The `RuntimeSessionController` is the main controller class that manages this lifecycle, backed by persisted session manifests that enable resume across process restarts.

## RuntimeSessionController

`RuntimeSessionController` is the primary entry point for managing a live agent session. It is constructed via one of two class-level factory functions: `start_runtime_session` (for new sessions) or `resume_runtime_session` (for previously persisted sessions).

### Starting a new session

```python
@classmethod
def start_runtime_session(
    *,
    agent_def_dir: Path,
    brain_manifest_path: Path,
    role_name: str | None,
    runtime_root: Path | None = None,
    backend: BackendKind | None = None,
    working_directory: Path | None = None,
    api_base_url: str = "http://localhost:9889",
    cao_profile_store_dir: Path | None = None,
    agent_identity: str | None = None,
    agent_name: str | None = None,
    agent_id: str | None = None,
    cao_parsing_mode: CaoParsingMode | None = None,
    mailbox_transport: str | None = None,
    mailbox_root: Path | None = None,
    mailbox_principal_id: str | None = None,
    mailbox_address: str | None = None,
    mailbox_stalwart_base_url: str | None = None,
    mailbox_stalwart_jmap_url: str | None = None,
    mailbox_stalwart_management_url: str | None = None,
    mailbox_stalwart_login_identity: str | None = None,
    blueprint_gateway_defaults: BlueprintGatewayDefaults | None = None,
    gateway_auto_attach: bool = False,
    gateway_host: str | None = None,
    gateway_port: int | None = None,
    tmux_session_name: str | None = None,
    registry_launch_authority: RegistryLaunchAuthorityV1 = "runtime",
) -> RuntimeSessionController
```

Starts a new runtime session by:

1. Loading the brain manifest from `brain_manifest_path`.
2. Resolving the role package from `role_name` within the agent definition directory (or using a brain-only placeholder when `role_name` is `None`).
3. Building a `LaunchPlan` via `build_launch_plan` (see [Launch Plan](launch-plan.md)).
4. Dispatching the launch plan to the chosen backend.
5. Persisting a session manifest to the session root for later resume.

**Parameters:**

| Parameter | Description |
|---|---|
| `agent_def_dir` | Path to the agent definition directory containing roles, brains, and blueprints |
| `brain_manifest_path` | Path to the built brain manifest (JSON) from the build phase |
| `role_name` | Name of the role to apply (resolved from `roles/<role_name>/system-prompt.md`); `None` for brain-only sessions |
| `runtime_root` | Optional runtime root override; defaults to the standard resolved root |
| `backend` | Target backend (see [Backends](backends.md)); resolved from manifest if omitted |
| `working_directory` | Working directory for the agent process |
| `api_base_url` | Base URL for `houmao_server_rest` or `cao_rest` backends |
| `agent_identity` | Legacy agent identity string for session addressing |
| `agent_name` | Friendly managed-agent name |
| `agent_id` | Authoritative managed-agent identifier |
| `mailbox_transport` | Mailbox transport type for inter-agent messaging |
| `mailbox_root` | Filesystem mailbox root path |
| `mailbox_principal_id` / `mailbox_address` | Mailbox identity overrides |
| `mailbox_stalwart_*` | Stalwart JMAP connection parameters |
| `blueprint_gateway_defaults` | Gateway defaults from the resolved blueprint |
| `gateway_auto_attach` | Whether to automatically attach a gateway at launch time |
| `gateway_host` / `gateway_port` | Host and port overrides for gateway attachment (require `gateway_auto_attach`) |
| `tmux_session_name` | Explicit tmux session name override |
| `registry_launch_authority` | Authority identifier for agent registry registration (default: `"runtime"`) |

### Resuming a session

```python
@classmethod
def resume_runtime_session(
    agent_def_dir: Path,
    session_manifest_path: Path,
) -> RuntimeSessionController
```

Resumes a previously started session from its persisted session manifest. The manifest contains all information needed to reconnect to the live agent process (or restart it if needed), including the original launch plan, backend state, and session identifiers.

**Parameters:**

| Parameter | Description |
|---|---|
| `agent_def_dir` | Path to the agent definition directory |
| `session_manifest_path` | Path to the persisted session manifest written during `start_runtime_session` |

### Session manifest persistence

Each session writes a manifest to its session root (`<runtime-root>/sessions/<backend>/<session-id>/`) upon creation. This manifest captures:

- The original launch plan and backend configuration.
- Session identifiers (tmux session name, backend-specific session IDs).
- Gateway state and attachment information.
- Runtime artifacts and metadata.

The session root serves as the persistent root for all session-related state, including the session manifest, gateway state files, and any runtime artifacts produced during the session. The session root is distinct from the brain runtime home (which holds projected configs and skills) and from any workspace-local job directory.

## InteractiveSession protocol

All backends expose a common `InteractiveSession` protocol for interacting with a running agent. The `RuntimeSessionController` delegates to this protocol for prompt delivery and session control.

### send_prompt

```python
def send_prompt(prompt: str) -> list[SessionEvent]
```

Sends a user prompt to the running agent session and returns a list of `SessionEvent` objects representing the agent's response and any side effects. This is the primary interaction method for delivering work to an agent.

### interrupt

```python
def interrupt() -> SessionControlResult
```

Interrupts the agent's current operation. The specific behavior depends on the backend — headless backends may send a SIGINT to the underlying process, while interactive backends may send a Ctrl-C sequence via tmux.

### terminate

```python
def terminate() -> SessionControlResult
```

Terminates the agent session. This stops the underlying agent process and cleans up backend-specific resources. The session manifest remains on disk for inspection but the session cannot be resumed after termination.

### close

```python
def close() -> None
```

Releases resources held by the session controller without necessarily terminating the underlying agent process. Use this when detaching from a session that should continue running.

## Lifecycle flow

```mermaid
flowchart TD
    A[build-brain] -->|BrainManifest| B[start_runtime_session]
    B --> C[build_launch_plan]
    C --> D[Backend dispatch]
    D --> E[Live session]
    E --> F{Interact}
    F -->|send_prompt| E
    F -->|interrupt| E
    F -->|terminate| G[Session ended]
    F -->|close| H[Detached]
    B --> I[Session manifest persisted]
    I -->|resume_runtime_session| E
```

## Start session sequence

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CLI as CLI
    participant RT as Runtime
    participant LP as LaunchPlan
    participant BE as Backend
    participant TM as tmux
    participant CTL as Controller
    participant MF as Manifest
    participant GW as Gateway

    Op->>CLI: start-session<br/>(manifest, role, backend)
    CLI->>RT: start_runtime_session()
    RT->>LP: build_launch_plan(request)
    LP-->>RT: LaunchPlan
    RT->>BE: create session
    BE->>TM: create/join tmux<br/>session + window
    TM-->>BE: pane handle
    BE-->>RT: InteractiveSession
    RT->>CTL: RuntimeSessionController<br/>(session, plan)
    CTL->>MF: persist_manifest()
    CTL->>GW: ensure_gateway_capability()
    CTL-->>Op: ready
```

## Resume session sequence

```mermaid
sequenceDiagram
    participant Op as Operator
    participant CLI as CLI
    participant RT as Runtime
    participant MF as Manifest
    participant LP as LaunchPlan
    participant BE as Backend
    participant TM as tmux
    participant CTL as Controller
    participant GW as Gateway

    Op->>CLI: resume(manifest_path)
    CLI->>RT: resume_runtime_session()
    RT->>MF: load_session_manifest()
    MF-->>RT: payload (V3/V4)
    RT->>LP: build_launch_plan<br/>(intent=resume_control)
    LP-->>RT: LaunchPlan
    RT->>BE: create session<br/>with resume_state
    BE->>TM: reattach existing session
    TM-->>BE: restored pane
    BE-->>RT: InteractiveSession<br/>(restored state)
    RT->>CTL: RuntimeSessionController
    CTL->>GW: ensure_gateway_capability()
    CTL-->>Op: ready
```

## See also

- [Launch Plan](launch-plan.md) — how launch plans are composed from brain manifests and roles
- [Backends](backends.md) — backend implementations that execute launch plans
- [Role Injection](role-injection.md) — how role prompts are delivered to agents
