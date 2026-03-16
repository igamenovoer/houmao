## Why

Houmao now has a clearer ownership model for runtime roots, registry records, launcher artifacts, generated homes and manifests, and per-session job directories, but the filesystem story is still spread across subsystem pages. Operators and developers need one reference tree that explains exactly which directories and files Houmao creates, what each artifact is for, which paths are contracts versus implementation details, and how to prepare storage, permissions, or root redirections before running the system.

At the same time, the known issue [`context/issues/known/issue-agent-id-cutover-leftovers.md`](../../../context/issues/known/issue-agent-id-cutover-leftovers.md) shows that the `agent_id` cutover still has live leftovers in registry docs, live OpenSpec main specs, and one packaged schema artifact. Since this change already centralizes filesystem and registry documentation, it is the right place to clean up those remaining contradictory `agent_key` and v1 references too.

## What Changes

- Add a new centralized `docs/reference/system-files/` reference subtree for Houmao-owned and Houmao-generated filesystem artifacts across runtime-managed agents, shared registry, gateway-adjacent session state, and CAO server launcher state.
- Document the root-resolution and ownership model for `~/.houmao/runtime`, `~/.houmao/registry`, workspace-local job directories, and CAO launcher runtime trees, including explicit-overrides versus env-var overrides versus defaults.
- Document the lifecycle, purpose, and contract level of important runtime artifacts such as generated homes, generated manifests, session `manifest.json`, gateway files nested under the session root, `live_agents/<agent-id>/record.json`, and launcher artifacts such as `ownership.json` and `launcher_result.json`.
- Document the CAO launcher `home/` subtree as a Houmao-selected root that CAO itself writes into, while keeping mailbox out of scope for this reference tree.
- Consolidate overlapping filesystem inventories that are currently split across `docs/reference/realm_controller.md`, `docs/reference/agents/contracts/public-interfaces.md`, `docs/reference/agents/internals/state-and-recovery.md`, `docs/reference/gateway/contracts/protocol-and-state.md`, and `docs/reference/cao_server_launcher.md` so those pages can stay focused on behavior, contracts, and workflows.
- Update broader reference pages to link to the centralized system-files docs when they mention runtime-owned files, registry files, gateway-adjacent session files, or CAO launcher artifact trees instead of re-explaining those layouts inline.
- Clean up stale or duplicated filesystem-path guidance in existing reference pages, including legacy `agent key` wording in registry landing docs and outdated default-runtime-root wording in agent-home docs, so the centralized system-files reference becomes the primary operator-facing source for filesystem preparation.
- Update live registry docs and live OpenSpec main specs so they consistently describe the current `agent_id`-keyed, v2 registry model rather than mixing in pre-cutover `agent_key` or `LiveAgentRegistryRecordV1` wording as though it were current behavior.
- Resolve the status of the still-packaged `src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v1.schema.json` artifact by either removing it if it is no longer an intentional shipped contract or explicitly documenting it as historical/non-current so it is not mistaken for the active registry schema.

## Capabilities

### New Capabilities
- `system-files-reference-docs`: Define the structure, coverage, and cross-linking rules for a centralized reference subtree that explains Houmao-owned and Houmao-generated filesystem artifacts across agent runtime, registry, gateway-adjacent session state, and CAO launcher state, excluding mailbox.

### Modified Capabilities
- `agents-reference-docs`: Runtime-managed agent docs will move detailed filesystem-layout discussion to the centralized system-files reference and keep agent pages focused on lifecycle, targeting, and interaction-path behavior.
- `registry-reference-docs`: Shared-registry docs will point to the centralized system-files reference for the broader root-and-layout map while keeping registry-specific contract and ownership semantics in the registry subtree.
- `agent-gateway-reference-docs`: Gateway docs will point to the centralized system-files reference when discussing session-root nesting and durable gateway file locations instead of duplicating the full filesystem map.
- `agent-discovery-registry`: Main registry capability specs will remove the last pre-cutover `agent_key` wording that still appears as if it were part of current canonicalization or lookup behavior.
- `brain-launch-runtime-pydantic-boundaries`: Main schema-packaging specs will describe the current `agent_id`-keyed v2 registry schema and will resolve how historical packaged registry schemas are represented.

## Impact

- Affected docs/specs: `docs/reference/index.md`, `docs/reference/system-files/**`, `docs/reference/realm_controller.md`, `docs/reference/cao_server_launcher.md`, `docs/reference/agents/index.md`, `docs/reference/agents/contracts/public-interfaces.md`, `docs/reference/agents/internals/state-and-recovery.md`, `docs/reference/agents_brains.md`, `docs/reference/registry/index.md`, `docs/reference/registry/contracts/record-and-layout.md`, `docs/reference/registry/internals/runtime-integration.md`, selected `docs/reference/gateway/**` pages, `openspec/specs/registry-reference-docs/spec.md`, `openspec/specs/agent-discovery-registry/spec.md`, and `openspec/specs/brain-launch-runtime-pydantic-boundaries/spec.md`.
- New docs subtree: `docs/reference/system-files/`.
- No runtime behavior or CLI contract changes are intended in this change. The work is primarily documentation/spec coherence, but it may also remove or explicitly classify one non-current packaged registry schema artifact if that file is confirmed not to be part of the active supported contract.
- The change should reduce drift between subsystem pages and improve operator guidance for pre-creating directories, setting permissions, and configuring path redirections.
