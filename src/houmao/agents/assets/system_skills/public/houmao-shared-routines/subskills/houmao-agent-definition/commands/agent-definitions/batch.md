# Agent Definition Batch Deployment

## Purpose

Expand one immutable definition revision into a bounded set of ordinary single-instance deployment plans. Batch is orchestration, not a second deployment model. Every member keeps the same validation, placeholder, runtime-state, private-workspace, and launch-handoff contracts as a single deployment.

## Delegation Gate

Require `--count` from 1 through 32. Treat missing names, tools, and credentials as blockers unless the user explicitly delegates that category:

- `--delegate-names`
- `--delegate-tools`
- `--delegate-credentials`

Delegation is narrow. It does not authorize guessing deploy-input values, private-workspace posture, tracked-workspace consent, or overrides that the user fixed. Tool and credential selection may use only supported tools and existing compatible credential names.

## Workflow

1. Require the exact immutable revision and shared deploy inputs.
2. Collect any member-specific overrides as JSON objects with a stable member ordinal. Preserve explicit values exactly.
3. Create a batch plan:

   ```bash
   houmao-mgr project agent-definitions batch-plan <revision> \
     --count <N> \
     --set <key>=<value> \
     --workdir <project-path> \
     --name-prefix <prefix> \
     --delegate-names \
     --tool <tool> \
     --credential <credential>
   ```

   Use the minimum delegation flags needed. Add repeatable `--member-override '<object>'` for per-member overrides. Add private-workspace options only when the user selected them.
4. Review the batch envelope and every member plan. Report deterministic names, tools, credentials, revision digests, workspace posture, collisions, and blockers. Cross-member and project collisions block before apply.
5. Apply the frozen batch plan:

   ```bash
   houmao-mgr project agent-definitions batch-apply <batch-plan.json>
   ```

6. Report the operation id, ordered member deployment identities, and each explicit launch handoff. State that no member was launched.
7. Inspect or recover an operation with:

   ```bash
   houmao-mgr project agent-definitions batch-inspect-operation <batch-plan.json>
   houmao-mgr project agent-definitions batch-doctor
   ```

The catalog stores ordinary deployment rows correlated by operation id and ordinal. It does not create a durable batch domain object.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the delegation gate, ordinary deployment contracts, collision rules, and user request, then execute the plan.

## Atomic Visibility Contract

Before the catalog commit, no member deployment is visible. A prepare failure rolls back batch-owned project resources. The catalog commit inserts all member deployment rows in one SQLite transaction. Projection publication follows the commit and is recoverable through batch doctor. Launch remains a later explicit user action for each returned handoff.

## Guardrails

- DO NOT create member plans until delegation gaps and all collisions are resolved.
- DO NOT broaden one delegation category into another.
- DO NOT leave a subset of member deployment rows visible after a pre-commit failure.
- DO NOT launch members during batch apply.
- DO NOT describe an operation id as a new reusable or independently mutable batch entity.
