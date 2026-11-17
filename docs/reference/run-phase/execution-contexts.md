# Agent Execution Contexts

Execution profiles select where Houmao prepares and controls an agent. They are independent of agent launch profiles and native backends. A project launch profile selects the agent's source and birth defaults; an execution profile selects an existing account, host, or container and the trusted route into it.

## Ownership and Credentials

Administrators create users, install Houmao and native agent tools, provision target project assets and credential references, and grant passwordless delegation. Houmao uses those prerequisites without creating production accounts, starting replacement containers, copying project trees, or asking for another user's password.

The execution binding records the observed owner UID/GID, host/context identity, owner-side state roots, admitted controller scope, and route fingerprint separately from the logical agent ID. Existing agents retain that binding when launch profiles or execution-profile files change. A target-changing edit fails with a context mismatch rather than migrating the agent.

Multiple agents can share one execution profile and OS account. Their IDs, native homes, runtime directories, and selected credentials remain separate, including distinct supported private-key references. Those agents still share the account's OS permissions. Separate directories prevent accidental credential replacement; they do not provide confidentiality against another process with the same UID.

Operator transport authentication is separate from agent authentication. An SSH transport key remains operator-local, and Houmao disables agent forwarding. Agent credentials come from target-side selected references. Operator sudo state, transport authentication sockets, and container-control sockets do not enter the harness environment.

## Trusted Profile Configuration

Named profiles live under the operator's platformdirs Houmao config root in `executors/<name>.yaml`. The ordinary Linux path is `~/.config/houmao/executors/<name>.yaml`. Houmao does not discover execution commands in project overlays, native homes, skills, or agent definitions. Configuration directories and files must be owned by the operator or root and must not be writable by groups or other users; symlinked profile files and collections are rejected.

This model-valid example selects an existing Linux account. Replace the paths and expected UID/GID with the target's provisioned values:

```yaml
schema_version: 1
name: worker-alice
transport: sudo
account: alice
entrypoint: /usr/local/bin/houmao-mgr
policy_path: /etc/houmao/executors/alice.yaml
project_root: /srv/alice/project
expected_uid: 1001
expected_gid: 1001
timeout_seconds: 30.0
environment:
  PATH: /usr/local/bin:/usr/bin:/bin
```

The entrypoint and policy paths belong to the target context. Authentication reference paths such as SSH `identity_file` and `known_hosts_file` belong to the operator context. The profile stores no passwords, raw private keys, inline provider tokens, or shell command fragments. Closed transport fields reject unknown transports and arbitrary argv hooks.

| Transport | Additional Profile Fields | Required External Setup |
| --- | --- | --- |
| `local` | None | Current account, installed helper and owner policy |
| `sudo` | Selected `account` | Existing Linux account and administrator-approved non-interactive delegation |
| `ssh` | `ssh_host`, `known_hosts_file`; optional `ssh_port` and `identity_file` | Trusted host key, batch authentication, target helper/policy and project |
| `docker` | Immutable full 64-character `container_id`; `account` may be `UID:GID` | Existing running container with the helper/project and authorized Docker exec |

Profile environment records are explicit non-secret target settings. Identity variables, loader/Python injection variables, delegation state, and credential-looking inline settings are rejected. Bare-name launch environment references resolve in the authorized target environment. Explicit launch values travel as structured data. The operator's ambient runtime roots, provider credentials, HOME, TMUX, and TMUX_PANE are not copied into delegated launches.

## Owner Admission

The fixed owner entrypoint is:

```text
houmao-mgr internals executor serve-stdio --policy /etc/houmao/executors/alice.yaml
```

The target policy fixes the observed UID/GID, admitted controller and operation scope, project authority, runtime/registry roots, and tmux socket. OS authorization grants access to this entrypoint. A controller name supplied in JSON or a registry entry does not grant authority.

