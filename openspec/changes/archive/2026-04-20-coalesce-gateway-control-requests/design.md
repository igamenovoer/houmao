## Context

The live gateway persists terminal-mutating work in `queue.sqlite` and serializes execution through `GatewayServiceRuntime._worker_loop()`. Public queued work enters through `POST /v1/requests` as `submit_prompt` or `interrupt`; internal mail notifier prompts use an internal stored request kind, `mail_notifier_prompt`. Direct prompt control uses `/v1/control/prompt` and is not part of the durable queue path.

Issue 35 targets the durable queue path: adjacent special control commands can pile up while the target is busy, then execute later as stale history. Ordinary prompts must remain ordered and unmerged, but commands like `interrupt`, `/compact`, `/clear`, and `/new` are control intents where later pending records often supersede earlier pending records.

## Goals / Non-Goals

**Goals:**

- Coalesce adjacent accepted control-intent records before execution.
- Keep ordinary prompts and internal notifier prompts semantically unchanged.
- Make control-command classification conservative and explicit.
- Persist audit evidence for requests removed from execution by coalescing.
- Keep behavior durable across gateway restart by applying coalescing when accepted work is selected for execution.

**Non-Goals:**

- Do not coalesce direct `/v1/control/prompt` requests because they bypass the durable queue.
- Do not infer control intent from prose, multiline prompts, or partial command text.
- Do not introduce new public request kinds.
- Do not add a user-facing queue management API in this change.
- Do not coalesce across managed-agent epoch boundaries or across ordinary prompt boundaries.

## Decisions

### Coalesce At Dequeue Time

Apply coalescing inside `GatewayServiceRuntime._take_next_request()` before promoting accepted work to `running`.

Rationale: this is the narrow point where durable accepted records become executable. It covers direct gateway HTTP callers, server proxy callers, runtime controller callers, and accepted records recovered after gateway restart.

Alternative considered: coalesce only in `create_request()` after inserting each new record. That would keep queue depth cleaner immediately after admission, but it would not reliably cover older accepted rows after restart or rows inserted by future internal paths. Enqueue-time coalescing can be added later as an optimization if needed.

### Use Conservative Control-Intent Classification

Classify a queued record as coalescible only when it is:

- `interrupt`, or
- `submit_prompt` with a prompt whose trimmed entire content is exactly one recognized control command.

Initial recognized prompt commands:

- `/compact`
- `/clear`
- `/new`

`mail_notifier_prompt` is always non-coalescible, even if its prompt text happens to mention a control command.

Rationale: exact whole-prompt classification avoids damaging ordinary agent instructions such as "please run /compact later" or multiline prompts containing a command example.

Alternative considered: parse command prefixes or provider-specific command syntax more broadly. That is riskier because queued prompts are user-authored content, not a structured control-command envelope.

### Treat Ordinary Work As A Hard Boundary

Scan the accepted queue in `accepted_at_utc` order. If the oldest accepted record is ordinary work, promote it unchanged. If the oldest accepted record is a control intent, scan only the maximal adjacent accepted control-intent block with the same `managed_agent_instance_epoch`. Stop at the first ordinary prompt, `mail_notifier_prompt`, unsupported kind, or different epoch.

Rationale: this preserves prompt ordering while still cleaning up runs of pending control work. It also keeps epoch safety aligned with the existing replay boundary.

Alternative considered: coalesce all pending control intents anywhere in the queue. That can reorder control relative to ordinary prompts and would violate the guardrail from the issue.

### Normalize A Control Block To One Interrupt Plus One Context Action

Within one adjacent control-intent block:

- duplicate `interrupt` records collapse to one interrupt intent,
- context commands collapse to the strongest latest effective context command,
- `/new` supersedes `/clear` and `/compact`,
- `/clear` supersedes `/compact`,
- duplicate `/compact` collapses to one `/compact`,
- if the block contains both interrupt and a context action, execute interrupt first, then the final context action.

The effective executable row should be the earliest row needed to preserve the normalized action order. If a single effective action remains, promote one surviving row. If both interrupt and context action remain, preserve two surviving rows in queue order by marking all other rows coalesced and adjusting payloads only where the surviving row already has the matching request kind. Avoid converting one public request kind into another when a matching surviving row exists.

Rationale: interrupt and context reset are different kinds of control. Collapsing all of them to only the last context command could skip the operator's intent to stop active work first.

Alternative considered: choose only the final command in the block. Simpler, but it loses interrupt intent in common "interrupt then reset" bursts.

### Persist Coalesced Records Explicitly

Add `coalesced` to the stored request state model and mark skipped accepted rows as `coalesced` with `finished_at_utc` set. Store a compact `result_json` containing:

- `coalesced_into_request_id`,
- `coalesced_reason`,
- `effective_actions`,
- optionally `coalesced_at_utc`.

Append a gateway event with `kind = "coalesced"` listing the affected request ids and effective actions.

Rationale: completed and failed rows already remain as durable history. A distinct `coalesced` state keeps queue depth correct while making the dropped work inspectable.

Alternative considered: delete redundant rows. That would make queue depth clean but erase the diagnostic trail requested by issue 35.

## Risks / Trade-offs

- [Risk] A prompt that looks like a control command could be ordinary content. -> Mitigation: require exact whole-prompt matches after trimming whitespace.
- [Risk] The normalized two-action sequence could still be surprising for mixed bursts. -> Mitigation: document the rule explicitly and cover it with tests.
- [Risk] Adding a stored request state touches schema validation and docs. -> Mitigation: use the existing queue schema migration path and keep `coalesced` terminal like `completed` and `failed`.
- [Risk] Coalescing at dequeue time means `queue_depth` can briefly include records that will later be coalesced. -> Mitigation: this is acceptable for v1 because execution correctness is the priority; enqueue-time cleanup remains a possible follow-up.

## Migration Plan

Existing `queue.sqlite` files do not need data migration because the schema stores `state` as text. The runtime and model literals must accept `coalesced`; any existing records keep their current states. Rolling back to a version that does not know `coalesced` may make historical coalesced rows unreadable through strict helpers, so rollout should pair the runtime change with the model update.

## Open Questions

- Should future versions expose a queue-inspection endpoint for terminal states beyond status queue depth?
- Should enqueue-time coalescing be added after dequeue-time behavior proves stable?
