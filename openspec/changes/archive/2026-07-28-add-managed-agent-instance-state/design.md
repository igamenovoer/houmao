## Context

Agent Definition Revisions contain an `instance-contract.toml` extension boundary. UC-04 needs typed per-instance runtime variables. UC-06 needs named mindset declarations, independent per-instance records, and immutable snapshots for skills.

Houmao already gives each managed agent a persistent memory root at `.houmao/memory/agents/<agent-id>`. Current `agents self` resolution, however, depends on the caller being inside a registered tmux session. Supported headless runtimes also receive a runtime manifest pointer, so tmux is the wrong identity boundary.

## Goals / Non-Goals

**Goals:**

- Store all canonical mutable definition-driven instance state in one database.
- Preserve state across supported relaunch of the same instance.
- Provide verified-self reads across supported managed runtimes.
- Keep static skills unchanged when state changes.
- Keep runtime variables and mindsets low-authority and non-secret.
- Define a truthful skill-to-mindset consumption protocol.

**Non-Goals:**

- Managed-self mutation.
- Shared state between peer agents.
- Runtime state in the project catalog.
- Provider-neutral interception of every skill invocation.
- Automatic migration between incompatible instance-contract digests.
- Mindset records as tool authority, workflow gates, or prompt instructions.

## Decisions

### Use One Canonical Instance-State Database

Each managed agent uses:

```text
.houmao/memory/agents/<agent-id>/
  houmao-memo.md
  pages/
  state.sqlite
```

`state.sqlite` contains:

- store schema and agent identity metadata;
- exact deployment and instance-contract identities and digests;
- runtime-variable declarations, values, revisions, and timestamps;
- mindset declarations, question configuration, records, revisions, and timestamps;
- launch-preparation attempts and state.

The project catalog stores immutable declarations and the instance-contract digest. It does not store mutable values or mindset records.

### Resolve Verified Self From Runtime Authority

Verified-self resolution follows:

1. Read the runtime-owned manifest path from the maintained environment pointer.
2. Confine and parse the manifest.
3. Verify its agent identity, runtime identity, and target project.
4. Resolve the current shared-registry record by opaque agent id.
5. Require the manifest generation and runtime binding to match the current record.
6. Reject stopped, stale, foreign-project, or ambiguous authority.

Tmux-backed runtimes may additionally cross-check the current tmux binding. Tmux presence is not the primary identity requirement.

User prompt text, cwd names, environment variables supplied outside a Houmao runtime, and guessed agent names never establish self authority.

### Use a Recoverable Managed-Launch State Machine

Launch preparation uses:

```text
absent -> preparing -> prepared -> starting -> active
                        |            |
                        +-> failed <-+
```

Preparation is idempotent. A fresh instance initializes `state.sqlite`, runtime-variable revision one, and mindset revision one before process start. A preserved compatible instance revalidates and reuses its state.

On failure, Houmao records the failed attempt. It removes only state created by that fresh attempt when no user mutation or preserved instance reference exists. It never promises a transaction that includes SQLite, files, and process startup.

### Define Runtime Variables as Typed Revisioned Values

The instance contract declares each variable's stable key, scalar type or enum, default, required posture, validation bounds, and consumers.

Launch combines declaration defaults with explicit per-instance values. Unknown keys, invalid types, and missing required values block preparation.

Prompt and memo consumers render from one immutable launch snapshot. Later updates do not rewrite submitted prompt context or overwrite memo edits. Static skill consumers call verified-self read commands and receive the current revision.

Operator mutation names one explicit agent target, validates an expected revision, and writes the next revision atomically. It does not prompt or wake the agent.

### Separate Mindset Declarations, Records, and Snapshots

The instance contract declares:

- stable mindset name;
- ordered stable question ids and default question text;
- optional bounded answer or note fields;
- static skills that require that mindset;
- optional projection posture used by the private-workspace change.

Fresh launch creates one record per declaration. A preserved compatible instance retains its revisions. V1 has no undefined “active mindset” subset and no implicit initial override. All declared mindsets initialize from the exact instance contract.

An admin revises one explicit agent and mindset name with expected-revision checking. Definitions do not silently reset existing records.

### Treat Mindset Consumption as a Skill Protocol

A static skill that requires a mindset includes an explicit first-phase instruction:

1. call the verified-self mindset snapshot command;
2. require the declared mindset name;
3. stop before task logic if lookup fails;
4. use the returned immutable revision for that invocation.

Definition validation checks every binding and verifies that packaged skill instructions declare the maintained snapshot step. Behavior tests cover manual and implicit skill invocation.

Houmao does not claim automatic invocation interception. A future provider hook may strengthen enforcement without changing the record model.

### Block Incompatible Instance-Contract Updates

An Agent Deployment update that changes its instance-contract digest is rejected while any live or preserved instance references the deployment. Fresh behavior requires a new deployment.

A future migration change may define variable-key removal, type conversion, mindset question reconciliation, and preserved-instance migration. V1 does not guess.

## Risks / Trade-offs

- [A headless process copies the manifest pointer] -> Verify current registry generation, runtime binding, project, and live state on every self operation.
- [A static skill ignores its required mindset step] -> Validate skill instructions and cover actual behavior; do not claim an unavailable runtime interceptor.
- [State schema changes after instances exist] -> Version the database and require explicit maintained migrations.
- [Definition updates conflict with preserved state] -> Block incompatible digest changes instead of silently reconciling.
- [Runtime variables carry secrets] -> Reject secret-marked declarations and direct users to credential mechanisms.

## Migration Plan

1. Add provider-independent verified-self resolution.
2. Add the instance-state database and migration framework.
3. Extend instance-contract validation.
4. Add recoverable launch preparation and preserved-instance compatibility checks.
5. Add runtime-variable commands and consumers.
6. Add mindset commands, snapshot protocol, and behavior tests.
7. Update system-skill routing and documentation.

## Open Questions

None block v1. Managed-self mutation, provider invocation hooks, shared state, and incompatible instance migration require separate changes.
