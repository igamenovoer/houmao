## Why

The shared-registry `record.json` contract is currently defined only through Pydantic models, so the repo ships no standalone schema file for that persisted artifact even though other runtime-owned JSON contracts already have packaged schemas. That makes the registry record harder to inspect, verify, and keep aligned with the repo's existing persisted-artifact boundary rules.

## What Changes

- Add a standalone packaged JSON Schema file for shared-registry `record.json` v1 under `src/houmao/agents/realm_controller/schemas/`.
- Require shared-registry record publication and refresh paths to validate payloads against that standalone schema when creating or rewriting `record.json`.
- Align tests and documentation so the registry record joins the same schema-packaged persisted-artifact contract already used for other runtime-owned JSON files.
- Clarify that registry record schema validation applies to runtime-managed creation and modification flows, not just ad hoc model parsing during load.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime-pydantic-boundaries`: packaged schema and write-time validation requirements expand to cover shared-registry `record.json` alongside existing persisted runtime artifacts.

## Impact

- Affected code: `src/houmao/agents/realm_controller/registry_models.py`, `src/houmao/agents/realm_controller/registry_storage.py`, `src/houmao/agents/realm_controller/schema_validation.py`, packaged schema files under `src/houmao/agents/realm_controller/schemas/`, and related tests/docs.
- Affected systems: shared agent registry publication, refresh, cleanup, and operator/developer inspection of runtime-owned persisted artifacts.
- Dependencies: no new external dependency is required; the change should reuse the existing packaged-schema loading and validation helpers already present in the runtime package.
