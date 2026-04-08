# Feature Request: Master Shared-Resource TOML Above Per-Agent Settings

> Obsolete as of 2026-04-08.
> Moved from `context/issues/features/feat-runtime-master-shared-resource-config.md` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Status
Proposed

## Summary
Add one repo-level master TOML configuration for shared runtime resources that sit above per-agent recipe settings, so the runtime can resolve shared infrastructure such as CAO server settings, shared mailbox settings, and similar cross-agent resources from a single authoritative place.

Today, those settings are spread across multiple surfaces:
- per-agent brain recipe mailbox blocks,
- `start-session` CLI overrides such as `--cao-base-url` and `--mailbox-root`,
- CAO server launcher TOML under `config/cao-server-launcher/`,
- mailbox-local operational state inside the mailbox root itself.

That works, but it means shared infrastructure is configured indirectly and inconsistently. A master shared-resource config would let recipes and blueprints reference named shared resources instead of repeating concrete paths, ports, and URLs.

## Why
Current configuration is fragmented in ways that make shared-agent infrastructure harder to reason about:
- mailbox enablement is declared inside a brain recipe, even when the mailbox itself is really a shared group-level resource,
- CAO client connection details are session-start flags, while CAO server launch details live in a different TOML file,
- there is no single declarative source for "the shared mailbox named X" or "the CAO service named Y",
- multiple recipes that should use the same shared resources must repeat or override concrete values separately,
- runtime tooling has to assemble shared-resource behavior from several config layers instead of resolving named resources from one stable schema.

This becomes more noticeable as we add more shared runtime resources:
- shared filesystem mailboxes,
- CAO service definitions,
- common runtime roots or service endpoints,
- possibly future shared stores, coordination services, or resource pools.

A master TOML layer would give the runtime a clearer contract for shared infrastructure while preserving per-agent settings for role/tool/skill-specific behavior.

## Requested Scope
1. Define one master TOML config for shared runtime resources, likely under `config/`, that the runtime can load as the authoritative shared-resource layer.
2. Support named shared resource definitions for at least:
   - CAO server/service settings,
   - shared filesystem mailbox settings,
   - any common runtime-root-related defaults that should not be duplicated per recipe.
3. Allow per-agent recipes or blueprints to reference shared resources by name instead of embedding concrete infrastructure values directly.
4. Define precedence between:
   - master shared-resource config,
   - per-agent recipe or blueprint config,
   - explicit runtime CLI overrides.
5. Keep secrets out of this master config; it should be for shared infrastructure settings, not credential material.
6. Update runtime startup so shared mailbox resolution and CAO connection resolution can consume these named shared-resource definitions.
7. Document the schema, location, and intended ownership of this master config clearly.

## Acceptance Criteria
1. The repo has a documented master TOML schema for shared runtime resources.
2. The runtime can resolve a named shared mailbox definition from that master config and use it to bootstrap or connect a mailbox-enabled session without repeating the mailbox root in every recipe.
3. The runtime can resolve a named CAO service definition from that master config and use it to connect CAO-backed sessions without requiring every caller to restate `--cao-base-url`.
4. Recipes or blueprints can reference shared resources indirectly by stable names.
5. CLI overrides still work and have clearly documented precedence over shared-config defaults.
6. The design clearly separates:
   - shared infrastructure config,
   - per-agent recipe config,
   - local secrets or credential profiles.
7. Docs include at least one end-to-end example showing:
   - a master shared-resource TOML,
   - a recipe referencing shared resources,
   - runtime resolution behavior.

## Non-Goals
- No requirement to move secrets into the master shared-resource config.
- No requirement to eliminate existing CLI overrides.
- No requirement to redesign mailbox-local `rules/` behavior inside shared mailbox roots.
- No requirement to solve principal deregistration or leave-group cleanup in the same change.
- No requirement to force every agent to use shared resources; local or ad hoc overrides may still exist.

## Suggested Follow-Up
- Create an OpenSpec change for shared runtime-resource configuration.
- Decide the exact file location and schema, for example whether it should live at `config/runtime-shared.toml` or a similar path.
- Define how recipes reference shared resources, for example by stable names like `mailbox_ref = "research-group"` or `cao_service_ref = "local-default"`.
- Align CAO launcher config, runtime connection config, and mailbox config around the new shared-resource layer without breaking existing workflows.
