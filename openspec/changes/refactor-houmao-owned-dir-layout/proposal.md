## Why

Recent CAO workdir changes removed one of the main reasons Houmao had to keep CAO home, runtime state, and agent workdirs mentally coupled. The current directory model still mixes discovery metadata, durable runtime control state, launcher-owned CAO state, and agent job-local scratch space too loosely, which makes ownership, cleanup, and destructive-edit expectations harder to reason about.

## What Changes

- Introduce an explicit Houmao-owned directory model with separate zones for discovery registry, durable runtime state, per-agent job-dir state, and mailbox state.
- **BREAKING** Add a dedicated default Houmao runtime root under `~/.houmao/runtime/` for durable runtime-managed session manifests, gateway state, and launcher-managed CAO server artifacts instead of defaulting new runtime-owned state to repo-local `tmp/agents-runtime`.
- **BREAKING** Flatten default Houmao-managed build-state paths so generated homes and manifests no longer rely on tool- or family-based directory bucketing.
- Introduce a two-layer agent association model for Houmao-owned state: canonical agent name remains the strong human-facing live identity, while each agent also carries an authoritative `agent_id` used for globally unique association; by default, `agent_id` is derived as `md5(canonical agent name)`.
- Require Houmao-owned directories that are named after one agent to use `agent_id` rather than canonical agent name as the writable directory key.
- Keep the shared registry under `~/.houmao/registry/` as a small discovery-oriented locator layer rather than using it as the mutable CAO home or runtime state root.
- Define a runtime-managed per-agent job dir under each agent working directory at `<working-directory>/.houmao/jobs/<session-id>/` for logs, outputs, temporary files, and other session-local destructive work.
- **BREAKING** Change the default filesystem mailbox root from a runtime-root-derived path to an independent Houmao mailbox root while preserving explicit mailbox-root overrides.
- Preserve the agent working directory itself as the CLI startup project context and generally agent-editable area, while keeping mailbox storage as an independent shared writable subsystem.
- Update the runtime, launcher, registry, and mailbox contracts so directory defaults, publication pointers, and cleanup boundaries all reflect the same ownership model.

## Capabilities

### New Capabilities

- `houmao-owned-dir-layout`: Defines the top-level Houmao directory zones, their default paths, and their ownership or mutability boundaries.

### Modified Capabilities

- `brain-launch-runtime`: Changes the default runtime-owned session-state layout, introduces the per-agent job-dir contract, and requires runtime-owned metadata to carry canonical agent name plus authoritative `agent_id`.
- `agent-discovery-registry`: Clarifies that the registry stays pointer-oriented and discovery-only rather than becoming the mutable home for runtime or CAO server state, and keys published live-agent directories by authoritative `agent_id` rather than canonical agent name.
- `cao-server-launcher`: Moves launcher-owned CAO artifacts and CAO home defaults into the Houmao runtime root while preserving the existing workdir-vs-home separation.
- `agent-mailbox-fs-transport`: Clarifies that the filesystem mailbox root remains an independent shared writable area instead of being implicitly grouped under runtime-owned or workspace-owned state.

## Impact

- Affected code: `src/houmao/agents/brain_builder.py`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/manifest.py`, `src/houmao/agents/realm_controller/registry_storage.py`, `src/houmao/agents/mailbox_runtime_support.py`, `src/houmao/cao/server_launcher.py`, and related path-resolution and identity-association helpers.
- Affected docs: runtime state/recovery docs, registry docs, CAO launcher docs, mailbox docs, and CLI guidance that currently describes runtime-root-derived layouts.
- Affected systems: runtime-owned session persistence, shared registry publication, CAO standalone launcher management, session-local logs and scratch outputs, mailbox root resolution defaults, and the name-vs-`agent_id` association model for system-owned writable state.
- Dependencies: builds on the recently clarified CAO workdir contract that allows agent workdirs to live outside CAO home.