A restricted sudo deployment can authorize the installed command with the exact fixed arguments for designated RunAs accounts. The executable, imported package code, interpreter configuration, and target policy must be trusted and protected from operator modification. Pointing a sudoers rule at an editable development checkout does not create restricted delegation. Test-account setup is separate fixture tooling; it is not a runtime provisioning API.

The owner policy is a separate, explicitly provisioned YAML or JSON file. This example corresponds to the `worker-alice` operator profile above:

```yaml
schema_version: 1
profile:
  schema_version: 1
  name: worker-alice
  transport: sudo
  account: alice
  entrypoint: /usr/local/bin/houmao-mgr
  policy_path: /etc/houmao/executors/alice.yaml
  project_root: /srv/alice/project
  expected_uid: 1001
  expected_gid: 1001
  timeout_seconds: 30.0
  environment:
    PATH: /usr/local/bin:/usr/bin:/bin
controller:
  controller_id: houmao-operator
  authority: sudo_policy
  operations: [describe, launch, state, inspect, capture, resume, prompt, interrupt, stop, relaunch, home, status, refresh_check, refresh]
  project_roots: [/srv/alice/project]
uid: 1001
gid: 1001
registry_root: /home/alice/.config/houmao/registry
runtime_root: /home/alice/.config/houmao/runtime
tmux_socket: /home/alice/.config/houmao/runtime/execution/tmux.sock
```

Choose UID/GID from the existing account. The helper checks effective UID/GID, account, host identity, controller operation scope, and project scope before dispatch. `project_roots` restricts explicit project and workdir selectors, including resolved symlinks and paths relative to the target project. Policy files must be regular root/owner-owned files without group/other write permissions. Symlinked policy files or ancestors are rejected. A controller label in a request cannot substitute for OS delegation.

For a pre-existing operator group and account, an administrator can grant precisely the fixed installed command and policy:

```text
%houmao-operators ALL=(alice) NOPASSWD: /usr/local/bin/houmao-mgr internals executor serve-stdio --policy /etc/houmao/executors/alice.yaml
```

The administrator validates the rule with `visudo -cf <rule-file>` before installation. This grant permits the helper's bounded policy-controlled requests; it does not grant arbitrary manager arguments, arbitrary Python/shell commands, other policy files, or root RunAs. The operator needs no unrestricted sudo grant or target-user password. SSH/container deployments use the corresponding provisioned OS authority and matching controller authority kind.

The private owner helper constructs HOME, USER, and LOGNAME from the actual account record. It uses explicit owner roots and approved non-secret environment settings, without copying ambient provider credentials, SSH-agent sockets, sudo metadata, or inherited tmux selectors. Context discovery is read-only: an uninitialized context returns `initialized: false` and actual UID/GID without creating directories. The first admitted mutation publishes a context UUID atomically. Later requests validate saved ownership and context rather than repairing missing or conflicting authority.

The maintained client sends its expected route fingerprint before first birth as well as later controls. The owner compares that expectation with its provisioned profile before initializing state. The fingerprint detects configuration drift; it is not an authentication credential. Its authority fields must agree between operator and owner configuration. Transport authentication-file references and timeout changes do not change that route fingerprint.

## Launch and Later Controls

```text
houmao-mgr project agents launch --profile reviewer --executor worker-alice
houmao-mgr agents single --agent-id <id> state
houmao-mgr agents single --agent-id <id> home
houmao-mgr agents single --agent-id <id> refresh --check
houmao-mgr agents single --agent-id <id> refresh
houmao-mgr agents single --agent-id <id> relaunch
```

The owner resolves the project, selected source, working directory, credentials, home, and runtime artifacts before birth. The profile's project root supplies the target project when no explicit project directory is given. Explicit project/workdir selectors are target-context paths; caller-side existence is not required. Missing target assets fail without using caller-local substitutes.

Later commands resolve the operator's saved execution locator and re-enter the captured owner route. They do not open foreign manifests locally or reinterpret an owner-loopback gateway port on the operator host. Owner inspection reports current lifecycle and generation before mutation admission; a changed generation causes a conflict. An unavailable, revoked, or incompatible route reports an error without local or default-server fallback.

