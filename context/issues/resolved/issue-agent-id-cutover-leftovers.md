# Issue: `agent_id` Cutover Still Has Live `agent_key` Leftovers In Docs, Specs, And One Packaged Schema Artifact

## Status
Resolved on 2026-03-17.

## Resolution Summary
The live registry docs and specs are now aligned to the `agent_id` and v2 schema contract, and the obsolete packaged v1 registry schema artifact is no longer shipped in this repository.

## Summary

The repository has already cut the live runtime and registry implementation over from registry-scoped `agent_key` to authoritative `agent_id`, but a small set of live documentation/spec artifacts still describe the old `agent_key` model as current behavior.

The leftovers are concentrated in:

- live reference docs under `docs/reference/registry/`,
- live OpenSpec main specs under `openspec/specs/`,
- one still-packaged `live_agent_registry_record.v1.schema.json` artifact that no longer appears to be used by runtime code or schema-consistency tests.

This is mostly a documentation/coherence issue rather than an active runtime bug, but it creates avoidable confusion about which identity surface is current, whether the registry contract is still v1, and whether `agent_key` remains part of the supported implementation.

## Current Implemented Direction

The current live implementation and main docs already indicate the new model:

- registry records and directory layout are keyed by authoritative `agent_id`,
- packaged registry schema validation uses `live_agent_registry_record.v2.schema.json`,
- strict runtime typing uses `LiveAgentRegistryRecordV2`,
- cleanup/result payloads already speak in `removed_agent_ids`, `preserved_agent_ids`, and `failed_agent_ids`.

Representative sources:

- `src/houmao/agents/realm_controller/registry_models.py`
- `src/houmao/agents/realm_controller/registry_storage.py`
- `src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v2.schema.json`
- `tests/unit/agents/realm_controller/test_schema_consistency.py`
- `docs/reference/registry/contracts/record-and-layout.md`

## Live Leftovers Found

### 1. Registry reference index still defines `agent key` as the active directory key

`docs/reference/registry/index.md` still says:

- `agent key`: the SHA-256 hex digest of the canonical agent name, used as the live-agent directory name.

That no longer matches the documented contract pages in the same subtree, which now describe `agent_id` as the on-disk directory key.

The same page also still says a standalone packaged JSON Schema is only a follow-up change, but the repo now ships and uses `live_agent_registry_record.v2.schema.json`.

Affected source:

- `docs/reference/registry/index.md`

### 2. Registry runtime-integration doc still names the old typed model

The Mermaid publication flow in `docs/reference/registry/internals/runtime-integration.md` still says the runtime builds `LiveAgentRegistryRecordV1`.

The live implementation builds and validates `LiveAgentRegistryRecordV2`.

Affected source:

- `docs/reference/registry/internals/runtime-integration.md`

### 3. OpenSpec `registry-reference-docs` main spec still requires old `agent_key` / v1 semantics

`openspec/specs/registry-reference-docs/spec.md` still normatively requires:

- `live_agents/<agent-key>/record.json`,
- SHA-256 `agent_key` derivation,
- strict v1 record fields,
- “agent key” as a term that docs must define.

Those requirements no longer reflect the current main implementation direction or the rest of the live registry docs.

Affected source:

- `openspec/specs/registry-reference-docs/spec.md`

### 4. OpenSpec Pydantic-boundaries spec still describes the registry schema as current v1 under `<agent-key>`

`openspec/specs/brain-launch-runtime-pydantic-boundaries/spec.md` still describes:

- the “current v1” shared-registry payload,
- storage under `live_agents/<agent-key>/record.json`,
- `LiveAgentRegistryRecordV1` as the authoritative typed boundary.

The live code instead uses `LiveAgentRegistryRecordV2` and the packaged `v2` schema.

Affected source:

- `openspec/specs/brain-launch-runtime-pydantic-boundaries/spec.md`

### 5. OpenSpec registry spec has one surviving `derive agent_key` sentence inside an otherwise `agent_id`-based spec

`openspec/specs/agent-discovery-registry/spec.md` is mostly aligned with the `agent_id` cutover, but one scenario still says canonicalized input proceeds “before deriving `agent_key`”.

That line looks like a simple leftover from the pre-cutover wording.

Affected source:

- `openspec/specs/agent-discovery-registry/spec.md`

### 6. Packaged `live_agent_registry_record.v1.schema.json` still exists and still exposes `agent_key`

The file `src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v1.schema.json` is still present with:

- top-level `agent_key`,
- title `LiveAgentRegistryRecordV1`.

Current runtime code appears to validate against `live_agent_registry_record.v2.schema.json`, and schema-consistency tests only assert alignment for the v2 registry schema. That makes the v1 file look like a leftover packaged artifact rather than an actively exercised contract.

This file may still be intentionally kept as a historical or transitional artifact, but if so that intent is not obvious from current live docs.

Affected source:

- `src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v1.schema.json`

## Intentional Historical References That Should Probably Stay

Many archived OpenSpec changes and historical review logs still mention `agent_key`. Those do not look like cleanup targets because they document prior decisions and should remain stable as historical context.

Examples include:

- `openspec/changes/archive/**`
- `context/logs/**`

Similarly, current docs that mention old `agent_key` directories only as legacy manual-cleanup state still appear intentional and aligned with the cutover. Example:

- `docs/reference/registry/contracts/record-and-layout.md`

## Impact

- New readers can get contradictory answers about whether registry identity is keyed by `agent_key` or `agent_id`.
- OpenSpec main specs can mislead future changes or reviews by restating pre-cutover registry semantics as if they were still current.
- The presence of a still-packaged v1 registry schema with `agent_key` can imply a supported compatibility contract even though current codepaths and tests are centered on v2.

## Suggested Cleanup Scope

- Update live registry reference docs so the glossary, scope notes, and diagrams consistently describe `agent_id` and the shipped v2 schema.
- Update live OpenSpec main specs so they no longer restate `agent_key` / v1 registry semantics as the active contract.
- Decide whether `live_agent_registry_record.v1.schema.json` is intentionally retained:
  - if yes, document that it is historical or compatibility-only;
  - if no, remove it in a follow-up cleanup.

## Resolution Status

Open as of 2026-03-16.
