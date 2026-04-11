## Context

`houmao-adv-usage-pattern` currently documents self-notification, pairwise edge-loop, and relay-loop workflow compositions over existing messaging, mailbox, and gateway skills. The pairwise and relay pages are useful as protocol references, but they currently drift into larger composition planning: the pairwise page describes recursive child edge-loops and parent linkage, while the relay page describes fan-out ownership and many-loop supervision.

The repository now also contains dedicated loop-planning skills for composed runs, including `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-relay`. Those skills own plan authoring, graph rendering, master/run-control boundaries, and operational actions such as start, status/peek, stop, and hard-kill where applicable. The advanced-usage pattern docs should remain one layer lower: reusable elemental protocols that those planning skills can compose.

This change is documentation and packaged-skill guidance only. It does not add a new workflow engine, gateway endpoint, mailbox route, or manager command.

## Goals / Non-Goals

**Goals:**

- Make the pairwise pattern page describe one two-node driver/worker local-close round.
- Make the relay pattern page describe one ordered N-node relay lane with one master/loop origin and one final egress.
- Remove or redirect graph-composition language from the elemental pattern pages.
- Keep existing protocol mechanics for queued gateway prompt handoff, mailbox receipts/results/acknowledgements, local `HOUMAO_JOB_DIR` ledgers, status-aware retry, idempotent retry, and context-derived timing policy.
- Add chooser/boundary guidance so readers know when to switch from an elemental pattern page to a dedicated loop-planning skill.

**Non-Goals:**

- Implementing or changing runtime behavior.
- Adding new mailbox, gateway, notifier, or manager APIs.
- Removing the dedicated loop-planning skills.
- Preserving recursive pairwise graph guidance in the advanced-usage pairwise page.
- Teaching multi-loop relay graphs in the advanced-usage relay page.

## Decisions

### Treat `houmao-adv-usage-pattern` as the elemental protocol layer

The top-level advanced-usage skill should describe the pattern pages as atomic protocol references and distinguish them from dedicated planning/run-control skills.

Why:

- The advanced-usage skill is already positioned above direct-operation skills, but it should not also become the graph authoring layer.
- Keeping it elemental makes the pages easier for agents to apply inside larger workflows without mixing local protocol details with topology planning.

Alternative considered:

- Keep the current combined protocol-plus-graph guidance. Rejected because it makes the pairwise and relay pages look like competing graph frameworks instead of reusable building blocks.

### Collapse the pairwise page to a two-node local-close round

The pairwise pattern should focus on one driver, one worker, one `edge_loop_id`, a receipt, a final result, and a final-result acknowledgement.

Why:

- That is the irreducible pairwise invariant: the worker returns the result to the same driver that sent the request.
- Recursive child edge-loops and parent linkage are composition concerns. They belong in dedicated pairwise loop-planning material, not in the elemental page.

Alternative considered:

- Keep child-loop recursion but label it optional. Rejected because the page still teaches the complex case first enough to dilute the two-node protocol.

### Collapse the relay page to one ordered N-node lane

The relay pattern should focus on one master/loop origin, one ordered relay path, hop-specific `handoff_id` values under one `loop_id`, and a final egress returning the result to the master.

Why:

- The relay invariant is forward ownership transfer along one lane, followed by distant return to the origin.
- Multi-lane route policy, fan-out, and graph-of-loops behavior requires plan-level decisions and belongs in `houmao-agent-loop-relay`.

Alternative considered:

- Keep “fan-out” and “many outbound loops” language while adding a note that the page can be simplified. Rejected because that leaves the default mental model as a graph controller.

### Preserve local state, retry, and timing mechanics

Both elemental pattern pages should continue to require local scratch ledgers under `HOUMAO_JOB_DIR`, mailbox-check-first retry behavior, stable identifiers for idempotent resend, and context-derived timing policy.

For the pairwise pattern, the driver should add one more gate before resending: after checking mailbox and finding no receipt or result, the driver should first peek the downstream worker's visible state for that `edge_loop_id` through `houmao-agent-inspect`. If the read-only peek shows the worker is still working on the same request, the driver should update local state and schedule the next review instead of resending. If read-only inspection is unavailable or inconclusive and the resend decision remains ambiguous, an active prompt, ping, or direct message status probe is allowed only as a last resort before resend. A resend is appropriate only when the expected signal is missing, the review is due, and the worker cannot be observed or confirmed as still owning or actively working the request.

