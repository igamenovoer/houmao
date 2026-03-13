## 1. Packaged Schema Contract

- [ ] 1.1 Add `live_agent_registry_record.v1.schema.json` under `src/houmao/agents/realm_controller/schemas/` to describe the persisted shared-registry `record.json` v1 payload in a form the runtime schema validator can enforce.
- [ ] 1.2 Extend schema-consistency coverage so the packaged registry schema is checked against `LiveAgentRegistryRecordV1` and drift is caught in tests.

## 2. Write-Path Validation

- [ ] 2.1 Validate serialized shared-registry payloads against the packaged registry schema inside `publish_live_agent_record()` before the atomic replace step.
- [ ] 2.2 Ensure schema-validation failures reject both initial publish and later refresh rewrites without partially replacing the existing `record.json`.

## 3. Regression Coverage And Docs

- [ ] 3.1 Add unit coverage for registry-schema discovery and for schema-invalid publish/rewrite attempts failing before partial file replacement.
- [ ] 3.2 Update runtime-facing documentation to note that shared-registry `record.json` now has a packaged standalone schema and is validated during runtime-managed create/update flows.
