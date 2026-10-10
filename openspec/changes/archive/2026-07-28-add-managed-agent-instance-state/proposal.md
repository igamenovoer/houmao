## Why

Reusable definitions need per-instance behavior configuration that survives relaunch without rewriting static skills, prompts, or project definitions. Houmao also needs verified-self state access that works across supported managed runtimes rather than only inside a tmux session.

This change depends on `deploy-predefined-agent-blueprints`.

## What Changes

- Add one canonical instance-state database at `.houmao/memory/agents/<agent-id>/state.sqlite`.
- Store the exact instance-contract digest, typed Agent Runtime Variable revisions, and named Agent Mindset revisions in that database.
- Extend Agent Definition instance contracts with runtime-variable declarations, mindset declarations, and skill-to-mindset bindings.
- Instantiate runtime variables and mindset records through a recoverable managed-launch state machine.
- Render prompt and memo consumers from one launch snapshot. Keep static skills byte-stable and let them query current values.
- Add verified-self identity resolution through a validated runtime manifest and current registry generation for both tmux and headless managed runtimes.
- Preserve operator-targeted mutation and verified-self read-only access. Managed agents cannot mutate their own runtime variables or mindsets in v1.
- Define mindset consumption as an explicit static-skill protocol. Bundle validation and behavior tests enforce the protocol; Houmao does not claim a provider-neutral invocation interceptor.
- Block incompatible deployment updates while live or preserved instances reference the older instance-contract digest.

## Capabilities

### New Capabilities

- `houmao-managed-agent-self-identity`: Defines provider-independent verified-self resolution from runtime authority.
- `houmao-agent-instance-runtime-variables`: Defines declarations, launch snapshots, revisions, operator mutation, verified-self reads, and lifecycle.
- `houmao-agent-mindsets`: Defines named declarations, per-instance records, immutable snapshots, skill bindings, operator revision, and authority limits.

### Modified Capabilities

- `agent-definition-bundles`: Adds runtime-variable and mindset declarations to the instance contract.
- `houmao-mgr-agent-definition-deployments`: Preserves the instance contract and blocks incompatible in-use updates.
- `houmao-admin-entrypoint-skill`: Routes explicit-instance state operations.
- `houmao-agent-entrypoint-skill`: Routes verified-self state reads.
- `houmao-shared-routines-skill`: Exposes actor-scoped state operations through the existing agent-instance routine.

## Impact

The change affects managed launch and relaunch, agent memory storage, runtime identity verification, definition validation, profile propagation, agent-instance CLI commands, system skills, behavior tests, and runtime documentation. Runtime values and mindset records remain instance-owned and never enter the project catalog as mutable state.
