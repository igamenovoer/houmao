## MODIFIED Requirements

### Requirement: Headless Claude/Gemini/Codex sessions are tmux-backed and inspectable
The runtime SHALL publish `HOUMAO_MANIFEST_PATH=<absolute manifest path>` into the tmux session environment so that name-based `--agent-identity` resolution can locate the persisted session manifest.

#### Scenario: Started headless tmux session publishes the HOUMAO manifest pointer
- **WHEN** the runtime starts a tmux-backed headless session
- **THEN** the tmux session environment contains `HOUMAO_MANIFEST_PATH` pointing at the persisted session manifest JSON

### Requirement: Deprecated standalone build and start entrypoints use config-first `.houmao` agent-definition resolution
Deprecated standalone build/start entrypoints SHALL resolve agent-definition roots with this precedence:
1. explicit CLI `--agent-def-dir`
2. `HOUMAO_AGENT_DEF_DIR`
3. nearest ancestor `.houmao/houmao-config.toml`
4. default `<cwd>/.houmao/agents`

#### Scenario: Env-var override wins for deprecated standalone build/start entrypoints
- **WHEN** `HOUMAO_AGENT_DEF_DIR=/tmp/agents`
- **AND WHEN** no explicit CLI `--agent-def-dir` is supplied
- **THEN** the effective agent-definition root is `/tmp/agents`

### Requirement: Filesystem mailbox startup can target either the shared-root mailbox path or an explicit private mailbox directory
When no explicit filesystem mailbox content root override is supplied and `HOUMAO_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the runtime SHALL derive the effective Houmao mailbox root from that env-var override before persisting or resolving filesystem mailbox state for that session.

#### Scenario: Mailbox env override relocates the shared-root mailbox path
- **WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a filesystem-backed mailbox session has no more specific explicit mailbox-root override
- **THEN** the runtime resolves the effective shared mailbox root from `/tmp/houmao-mailbox`

### Requirement: Runtime defaults new build and session state to the Houmao runtime root
When no explicit runtime-root override is supplied and `HOUMAO_GLOBAL_RUNTIME_DIR` is set to an absolute directory path, the runtime SHALL use that env-var value as the effective runtime root instead of the built-in default.

#### Scenario: Runtime-root env-var override relocates the effective runtime root
- **WHEN** `HOUMAO_GLOBAL_RUNTIME_DIR` is set to `/tmp/houmao-runtime`
- **AND WHEN** no explicit runtime-root override is supplied
- **THEN** the effective Houmao runtime root is `/tmp/houmao-runtime`

### Requirement: Runtime materializes canonical agent name and authoritative `agent_id` for system-owned association
Runtime-owned session start SHALL materialize canonical agent names in `HOUMAO-<name>` form and SHALL derive the initial authoritative `agent_id` from that canonical name when no explicit or previously persisted `agent_id` exists.

The initial authoritative id SHALL be the full lowercase `md5("HOUMAO-<name>").hexdigest()` value.

#### Scenario: Runtime bootstraps agent identity from the HOUMAO canonical name
- **WHEN** a developer starts a runtime-owned session with canonical agent name `HOUMAO-gpu`
- **THEN** the runtime materializes the full lowercase `md5("HOUMAO-gpu").hexdigest()` value as the session's initial authoritative `agent_id`

### Requirement: Runtime creates and reuses a per-agent job dir for each started session
When no explicit job-dir override is supplied and `HOUMAO_LOCAL_JOBS_DIR` is set to an absolute directory path for that launch or started agent, the runtime SHALL derive the effective per-agent job dir as `<HOUMAO_LOCAL_JOBS_DIR>/<session-id>/`.

The runtime SHALL create that directory before the session needs runtime-managed scratch space and SHALL expose its absolute path to the launched session through `HOUMAO_JOB_DIR`.

#### Scenario: Job-dir env override publishes the HOUMAO job-dir pointer
- **WHEN** `HOUMAO_LOCAL_JOBS_DIR` is set to `/tmp/houmao-jobs`
- **AND WHEN** the runtime starts a session whose generated session id is `session-20260314-120000Z-abcd1234`
- **THEN** the effective job dir is `/tmp/houmao-jobs/session-20260314-120000Z-abcd1234/`
- **AND THEN** the started session environment includes `HOUMAO_JOB_DIR` pointing to that absolute path

### Requirement: Parsing mode changes do not alter AGENTSYS identity/addressing contracts
Changing runtime parsing mode SHALL NOT redefine the active Houmao identity or addressing contracts. Parsing-mode differences do not rename canonical agent identities, mailbox addressing, or tmux-published discovery pointers away from the `HOUMAO-*` / `HOUMAO_*` family selected by this change.

#### Scenario: Parsing mode change preserves the HOUMAO namespace contract
- **WHEN** the runtime starts two equivalent sessions that differ only in parsing mode
- **THEN** both sessions persist canonical `HOUMAO-...` identity metadata
- **AND THEN** both sessions publish `HOUMAO_MANIFEST_PATH` and related `HOUMAO_*` discovery variables rather than reverting to `AGENTSYS_*`

### Requirement: Name-addressed tmux-backed session control SHALL recover `agent_def_dir` from session environment
Name-addressed tmux-backed control SHALL prefer the tmux-published `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_DEF_DIR` values when they are present and valid.

#### Scenario: Name-addressed control recovers the agent-definition root from HOUMAO tmux env
- **WHEN** tmux session `HOUMAO-chris` exists
- **AND WHEN** that tmux session publishes valid `HOUMAO_MANIFEST_PATH` and `HOUMAO_AGENT_DEF_DIR` values
- **THEN** name-addressed tmux-backed session control resolves the manifest and effective agent-definition root from those `HOUMAO_*` values

### Requirement: Runtime-launched agent subprocess env injects loopback `NO_PROXY` by default
For supported loopback compatibility base URLs, the runtime SHALL bypass ambient proxy environment variables by default by ensuring loopback entries exist in `NO_PROXY` and `no_proxy`.

When `HOUMAO_PRESERVE_NO_PROXY_ENV=1`, the runtime SHALL NOT modify `NO_PROXY` or `no_proxy` and will respect caller-provided values.

#### Scenario: Preserve mode does not modify loopback no-proxy entries
- **WHEN** the runtime launches against a supported loopback compatibility base URL
- **AND WHEN** caller environment includes `HOUMAO_PRESERVE_NO_PROXY_ENV=1`
- **THEN** the runtime does not inject or modify `NO_PROXY` or `no_proxy`

### Requirement: Runtime mail send and reply commands require full recipient addresses and explicit body inputs
Runtime mail send and reply commands SHALL require full mailbox addresses in the active Houmao namespace rather than loose agent-name shortcuts.

#### Scenario: Runtime mail send accepts full HOUMAO mailbox addresses
- **WHEN** a developer invokes `mail send` for a resumed mailbox-enabled session with `--to HOUMAO-bob@agents.localhost` and `--body-content`
- **THEN** the command accepts that address as a valid full recipient address

