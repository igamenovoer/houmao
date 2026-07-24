## Context

The foundational Agent Definition change creates one Deployment Request, one deterministic Deployment Plan, and one ordinary project Agent Deployment. UC-03 asks the operator agent to repeat that operation `N` times while choosing only categories the human explicitly delegates.

The earlier design introduced a durable Agent Deployment Batch with its own inspection, doctor, update, removal, and nullable member graph. The user need is an all-or-nothing creation operation and provenance, not a second long-lived deployment lifecycle.

## Goals / Non-Goals

**Goals:**

- Validate every member before any deployment becomes visible.
- Bound operator discretion to explicit delegation categories.
- Preserve one exact definition revision and shared input contract.
- Correlate created deployments without coupling their later lifecycle.
- Recover cleanly from interrupted filesystem and catalog publication.

**Non-Goals:**

- A durable batch domain object.
- Batch-wide update, removal, launch, or instance state.
- Credential creation or secret storage.
- Invented per-member differences outside explicit overrides or delegation.

## Decisions

### Add Batch Request and Plan Envelopes

A Batch Deployment Request contains:

- exact definition revision and digest;
- target project;
- positive count within a maintained limit;
- shared deployment input values;
- optional definition-valid per-member overrides;
- explicit delegation booleans for names, tools, and credential references;
- user-fixed selections that delegation cannot replace.

A Batch Deployment Plan contains ordered ordinary member plans. Each member is valid as a single-deployment plan and includes its generated identity, resolved selections, rendered files, digests, and catalog proposal.

### Keep Delegation Field-Limited

The operator may select:

- unique project deployment and profile names when name delegation is present;
- a registered compatible CLI tool when tool delegation is present;
- an existing compatible credential reference when credential delegation is present.

Plural quantity alone grants no delegation. Missing delegation causes a focused question when a required selection remains unresolved.

The planner validates selections deterministically. It records the selected identity and rationale text, but product code does not claim to reproduce the operator's semantic rationale.

### Use an Operation Record, Not a Batch Domain Object

The planner assigns one opaque `batch_operation_id`. Each successful ordinary Agent Deployment stores that id and its member ordinal.

The operation record exists only in the deployment job area and operation journal. It supports apply recovery and provenance inspection. It is not a catalog entity with independent business lifecycle commands.

After success, each deployment is inspected, updated, launched, or removed independently. Removing one member does not mutate historical provenance on peers.

### Make Catalog Visibility All-or-Nothing

All member files are staged under `.houmao/jobs/agent-definition-batches/<operation-id>/`. Preflight covers:

- member validity;
- target project identity;
- cross-member name and path collisions;
- existing project collisions;
- tool and credential compatibility;
- complete rendered-content digests.

One SQLite transaction inserts every member Agent Deployment and marks the operation committed. No member becomes catalog-visible before all staged members are ready.

Filesystem and SQLite cannot be physically atomic. The operation journal records `planned`, `preparing`, `prepared`, `committing`, `applied`, or `failed`. Doctor completes publication or removes only operation-owned staging after an interruption.

### Reuse Single-Deployment Models and Apply Logic

Batch planning composes ordinary requests and plans. It does not maintain a second renderer or deployment schema. Shared inputs are expanded before ordinary member validation.

The existing `houmao-agent-definition` routine gathers the count and delegation, previews the ordered plan, requests confirmation, calls maintained batch apply, and returns one launch handoff per member without launching them.

## Risks / Trade-offs

- [A late member fails publication] -> Preserve the operation journal and keep all catalog members hidden until staged content is ready.
- [Delegated names collide] -> Validate the complete ordered set and target project before apply.
- [Operator discretion expands accidentally] -> Store explicit delegation flags and reject selections outside those categories.
- [Users later need batch lifecycle operations] -> Add a durable batch entity only after concrete lifecycle use cases exist.

## Migration Plan

1. Add batch request, plan, and operation-journal models.
2. Add complete-set validation and cross-member collision detection.
3. Add staged apply and one catalog visibility transaction.
4. Add member provenance fields and project migration.
5. Extend Agent Definition skill routing and behavior tests.

## Open Questions

None block v1. Batch-wide post-creation lifecycle operations require a separate change.
