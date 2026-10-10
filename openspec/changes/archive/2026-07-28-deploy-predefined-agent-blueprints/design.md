## Context

Houmao already stores concrete specialists, project profiles, registered skills, and launch settings. Those contracts are suitable for a project that has already decided every value. They are too strict for authoring a reusable individual agent from prose, examples, source skill directories, and task-specific unknowns.

The original version of this change combined authoring, single and batch deployment, runtime variables, mindsets, private workspaces, and live launch behavior. That shape produced 150 tasks and coupled four persistence lifecycles. This revision keeps the complete user journey but splits it across independently implementable changes.

This foundational change owns UC-01 and UC-02. It ends after one Agent Deployment has been applied to a project and a launch command has been returned.

## Goals / Non-Goals

**Goals:**

- Preserve human-authored requirements in one freeform source entrypoint.
- Record a reviewable operator-agent interpretation without rewriting source.
- Materialize an immutable portable Agent Definition Revision.
- Declare typed deployment inputs and exact target bindings.
- Separate operator-authored requests from deterministic deployment plans.
- Create one project Agent Deployment with complete provenance.
- Reuse the existing `houmao-agent-definition` shared routine.

**Non-Goals:**

- Batch deployment.
- Managed-agent runtime variables or mindset records.
- Private workspace materialization.
- Provider-neutral skill invocation interception.
- Freeform semantic rewrites that product code claims to validate.
- Live managed-agent launch during definition deployment.

## Decisions

### Keep One Freeform Source Entrypoint

An authoring workspace uses:

```text
<workspace>/
  intent/
    src/
      agent-def-overview.md
      <optional files referenced by the overview>
    derived/
      interpretation.md
      materialization.toml
      materials/
      validation.json
      approval.toml
  agent-definition/
    <materialized immutable revision>
```

`init-intent` creates only `intent/src/agent-def-overview.md`. The overview may reference supporting files when prose becomes too large. Unreferenced siblings are outside the source set.

The source set is human-owned. Derivation records the digest of the overview and every referenced file. It never edits source files.

### Keep Derived Intent Small

The original design created separate mapping, placeholder, skill-resolution, runtime-variable, mindset, workspace, packet, validation, and approval files. Several repeated the same facts and could drift.

The revised derived layer contains:

- `interpretation.md`: the operator agent's readable interpretation, assumptions, and unresolved authoring questions;
- `materialization.toml`: the normalized machine input and source-to-output mapping;
- `materials/`: copied skill directories and other approved definition assets;
- `validation.json`: source and material digests plus validation findings;
- `approval.toml`: the human approval bound to the exact derived digest.

`materialization.toml` is the only machine input to materialization. Human-readable reports may be generated on demand but are not parallel authorities.

### Materialize an Immutable Agent Definition Revision

The portable revision uses:

```text
agent-definition/
  definition.toml
  deploy-contract.toml
  instance-contract.toml
  assets/
    prompts/
    memo/
    skills/
  provenance/
    materialization.json
```

`definition.toml` contains schema version, definition identity, revision identity, purpose, component references, and whole-revision digest.

`deploy-contract.toml` declares deployment inputs and bindings. `instance-contract.toml` is the extension boundary for later per-instance features. This change validates its schema and digest but does not define runtime-variable, mindset, or private-workspace behavior.

The materialized revision contains complete copies of source Agent Skills. It never depends on the original authoring path.

### Use Typed Bindings Instead of Semantic Adaptation Modes

Each deployment input declares:

- stable key;
- scalar type or maintained enum;
- required or optional posture;
- optional default;
- validation bounds;
- one or more typed target bindings;
- rendering mode for text targets.

Structured targets use typed field assignments. Text targets use exact non-executable markers such as `{{houmao.deploy.task_objective}}`. Rendering applies context-specific escaping and rejects unknown or unresolved markers.

V1 does not include `semantic_patch` or `semantic_replace`. A change that cannot be represented by a declared binding requires a new Agent Definition Revision. This makes validation honest and reproducible.

### Split Deployment Request From Deployment Plan

A Deployment Request records:

- exact definition revision and digest;
- target project;
- typed user-supplied input values;
- explicitly selected tool and credential references;
- selected project workdir and maintained launch posture;
- no secrets.

