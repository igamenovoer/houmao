## Context

`add-central-agent-registry` introduced a persisted shared-registry `record.json` contract under `~/.houmao/registry/live_agents/<agent-key>/record.json`. The implementation already defines that payload with strict Pydantic models in `registry_models.py` and validates records during load, but it does not ship a standalone packaged JSON Schema for the registry record the way the runtime already does for `launch_plan` and `session_manifest`.

This repo also already has two useful pieces of infrastructure for persisted-artifact boundaries:

- packaged schema files under `src/houmao/agents/realm_controller/schemas/`
- lightweight runtime schema validation helpers in `schema_validation.py`

The requested follow-up is to make the shared-registry record participate in that same boundary contract: there should be one standalone schema file for the persisted JSON document, and runtime-managed create/update flows should validate against it before writing.

## Goals / Non-Goals

**Goals:**
- Add one packaged standalone JSON Schema file for shared-registry `record.json` v1.
- Validate runtime-managed registry-record creation and rewrite paths against that packaged schema before the atomic write step.
- Keep the schema contract aligned with `LiveAgentRegistryRecordV1` so the packaged file and typed model do not drift silently.
- Reuse existing runtime schema-validation infrastructure rather than introducing a new dependency or schema subsystem.

**Non-Goals:**
- Redesigning the registry record shape, lease rules, or identity semantics introduced by `add-central-agent-registry`.
- Changing registry load/resolution behavior beyond what is needed for write-path schema enforcement.
- Generalizing full JSON Schema validation for every runtime artifact in this change.
- Introducing a new external JSON Schema library if the existing repo-local validation approach is sufficient.

## Decisions

### 1. Package a dedicated `live_agent_registry_record.v1.schema.json` file under the existing runtime schema directory

The change will add a standalone schema file for the shared-registry record under:

```text
src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v1.schema.json
```

Rationale:
- it follows the repo's current naming and packaging pattern for persisted artifact schemas,
- it makes the on-disk registry contract discoverable without reading Python source,
- the versioned file name keeps future schema revisions explicit.

Alternatives considered:
- `registry_record.v1.schema.json`: rejected because it is less specific once more registry-owned files exist later.
- no standalone schema file: rejected because it preserves the current gap the change is meant to close.

### 2. Keep `LiveAgentRegistryRecordV1` as the typed construction/load boundary and use the packaged schema as the shipped disk contract

Runtime code will continue to construct and parse registry records through `LiveAgentRegistryRecordV1`. The standalone JSON Schema will be the packaged external contract for the persisted file, and tests will explicitly keep the schema aligned with the model.

Rationale:
- the model already captures strict typing, normalization, and cross-field validation ergonomically,
- the packaged schema serves a different purpose: a stable inspectable contract for persisted JSON,
- keeping both surfaces is consistent with the repo's existing persisted-artifact boundary approach.

Alternatives considered:
- schema-only without a Pydantic model: rejected because it would weaken the typed runtime boundary.
- Pydantic-only with no packaged schema: rejected because it leaves the persisted artifact without a standalone contract.

### 3. Enforce schema validation in the shared-registry publish path so one hook covers both first write and later rewrites

The runtime will validate the serialized registry payload against the packaged schema inside `publish_live_agent_record()` before the atomic replace step. Because all runtime-managed create/refresh flows funnel through that helper, this one validation point covers:

- initial record creation,
- later lease-refresh rewrites,
- publication updates caused by gateway/mailbox/runtime state changes.

Rationale:
- one choke point is simpler and less error-prone than validating at many call sites,
- it satisfies the requested “creation/modification” boundary directly,
- it preserves atomic-write semantics by failing before replacement rather than after a partial update.

Alternatives considered:
- validate only when reading records: rejected because the request is specifically about creation/modification-time enforcement.
- validate only in tests: rejected because that would not enforce the contract in production runtime behavior.

### 4. Keep the packaged registry schema within the subset the existing runtime validator can enforce

The repo's `schema_validation.py` helper is intentionally lightweight. The packaged registry schema should therefore stay within that supported subset for write-time validation, even if that means authoring a flatter schema document instead of relying on more complex `$ref`-heavy or `anyOf`-heavy generated output.

Rationale:
- it avoids introducing a new dependency for this focused follow-up,
- it keeps runtime write-time validation deterministic and easy to reason about,
- it lets the change reuse existing packaging and validation helpers rather than expanding them first.

Alternatives considered:
- adding a full JSON Schema engine dependency: rejected unless the current helper proves insufficient for the needed registry schema shape.
- extending the helper to support a much larger JSON Schema surface in this same change: rejected because that broadens scope beyond the concrete registry-record need.

## Risks / Trade-offs

- **Dual sources of truth (model + schema)** → Mitigate with schema-consistency tests that compare the packaged file against `LiveAgentRegistryRecordV1`.
- **A flatter packaged schema may duplicate nested structure textually** → Mitigate by keeping the schema narrow and versioned, and by adding explicit tests around required/optional registry fields.
- **Schema enforcement can reject publication that Pydantic alone would have accepted** → Mitigate by failing before atomic replace, surfacing the validation error clearly, and treating this as intentional enforcement of the packaged disk contract.

## Migration Plan

No durable migration is required. The registry record is lease-based and runtime-managed, so the new schema applies to runtime-generated create/update flows after rollout. Existing stale directories can continue to be ignored or cleaned by the existing cleanup tooling.

## Open Questions

None currently. The main implementation question is not product scope but execution detail: whether the packaged schema can stay inside the current validator's supported subset without expanding that validator. The design assumes yes and scopes the change accordingly.
