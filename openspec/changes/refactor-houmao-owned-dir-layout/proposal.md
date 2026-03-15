## Why

Recent CAO workdir changes removed one of the main reasons Houmao had to keep CAO home, runtime state, and agent workdirs mentally coupled. The current directory model still mixes discovery metadata, durable runtime control state, launcher-owned CAO state, and agent job-local scratch space too loosely, which makes ownership, cleanup, and destructive-edit expectations harder to reason about.

## What Changes

- Introduce an explicit Houmao-owned directory model with separate zones for discovery registry, durable runtime state, per-agent job-dir state, and mailbox state.
- **BREAKING** Add a dedicated default Houmao runtime root under `~/.houmao/runtime/` for durable runtime-managed session manifests, gateway state, and launcher-managed CAO server artifacts instead of defaulting new runtime-owned state to repo-local `tmp/agents-runtime`.
- **BREAKING** Flatten default Houmao-managed build-state paths so generated homes and manifests no longer rely on tool- or family-based directory bucketing.
- **BREAKING** Replace registry-scoped `agent_key` with cross-module `agent_id` as the authoritative system-owned agent identity; canonical agent name remains the strong human-facing label, while `agent_id` becomes the stable per-agent association key that answers whether a specific agent identity is currently up.
- When no explicit or previously persisted `agent_id` exists, bootstrap the initial `agent_id` as `md5(canonical agent name)` and then persist or reuse that `agent_id` for later builds, starts, resumes, publication, and rename-like workflows.
- **BREAKING** Old `agent_key`-keyed registry directories are not migrated or read after the `agent_id` cutover; they become legacy on-disk state that users may remove manually.
- Require Houmao-owned directories that are named after one agent to use `agent_id` rather than canonical agent name as the writable directory key.
- **BREAKING** Decouple tmux session naming from canonical agent name: tmux session names become unique live-session handles, and canonical agent name must be recovered from persisted manifest metadata or shared-registry publication rather than inferred from the tmux session name itself.
- **BREAKING** Persist session identity as first-class manifest metadata: canonical agent name, authoritative `agent_id`, and the actual tmux session name become durable runtime contract fields rather than inferred or backend-state-only details.
- Add env-var override support for Houmao-owned directory locations so CI and dynamic environments can relocate registry, runtime, mailbox, and job-dir defaults without rewriting configs.
- Keep the shared registry under `~/.houmao/registry/` as a small discovery-oriented locator layer rather than using it as the mutable CAO home or runtime state root.
- Define a runtime-managed per-agent job dir under each agent working directory at `<working-directory>/.houmao/jobs/<session-id>/` for logs, outputs, temporary files, and other session-local destructive work.
- Keep `AGENTSYS_LOCAL_JOBS_DIR` as a per-launch or per-agent relocation surface for that session's job dir rather than as a required machine-global configuration.
- **BREAKING** Change launcher-managed CAO artifact paths from `runtime_root/cao-server/<host>-<port>/...` to `runtime_root/cao_servers/<host>-<port>/{launcher,home}/...`, with no old-path compatibility shim.
- **BREAKING** Change the default filesystem mailbox root from a runtime-root-derived path to an independent Houmao mailbox root while preserving explicit mailbox-root overrides.
- Preserve the agent working directory itself as the CLI startup project context and generally agent-editable area, while keeping mailbox storage as an independent shared writable subsystem.
- Update the runtime, launcher, registry, and mailbox contracts so directory defaults, env-var override precedence, publication pointers, and cleanup boundaries all reflect the same ownership model.

## Capabilities

### New Capabilities

- `houmao-owned-dir-layout`: Defines the top-level Houmao directory zones, their default paths, and their ownership or mutability boundaries.

### Modified Capabilities

- `brain-launch-runtime`: Changes the default runtime-owned session-state layout, introduces the per-agent job-dir contract, requires runtime-owned metadata to carry canonical agent name plus authoritative `agent_id` plus the actual tmux session name as first-class manifest fields, and treats tmux session names as persisted live-session handles rather than authoritative agent names.
- `agent-discovery-registry`: Clarifies that the registry stays pointer-oriented and discovery-only rather than becoming the mutable home for runtime or CAO server state, replaces registry-specific `agent_key` with authoritative `agent_id`, keys published live-agent directories by `agent_id`, makes direct liveness resolution by `agent_id` primary, and does not preserve compatibility for old `agent_key`-keyed directories.
- `cao-server-launcher`: Moves launcher-owned CAO artifacts and CAO home defaults into the Houmao runtime root, adopts the `cao_servers/<host>-<port>/{launcher,home}/` layout, treats the old `cao-server/<host>-<port>/` layout as legacy state, and preserves the existing workdir-vs-home separation.
- `agent-mailbox-fs-transport`: Clarifies that the filesystem mailbox root remains an independent shared writable area instead of being implicitly grouped under runtime-owned or workspace-owned state.

## Impact

- Affected code: `src/houmao/agents/brain_builder.py`, `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/manifest.py`, `src/houmao/agents/realm_controller/registry_models.py`, `src/houmao/agents/realm_controller/registry_storage.py`, `src/houmao/agents/mailbox_runtime_support.py`, `src/houmao/cao/server_launcher.py`, and related path-resolution and identity-association helpers.
- Affected docs: runtime state/recovery docs, registry docs, CAO launcher docs, mailbox docs, and CLI guidance that currently describes runtime-root-derived layouts.
- Affected systems: runtime-owned session persistence, shared registry publication and lookup, CAO standalone launcher management, tmux-backed control resolution, session-local logs and scratch outputs, mailbox root resolution defaults, and the name-vs-`agent_id` association model for system-owned writable state.
- Dependencies: builds on the recently clarified CAO workdir contract that allows agent workdirs to live outside CAO home.