The request contains intent, not rendered project files.

Planning snapshots the request and definition, resolves every binding, validates project collisions, renders generated content, and writes a Deployment Plan under `.houmao/jobs/agent-definition-deployments/<plan-id>/`.

The plan contains:

- request reference and digest;
- definition reference and digest;
- resolved project names and references;
- rendered files and their digests;
- proposed catalog rows and managed-content paths;
- warnings and blockers;
- plan schema and target project identity.

Apply consumes only an intact plan. It does not repeat operator judgment.

### Model Project Apply as Recoverable Visibility

SQLite and filesystem writes cannot share one transaction. Apply therefore uses a recoverable operation state rather than claiming physical atomicity:

```text
planned -> preparing -> prepared -> committing -> applied
                         |             |
                         +-> failed <--+
```

Managed content is written to operation-owned staging paths. The catalog transaction makes the Agent Deployment visible only after every staged artifact is ready. Final path publication uses atomic replacement where the filesystem supports it.

If a crash occurs, doctor detects the operation state and either finishes publication or removes only operation-owned staged content. User-owned or previously applied paths are never deleted by rollback.

### Persist One Ordinary Agent Deployment

The project catalog stores one Agent Deployment with:

- opaque deployment id and human-facing name;
- definition identity, revision, and digest;
- request and plan references and digests;
- generated specialist and project-profile relationships;
- registered-skill relationships;
- managed-content references and digests;
- instance-contract digest;
- created and updated timestamps.

Large packets, rendered files, and skills remain file-backed. Credential records contain references only.

Identical immutable registered-skill content may be reused through a project cache keyed by content digest. Deployment-specific rendered files remain owned by the deployment.

### Make Update and Removal Explicit

Update always creates a fresh request and plan. It rejects local output drift and a changed definition identity.

An update that changes `instance_contract_digest` is blocked while any live or preserved managed-agent instance references the deployment. The operator must create a new deployment or use a future explicit instance-migration feature.

Removal rejects live or preserved instance references. It deletes only catalog-owned relationships and managed files whose digest and ownership still match. Credentials and user-owned files remain intact.

### Reuse the Existing Agent Definition Routine

The public `houmao-shared-routines` skill already exposes `houmao-agent-definition`. That routine owns:

- `init-intent`;
- `derive`;
- `clarify`;
- `approve`;
- `materialize`;
- `validate`;
- `plan-deployment`;
- `apply-deployment`;
- `inspect`;
- `doctor`;
- `update`;
- `remove`.

`houmao-admin-entrypoint` routes natural-language authoring and deployment requests there. The managed-agent entrypoint does not expose definition administration. Deployment returns a maintained profile-backed launch command and does not execute it.

### Treat Authoring and Definition Content as Untrusted Data

All referenced paths are confined beneath their declared roots. Symlinks and special files are rejected at copy and materialization boundaries. TOML and Markdown content never becomes executable configuration.

Credential values are never stored in source, derived material, revisions, requests, plans, or catalog provenance.

## Risks / Trade-offs

- [Users want task-specific prose changes beyond declared bindings] -> Require a new revision in v1 and consider reviewed operator-authored edits in a later change.
- [Repeated skill copies consume disk] -> Reuse immutable project skill content by digest while retaining portable copies in definition revisions.
- [A crash occurs between catalog commit and final path publication] -> Preserve operation state and let doctor complete or reconcile publication.
- [Definition update invalidates preserved instance state] -> Block instance-contract changes while any live or preserved instance references the deployment.
- [The historical change name still says blueprints] -> Treat the directory name as an existing OpenSpec identifier; all user-facing terminology uses Agent Definition.

## Migration Plan

1. Add authoring workspace and revision schemas.
2. Add generic validation and materialization.
3. Add Deployment Request and Deployment Plan models.
4. Add project catalog migration and managed deployment storage.
5. Add recoverable plan apply, doctor, update, and removal.
6. Extend the existing Agent Definition routine and route tables.
7. Package a validating reference definition and update documentation.
8. Run focused tests, full project validation, and distribution checks.

Existing specialists and profiles remain valid. Existing projects run the maintained project migration before using Agent Deployments.

## Open Questions

None block this foundational change. Batch operations, mutable instance state, and private workspaces are owned by their dependent OpenSpec changes.
