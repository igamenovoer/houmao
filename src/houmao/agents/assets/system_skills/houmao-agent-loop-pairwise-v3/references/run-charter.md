# Normalized Start Memo And Recovery Material

Use this reference when the user agent is ready to materialize the designated master's initialize memo contract and later send one compact `start` trigger, normally via mail.

## Required Fields

- `run_id`
- `plan_ref`
- plan revision, digest, or equivalent freshness marker
- designated master identity
- allowed participants
- workspace contract summary
- delegation policy summary
- prestart strategy summary
- initialize memo material summary
- explicit `operator_preparation_wave` summary when that strategy is selected
- routing packet validation summary, including graph artifact and packet JSON artifact used when available
- root routing packet or exact root packet reference when routing packets are part of the plan
- completion condition summary
- default stop mode
- reporting contract summary with canonical observed states

## Master Initialize Memo Template

```text
You are the master for pairwise loop run `<run_id>`.

Plan reference:
- type: <single-file | bundle>
- path: <canonical plan path such as <plan-output-dir>/plan.md>

Control-plane contract:
- I am outside the execution loop.
- Do not rely on me for liveness.
- Keep this run alive until the completion condition is satisfied or I send stop.
- I may later ask to `peek master <run_id>`, `pause <run_id>`, `resume <run_id>`, `recover_and_continue <run_id>`, or `stop <run_id>`.

Execution model:
- Use the authored plan for composed topology, recursive child-control edges, completion, stop, reporting, and lifecycle posture.
- Use the authored plan for workspace posture, writable surfaces, bookkeeping paths, and ownership boundaries.
- Use the Houmao elemental pairwise edge-loop pattern for each immediate driver-worker delegation edge.
- Every delegation edge must close back to its immediate driver.
- Child results must not bypass the immediate driver.
- Advise all agents to use email/mailbox as the default job communication channel for in-loop pairwise edge requests, receipts, and results.

Workspace contract:
- mode: <standard | custom>
- posture: <in-repo | out-of-repo | custom>
- task root or launch cwd: <task root, workspace root, or explicit custom cwd>
- source mutation surfaces: <declared writable source paths>
- shared writable surfaces: <declared shared writable paths or none>
- bookkeeping paths: <declared operator-visible bookkeeping paths>
- runtime-owned recovery files: remain outside this authored workspace contract

Delegation policy:
<normalized policy from references/delegation-policy.md>

Prestart posture:
- prestart strategy: <precomputed_routing_packets | operator_preparation_wave>
- initialize memo material: <master run contract plus participant-local memo guidance written under exact sentinels | not applicable>
- email/mailbox verification: <confirmed for every required participant | initialization blocked>
- operator preparation wave: <not selected | targeted preparation mail sent to explicit target set>
- gateway mail-notifier interval: <5s unless user specified otherwise when operator preparation wave is selected>
- acknowledgement mode: <fire_and_proceed | require_ack>
- required acknowledgements: <not applicable | completed for targeted preparation recipients>
- routing packet validation: <completed by validate-packets | completed by manual visible-coverage check | not applicable>
- graph artifact: <none | NetworkX node-link graph path>
- packet JSON artifact: <none | packet JSON path>
- root routing packet: <inline packet text or exact packet reference>
- child packet forwarding rule: append prepared child packets verbatim to pairwise edge request email; do not edit, merge, or summarize unless the plan explicitly permits it
- mismatch rule: stop downstream dispatch and report when a child packet is missing, has the wrong recipient, or has a stale plan revision or digest
- in-loop job communication: <email/mailbox default | explicit override>

Completion condition:
<user-defined operational success condition>

Default stop mode:
<interrupt-first | graceful>

Reporting contract:
<peek, completion, and stop-summary expectations using canonical observed states>
```

## Compact Start Trigger Template

```text
You are the master for pairwise loop run `<run_id>`.

Read your pairwise-v3 initialize memo for run `<run_id>`.
Use that memo plus the authored plan as the control-plane contract for this run.
Start the run now.
```

Deliver this compact trigger through mail by default. Use direct prompt delivery only when the user explicitly asks for it.

## Recovery Continuation Page Template

```text
You are continuing pairwise loop run `<run_id>` after restart recovery.

Recovery posture:
- recovery epoch: <epoch number>
- plan reference: <canonical plan path and freshness marker>
- this is the same logical run id, not a brand-new run

Before fresh work, inspect and reconcile:
- leftover mailbox state
- `houmao-memo.md` and linked pages
- workspace, branch, or local artifact state
- notes, logs, tmp outputs, or partial results
- incomplete downstream obligations or pending result-return duties

Execution model:
- use the authored plan plus this recovery page as the continuation contract
- keep following the authored workspace contract for writable and read-only surfaces
- do not invent a replacement run id
- re-arm any live reminder posture that the recovery summary says must be recreated after acceptance
```

## Compact Recover-And-Continue Trigger Template

```text
You are the master for recovered pairwise loop run `<run_id>`.

Read the durable recovery page at `pages/<relative-page>`.
Use that page plus the authored plan as the continuation contract for this run.

Reply with exactly one of:
- accepted
- rejected
```

## Guardrails

- Keep the charter page compact and normalized.
- Send the plan reference, policy summary, initialize memo posture, and root routing packet or exact root packet reference when routing packets are used, not a second unstructured copy of the whole plan.
- Keep the workspace contract summary faithful to the authored plan. Do not translate `custom` into `houmao-ws/...`.
- Do not omit the statement that the user agent is outside the execution loop.
- Do not use the compact start trigger as the only readable copy of the full run contract when the designated master's managed memory is being used.
- Do not default ordinary `start` to direct prompt delivery.
- Do not ask the master to infer child packet content from the full plan when the packet inventory should already be authored.
- Do not ask the master or intermediate drivers to run graph analysis or recompute descendant slices after `start`; they must use dispatch tables and exact child packets prepared before `ready`.
- Do not reuse the compact start trigger as the only restart-recovery contract; `recover_and_continue` needs the recovery-specific durable page.
