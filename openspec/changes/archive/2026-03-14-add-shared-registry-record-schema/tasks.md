## 1. Packaged Schema Contract

- [x] 1.1 Add `live_agent_registry_record.v1.schema.json` under `src/houmao/agents/realm_controller/schemas/` to describe the current persisted shared-registry `record.json` v1 payload, including nested `identity`, `runtime`, and `terminal` groups plus optional `gateway` and `mailbox` groups, in a form the runtime schema validator can enforce.
- [x] 1.2 Extend `tests/unit/agents/realm_controller/test_schema_consistency.py` so the packaged registry schema is checked against the validator-enforceable structural subset of `LiveAgentRegistryRecordV1`, while model-only semantic invariants remain covered by registry-model and registry-storage tests.

## 2. Write-Path Validation

- [x] 2.1 Validate serialized shared-registry payloads against the packaged registry schema inside `publish_live_agent_record()` before the atomic replace step.
- [x] 2.2 Ensure schema-validation failures reject both initial publish and later refresh rewrites without partially replacing the existing `record.json`.

## 3. Regression Coverage And Docs

- [x] 3.1 Add unit coverage for registry-schema discovery, structural alignment of the optional `gateway` and `mailbox` groups, and schema-invalid publish/rewrite attempts failing before partial file replacement.
- [x] 3.2 Update `docs/reference/registry/contracts/record-and-layout.md` and `docs/reference/registry/internals/runtime-integration.md` to note that shared-registry `record.json` now has a packaged standalone schema and is validated during runtime-managed create/update flows.
