## 1. Create the centralized system-files reference subtree

- [x] 1.1 Add `docs/reference/system-files/index.md` and update `docs/reference/index.md` so the new system-files subtree is top-level discoverable.
- [x] 1.2 Write the system-files roots and ownership page covering default roots, override precedence, ownership categories, and the explicit mailbox-out-of-scope boundary.
- [x] 1.3 Write the runtime-managed agent and session files page covering generated homes, generated manifests, session roots, `manifest.json`, nested gateway files, and workspace-local job directories.
- [x] 1.4 Write the CAO launcher system-files page covering `cao_servers/<host>-<port>/launcher/`, the derived `home/` subtree, launcher artifacts, and the distinction between Houmao-owned and CAO-owned contents.
- [x] 1.5 Write the shared-registry system-files page covering `live_agents/<agent-id>/record.json`, registry root placement, and the registry’s pointer-oriented boundary.
- [x] 1.6 Write the operator filesystem-preparation page covering pre-created directories, writable paths, relocation/redirection surfaces, ignore-rule guidance, and cleanup expectations.

## 2. Simplify broad runtime and agent docs that currently duplicate filesystem inventory

- [x] 2.1 Update `docs/reference/realm_controller.md` so it keeps CLI and lifecycle guidance but replaces the full session-root, gateway-file, and `job_dir` inventory with links to the centralized system-files reference.
- [x] 2.2 Update `docs/reference/agents/contracts/public-interfaces.md` so it keeps command-surface intent and representative output but stops presenting the canonical runtime-owned artifact tree inline.
- [x] 2.3 Update `docs/reference/agents/internals/state-and-recovery.md` so it keeps recovery and authority boundaries while deferring the canonical storage inventory to the centralized system-files reference.
- [x] 2.4 Update `docs/reference/agents/index.md` and `docs/reference/agents_brains.md` so they link to the centralized system-files reference for generated-home and runtime-root placement and no longer present stale default-root wording as current guidance.

## 3. Simplify launcher, registry, and gateway docs that currently overlap the filesystem map

- [x] 3.1 Update `docs/reference/cao_server_launcher.md` so it keeps launcher CLI, proxy, and health semantics while moving launcher-tree, derived-`home/`, and general filesystem-preparation guidance into the centralized system-files reference.
- [x] 3.2 Update `docs/reference/registry/index.md`, `docs/reference/registry/contracts/record-and-layout.md`, and `docs/reference/registry/internals/runtime-integration.md` so the landing page becomes a mental-model navigator, the runtime-integration page uses current `LiveAgentRegistryRecordV2` and shipped-schema wording, and legacy `agent key` terminology is replaced with current `agent_id` terminology wherever the docs are describing the live contract.
- [x] 3.3 Update the relevant `docs/reference/gateway/` pages, especially `docs/reference/gateway/contracts/protocol-and-state.md`, so they keep gateway-specific artifact semantics but defer the broader runtime-root and session-root filesystem map to the centralized system-files reference.

## 4. Align live OpenSpec main specs and packaged schema artifacts with the implemented `agent_id` cutover

- [x] 4.1 Update `openspec/specs/registry-reference-docs/spec.md` so the main spec no longer defines `agent key` or v1 registry semantics as the current reference-doc contract.
- [x] 4.2 Update `openspec/specs/brain-launch-runtime-pydantic-boundaries/spec.md` so the packaged shared-registry schema requirements describe the current `agent_id`-keyed v2 contract and clearly handle any retained historical registry schema artifacts.
- [x] 4.3 Update `openspec/specs/agent-discovery-registry/spec.md` to remove the last surviving “derive `agent_key`” wording from the current canonicalization flow.
- [x] 4.4 Resolve the status of `src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v1.schema.json`: remove it if unused, or explicitly classify it as historical/non-current in the surrounding docs/specs if it must stay packaged.

## 5. Sanity-check consistency and scope

- [x] 5.1 Review the new and updated pages for consistent ownership vocabulary, artifact contract-strength labeling, and source-reference coverage.
- [x] 5.2 Verify that mailbox filesystem details remain outside the new subtree and that system-files pages point readers to the mailbox reference instead of duplicating mailbox layout documentation.
- [x] 5.3 Do a consistency pass across `docs/reference/`, `openspec/specs/`, and the packaged registry schemas so live non-historical references no longer give contradictory answers about `agent_key` versus `agent_id` or v1 versus v2 registry contracts.
