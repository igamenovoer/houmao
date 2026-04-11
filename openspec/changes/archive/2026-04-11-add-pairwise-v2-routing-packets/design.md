## Context

`houmao-agent-loop-pairwise-v2` currently treats `initialize` as a standalone preparation wave before `start`. The authored plan may keep preparation material for every participant, but the default mail recipient set is delegating/non-leaf participants and acknowledgement gating applies only to targeted preparation recipients.

That model is useful when the operator wants explicit preflight, but it is heavier than needed for ordinary pairwise trees. It also asks agents in long-running work to remember or rediscover an old preparation message instead of receiving the relevant plan slice at the moment they are contacted. A fully cascading alternative would avoid the operator prep wave, but asking every intermediate node to recompute the descendant slice from the full plan would push graph reasoning into runtime handoffs.

This design keeps the lightweight cascade but moves the graph reasoning to the planning stage.

## Goals / Non-Goals

**Goals:**

- Make precomputed routing packets the default `houmao-agent-loop-pairwise-v2` prestart strategy.
- Do subtree slicing once while authoring or revising the plan.
- Let runtime intermediate agents append exact prepared child packets to downstream pairwise edge requests without recomputing the graph.
- Preserve the existing operator-origin preparation wave as an explicit strategy for complex plans, acknowledgement-gated preflight, or user-requested participant warmup.
- Keep the user agent outside the execution loop and keep accepted-run liveness on the master.

**Non-Goals:**

- No new runtime loop engine, queue, mailbox transport, or gateway endpoint.
- No change to the elemental pairwise edge-loop protocol in `houmao-adv-usage-pattern`.
- No change to the stable `houmao-agent-loop-pairwise` skill.
- No removal of the old preparation-wave behavior when it is explicitly selected.

## Decisions

### 1. Add an explicit prestart strategy field

Plans should choose one `prestart_strategy`:

- `precomputed_routing_packets` as the default
- `operator_preparation_wave` as the explicit opt-in legacy/enriched preflight path

Rationale: this preserves both user-facing options without overloading `fire_and_proceed` and `require_ack`. In the new default, `fire_and_proceed` and `require_ack` no longer describe the primary behavior because no operator-origin participant preparation mail is sent.

Alternative considered: keep `initialize` as the only switch and infer the mode from missing preparation targets. That would be too implicit and would make start readiness hard to audit.

### 2. Generate routing packets at plan time

The authoring lane should produce one root packet for the designated master and one child packet for each parent-to-child pairwise edge in the authored topology. For bundle plans, packets may live in a dedicated support file or directory, but `plan.md` must point to them from the canonical entrypoint. For single-file plans, packets may be sections under the plan.

Each packet should include:

- packet id
- run id or run id placeholder
- plan id plus plan revision, digest, or equivalent freshness marker
- intended recipient
- immediate driver
- local role and local objective
- allowed delegation targets
- dispatch table for any children
- exact child packet text or exact references to child packet text
- result-return contract back to the immediate driver
- mailbox, receipt, result, reminder, and timeout-watch obligations
- forbidden actions

Rationale: this keeps runtime handoffs local and mechanical. The intermediate agent does not need to infer descendants, extract subtrees, or decide what a child needs to know.

Alternative considered: let each intermediate agent slice the accepted plan when dispatching children. That is flexible but makes every intermediate node a graph planner and increases the chance of inconsistent slices.

### 3. Make runtime forwarding verbatim and fail-closed

The master receives the root routing packet in the start charter. Any driver that delegates to a child appends the exact packet for that child to the normal pairwise edge request. The driver may add local request context, but it must not edit, merge, or summarize the child routing packet unless the plan explicitly allows that transformation.

If the expected child packet is missing, the packet recipient does not match the intended child, or the packet revision does not match the active plan revision, the driver should stop that downstream dispatch and report the mismatch to its own immediate driver or, for the master, to the operator.

Rationale: packet forwarding should be easy to execute correctly. Fail-closed behavior is better than letting agents repair routing contracts from memory.

Alternative considered: allow runtime summarization to reduce prompt size. That saves tokens but reintroduces context drift and accidental policy changes.

### 4. Redefine default readiness

For `precomputed_routing_packets`, `initialize` should validate that the packet set covers the topology, that every non-leaf packet contains a child dispatch table, and that the root packet is available for the start charter. After that validation, the run may move to `ready` without sending preparation mail or waiting for acknowledgements.

For `operator_preparation_wave`, readiness stays close to the current contract: targeted preparation recipients receive operator-origin preparation mail, and `require_ack` keeps the run in `awaiting_ack` until required replies arrive.

Rationale: `ready` should mean “the selected prestart strategy is complete,” not always “preparation mail was sent.”

Alternative considered: skip `initialize` entirely in the packet default. That would make `start` heavier and blur the existing v2 lifecycle vocabulary.

### 5. Keep operator preparation wave as an explicit mode

The old behavior remains useful when the operator wants early participant warmup, out-of-band acknowledgement, or explicit confirmation that non-leaf agents are ready before the master starts. In that mode, the existing target policy remains: delegating/non-leaf participants by default, leaves only when explicitly requested or named.

Rationale: the new default should simplify ordinary plans without losing the stronger preflight semantics for plans that need them.

Alternative considered: remove preparation mail entirely. That would break the enriched v2 use case that motivated `initialize` and `awaiting_ack`.

## Risks / Trade-offs

- **Packet size growth**: Non-leaf packets may carry child packet text, increasing prompt size. Mitigation: allow bundle plans to reference exact packet files, while requiring the start/edge handoff to include or unambiguously point at the exact packet to forward.
- **Stale packet drift**: A revised plan could leave old packets in place. Mitigation: require a plan revision or digest in every packet and fail closed on mismatch.
- **Mechanical forwarding mistakes**: A driver could append the wrong child packet. Mitigation: require intended recipient and immediate driver fields and require mismatch reporting instead of runtime repair.
- **Loss of warmup**: The default no longer contacts non-leaf agents before the master starts. Mitigation: keep `operator_preparation_wave` as an explicit strategy for warmup or acknowledgement-gated preflight.

## Migration Plan

1. Update v2 plan structure and templates to prefer `precomputed_routing_packets`.
2. Update authoring guidance to generate root and edge routing packets with dispatch tables.
3. Update `initialize` guidance so the default path validates packet completeness instead of sending preparation mail.
4. Update `start` and run-charter guidance so the master receives the root packet and forwards child packets through ordinary pairwise edge requests.
5. Retain the existing targeted preparation-wave guidance under the explicit `operator_preparation_wave` strategy.

## Open Questions

None.