Home/status inspection stays read-only and returns context-qualified paths. Native refresh retains its existing contract: it never restarts an agent or regenerates launch-profile-derived prompt/configuration materials. Restarts use relaunch. See [native agent home refresh](native-refresh.md) for native-tool behavior.

## Locators and Recovery

The operator registry stores `executor_agents/<agent_id>/record.json` separately from owner-local `live_agents/` and communication-only `external_agents/`. Locators contain identity, profile reference, and the captured execution binding, without copied manifests, queues, credentials, or caller-local control endpoints. The owner's manifest and lifecycle record remain authoritative.

An exact ID selects one known logical identity. Friendly names must be unique across managed owner contexts, and a tmux session name alone cannot select a foreign owner. Communication-only imports retain their lifecycle restrictions even when an execution profile shares a name or address. Explicit `--port` retains the existing pair-authority bypass; it grants no execution rights.

Local stale-presence cleanup does not infer foreign liveness from a missing caller-local tmux session. Lifecycle-inclusive listing can report a known target as unavailable or unverified, without claiming it is stopped.

If owner launch succeeds but operator publication fails, the result reports partial success with the admitted identity. Recover the locator explicitly rather than repeating birth:

```text
houmao-mgr admin executors reconcile --executor worker-alice --agent-id <id>
houmao-mgr admin executors forget --agent-id <id>
```

Reconciliation verifies the admitted owner binding before publication. Forget removes only the lexical operator locator; it does not stop the owner-side agent or delete runtime files.

## Finite Protocol and Failure Semantics

Each transport sends one versioned JSON request over stdin and receives one correlated JSON response on stdout. Request data never becomes a shell command or unrestricted manager argv. Protocol limits are 1 MiB per request, 8 MiB per response, JSON nesting depth 32, and a configurable transport deadline of at most 120 seconds. Native stderr is separately bounded and never copied into public transport errors.

| Result | Meaning | Follow-up |
| --- | --- | --- |
| `completed`, `admitted: true` | The owner returned the correlated operation result | Use the returned owner state |
| `rejected`, `admitted: false` | The request did not enter runtime mutation | Correct the reported prerequisite or admission error |
| `indeterminate`, `admitted: null` or `true` | The result was lost or incomplete after mutation may have begun | Inspect the owner before a deliberate follow-up |

Timeout, disconnection, oversized output, and uncorrelated responses do not establish that an owner operation stopped or rolled back. Houmao never automatically replays a mutation, relaunches a second agent to repair publication, or retries against a local namesake. Correlation and target information support explicit reconciliation.

Initial transport operations are finite launch, describe/state, inspect/capture, resume, prompt, interrupt, stop, relaunch, home/status, refresh check/refresh, and supported finite gateway/cleanup operations. Backend capability still applies. Interactive terminal attach, unbounded watch/event streaming, unsupported container runtimes, nested multi-hop execution, automatic asset deployment, and cross-context migration return explicit unsupported outcomes.

## Tmux Authority

Owner-side launch, reconstruction, gateway access, discovery, and teardown use a saved concrete tmux socket and exact agent handles. Delegated entry clears both inherited TMUX and TMUX_PANE. Current-account/join workflows capture their selected socket explicitly rather than guessing from a session name. Stop and cleanup affect only the selected agent; they never kill or restart the shared localhost tmux server or an unrelated session.

Tests use unique isolated sockets and fixture-owned sessions. `TMUX_TMPDIR` alone is insufficient because inherited TMUX/TMUX_PANE can still select an enclosing server. Never use a libtmux server context manager for a user-owned server: exiting that context can destroy the server.

## Verification Status

