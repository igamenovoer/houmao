## Why

The shared-registry `record.json` contract is currently enforced only through Pydantic models even though the repository now documents a fuller v1 record shape, including nested `identity`, `runtime`, and `terminal` groups plus optional `gateway` and `mailbox` metadata. Unlike other runtime-owned JSON artifacts, the repo still ships no standalone packaged schema file for that persisted contract. That makes the registry record harder to inspect, verify, and keep aligned with the repo's existing persisted-artifact boundary rules and the newer registry reference docs.

## What Changes

- Add a standalone packaged JSON Schema file for shared-registry `record.json` v1 under `src/houmao/agents/realm_controller/schemas/`, covering the current nested record shape including optional `gateway` and `mailbox` groups when present.
- Require shared-registry record publication and refresh paths to validate payloads against that standalone schema when creating or rewriting `record.json`.
- Align tests with the repo's existing packaged-schema consistency pattern so validator-enforceable structural drift between the packaged schema and `LiveAgentRegistryRecordV1` is caught early while model-only semantic invariants remain with the Pydantic boundary.
- Update the concrete registry reference pages that already describe the current record shape so they explain the new packaged schema and write-time validation behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime-pydantic-boundaries`: packaged schema and write-time validation requirements expand to cover shared-registry `record.json` alongside existing persisted runtime artifacts.

## Impact

- Affected code: `src/houmao/agents/realm_controller/registry_models.py`, `src/houmao/agents/realm_controller/registry_storage.py`, `src/houmao/agents/realm_controller/schema_validation.py`, packaged schema files under `src/houmao/agents/realm_controller/schemas/`, `tests/unit/agents/realm_controller/test_schema_consistency.py`, and related registry tests.
- Affected systems: shared agent registry publication, refresh, cleanup, and operator/developer inspection of runtime-owned persisted artifacts.
- Affected docs: `docs/reference/registry/contracts/record-and-layout.md` and `docs/reference/registry/internals/runtime-integration.md`.
- Dependencies: no new external dependency is required; the change should reuse the existing packaged-schema loading, validation, and schema-consistency helpers already present in the runtime package.
