# Proposal

## Why

[Issue #81](https://github.com/igamenovoer/houmao/issues/81) requires Houmao to launch and control agents in an existing Linux account, container, or remote host while preserving execution ownership. Current launch preparation and later runtime reconstruction assume the operator's local filesystem, environment, and tmux server.

## What Changes

- Introduce named execution profiles, separate from agent launch profiles and backends, for the current account, passwordless delegation to an existing Linux account, container exec, and SSH execution. Administrators provision users, delegation permissions, target projects, definitions, and credential references outside this change.
- Enter the selected execution context before resolving project assets, credentials, native homes, runtime directories, or launch environment. Reuse maintained Houmao launch and control operations inside that context through a bounded, versioned stdio request contract.
- Persist an observed execution binding separately from logical agent identity. Bind later operations to the same owner, context, authorized controller, and concrete runtime/control handles; reject mismatches and unsupported operations explicitly.
- Keep owner-side manifests authoritative. Store only secret-free routing locators in the operator's registry and distinguish executor-managed agents from external communication-only imports.
- Route lifecycle and supported communication operations through the saved executor. Return context-qualified home and artifact paths; retain refresh's existing guarantee that it never restarts an agent.
- Support multiple agents under one OS user with separate native homes, runtime state, and credential bindings, including distinct private keys. These agents retain that user's shared OS permissions.
- Make tmux server selection explicit throughout owner-side operations. Clear inherited tmux selectors at context entry and restrict teardown to the addressed agent on its recorded server.
- **BREAKING:** Revise strict runtime/registry contracts where needed to record execution ownership and distinguish routing locators from local runtime presence. Unsupported old delegated metadata fails explicitly rather than guessing an owner.

## Capabilities

### New Capabilities

- `agent-execution-contexts`: Execution profiles, owner-context admission, observed bindings, operation transport, credential separation, and execution-bound control.

### Modified Capabilities

- `houmao-mgr-agents-launch`: Select an executor for project-backed birth and prepare the agent entirely within the selected context.
- `agent-discovery-registry`: Preserve execution bindings on owner records and add a separate operator-side executor locator collection without copying runtime state.
- `houmao-mgr-registry-discovery`: Resolve executor-managed targets alongside local lifecycle records, then route control and lifecycle-aware listing through their bound owner.

## Impact

Product changes will affect `src/houmao/srv_ctrl/commands/`, project launch preparation, `realm_controller` runtime/manifest/registry contracts, tmux helpers and discovery, and shared owned-path resolution. Execution adapters will use native subprocess, sudo, container, and OpenSSH facilities; no executor daemon or new remote filesystem framework is planned.

Focused integration coverage will verify real differing UIDs, restricted delegation, same-user agents with different keys, isolated tmux routing, and actual container/SSH handoffs. Passwordless sudo was verified locally on 2026-11-17 for root and `nobody`; temporary test-account provisioning is authorized for verification. Runtime account provisioning, project/asset deployment, cross-context migration, strong isolation between agents sharing a UID, public network authentication (#84), and Pi integration remain outside this change.

CLI/reference documentation will explain configuration, supported operations, transport limits, lost-response recovery, and the distinction between execution ownership and credential identity. Existing communication-only imports retain their lifecycle restrictions.