For the relay pattern, each upstream sender in the ordered lane should use the same gate before resending a due handoff. After checking mailbox and finding the expected receipt, final result, or acknowledgement still missing, the upstream sender should first peek the downstream agent's visible state for the same `loop_id` and `handoff_id` through `houmao-agent-inspect`. If the read-only peek shows the downstream agent still owns or is actively working the handoff, the upstream sender should update local review state and schedule the next review instead of resending. If read-only inspection is unavailable or inconclusive and the resend decision remains ambiguous, an active prompt, ping, or direct message status probe is allowed only as a last resort before resend.

Why:

- The user-requested narrowing is about topology scope, not changing the underlying reliability contract.
- These mechanics are still needed for one pairwise round and one relay lane.
- Pairwise resend should not punish a correctly running worker that has not yet produced a result; read-only inspection reduces duplicate prompt pressure while keeping a last-resort active status probe available for ambiguous loss.
- Relay resend has the same duplicate-pressure risk; read-only inspection preserves observability by default, while a last-resort active status probe remains available when inspection cannot answer the liveness question.

Alternative considered:

- Remove supervisor and optional self-mail checkpoint content entirely. Rejected because even elemental rounds still need explicit follow-up and durable-enough backlog pointers in long-running work.
- Always resend when the result is overdue after mailbox review. Rejected because it can interrupt or duplicate active worker effort when the worker is visibly still handling the same `edge_loop_id`.
- Use active `ping` or a fresh prompt as the default pairwise or relay peek path. Rejected because active probes can disturb downstream work and should be reserved as the last resort when mailbox state and read-only inspection cannot resolve the resend decision.

### Route composed topology to dedicated loop skills

The advanced-usage chooser should direct readers to dedicated loop-planning skills when they need a master-owned run, multiple pairwise edges, a pairwise tree, multiple relay lanes, rendered graphs, or run-control actions.

Why:

- The dedicated skills already define plan structures, graph rendering rules, and run-control boundaries.
- This keeps each skill’s ownership clear and avoids duplicating plan-level guidance in the lower-level pattern pages.

Alternative considered:

- Add a new “complex cases” section inside `houmao-adv-usage-pattern`. Rejected because it recreates the same ownership overlap the change is trying to remove.

## Risks / Trade-offs

- [Loss of inline recursive examples] -> Readers who used the pairwise page as a tree recipe may need one extra hop to the dedicated pairwise loop-planning skill. Mitigation: add explicit redirect guidance from the pairwise page and top-level chooser.
- [Ambiguous relay term “loop”] -> A single ordered relay lane can still be confused with a graph cycle. Mitigation: define the loop as the master-owned supervision/result-return loop, not arbitrary worker-to-worker cycling.
- [Over-removing supervision guidance] -> Narrowing the pages too aggressively could omit necessary retry behavior. Mitigation: preserve local ledger, supervisor reminder, optional self-mail checkpoint, mailbox-check-first retry rules, read-only peek-before-resend handling, and last-resort active status probes for the elemental round/lane.
- [Manual-invocation pairwise skill boundary] -> Some dedicated pairwise skills are manual-invocation-only. Mitigation: phrase redirects as “use a dedicated loop-planning skill when explicitly invoked or when that skill is the selected workflow,” rather than auto-triggering manual skills from generic wording.

## Migration Plan

1. Add a delta spec for `houmao-adv-usage-pattern-skill` that narrows pairwise and relay requirements to elemental patterns and updates chooser guidance.
2. Update `houmao-adv-usage-pattern/SKILL.md` to describe atomic pattern pages and redirect composed topology to dedicated loop skills.
3. Revise the pairwise pattern page to remove recursive child edge-loop sections, `parent_edge_loop_id` requirements, and complex graph-planning wording, while adding the downstream-worker peek gate before any resend.
4. Revise the relay pattern page to remove fan-out, many-loop, and graph-of-loops wording while keeping one ordered N-node lane and adding downstream peeking before resend, with active status probes reserved as the last resort.
5. Run relevant validation for system-skill assets or docs text.

Rollback is low risk: restore the previous wording from version control and revert the delta spec before archive.

## Open Questions

None for proposal scope. The requested direction is clear: elemental pairwise and relay patterns in `houmao-adv-usage-pattern`; composed graphs in dedicated loop skills.