Contract, profile-trust, bounded protocol, native argv, helper-pipe timeout/output limits, and locator storage tests run in `tests/unit/execution/`. Tests include target retargeting rejection, immutable container selectors, path/context separation, name ambiguity, local identity conflicts, symlink-safe locator removal, and failed atomic publication.

These component tests do not qualify an end-to-end backend or transport. Real multi-user, SSH, and native-agent evidence must identify the configured fixture, case/model, and result. Docker transport implementation is included; live Docker qualification is deferred by the user and must remain identified as deferred rather than represented as a passing run. No public HTTP listener gains delegation authority through this feature.

On 2026-11-17, the opt-in fixture-boundary suite passed five real OS tests covering distinct operator/owner UIDs, restricted sudo denials, owner HOME/file modes, independent explicit tmux sockets, pinned SSH host trust, and exact-resource teardown. Two further product-stdio tests passed using the actual `execute_request` client as the temporary restricted operator over sudo and a fixture-owned SSH daemon. They confirmed fresh-context read-only description, actual owner UID/GID, operation denial, first-request route-drift rejection, and absence of runtime/registry initialization.

Reproduce those owner-admission checks with an explicitly selected installed entrypoint:

```bash
HOUMAO_EXECUTION_INTEGRATION=1 HOUMAO_EXECUTION_ENTRYPOINT=/absolute/path/to/houmao-mgr pixi run python -m pytest tests/integration/execution/test_fixture_boundaries.py tests/integration/execution/test_owner_stdio.py -q
```

The tests create temporary accounts, a validated temporary sudoers rule, isolated tmux servers, and an independent loopback SSH daemon. Their keys and state remain outside the checkout; cleanup preserves the shared localhost tmux and SSH servers. See [execution fixture instructions](../../../tests/integration/execution/README.md) for resource ownership and setup details. These seven checks qualify owner admission and the real transports' read-only path.

The native owner suite also passed both DSH execution cases on 2026-11-17: ACP through restricted sudo and Web through the fixture-owned SSH daemon, using DSH `0.2.2-rc.3`. Each case prepares the maintained agent fixture as the target owner with explicit `cloud-api`, model `controlled`, context window `8192`, maximum output tokens `128`, reasoning disabled, and an external synthetic credential file targeting a controlled local Messages endpoint. It does not contact a production model provider.

Both native cases launch two agents under the same owner/profile with separate homes and distinct generated Ed25519 private-key references. The existing adapter auth-file projection selects each agent's key. Digest checks confirm that refreshing, stopping, and relaunching the first agent preserve both key selections, the sibling's generation, and the sibling's session. The tests verify actual owner UID/GID and manifest ownership, target-only project access, model prompting, home/state, refresh, interrupt, stop, relaunch, and state reconstruction. A same-name session on the operator's separate server remains available.

Reproduce native qualification with explicit installed executables:

```bash
HOUMAO_EXECUTION_INTEGRATION=1 HOUMAO_EXECUTION_ENTRYPOINT=/absolute/path/to/houmao-mgr HOUMAO_DSH_EXECUTABLE=/absolute/path/to/qualified-dsh pixi run --as-is python -m pytest tests/integration/execution/test_native_owner.py -q
```

The final native run used the standard maintained stdio helper without diagnostic instrumentation and passed `2` cases in `123.73` seconds. Fixture setup provisions copies of installed Node/Bun executables into its private external test installation when those executables live beneath the operator's private home. It leaves the original home permissions and global installations unchanged. Per-agent key material remains selection and overwrite isolation, with the shared-UID permission limit described above.

A focused secondary Codex check also passed using native Codex `0.162.1`: `test_codex_owner.py::test_actual_codex_headless_owner_routing` completed one case in `20.25` seconds. It selects the maintained self-hosted fixture, model `controlled`, unattended headless mode, external synthetic credentials, and a local Responses SSE server. The check covers actual sudo-owner launch, qualified CODEX_HOME, manifest UID/GID, model input, successful turn state, and stop. It does not qualify Codex MCP hot refresh, SSH execution, or container execution.
