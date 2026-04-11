## Context

`houmao-agent-loop-relay` currently packages a complete relay-specific planning and run-control skill. It owns relay plan authoring, route policy, result-return contracts, Mermaid relay graphs, and `start`/`status`/`stop` control while composing lower-level messaging, gateway, mailbox, and advanced-usage guidance.

Recent changes intentionally narrowed `houmao-adv-usage-pattern` so its pairwise and relay pages are elemental protocol pages only. That leaves a clean layer above them: a planner that can decompose an arbitrary user-requested communication graph into typed protocol components instead of forcing the whole graph into the relay vocabulary. The existing relay skill is the right asset family to replace because it already owns graph planning and run control, but its name and internal model are now too narrow.

## Goals / Non-Goals

**Goals:**

- Rename the packaged relay-only planning skill to `houmao-agent-loop-generic`.
- Make the new skill responsible for generic multi-agent loop graph decomposition, rendered graphs, run charters, and `start`/`status`/`stop` run control.
- Require the generic plan to decompose the graph into explicitly typed components:
  - `pairwise`: an immediate driver-worker local-close edge that uses the elemental pairwise edge-loop protocol.
  - `relay`: a relay-rooted ordered lane that uses the elemental relay-loop protocol.
- Keep the user agent outside the execution loop and keep accepted-run liveness on the designated master/root run owner.
- Update catalog and documentation surfaces so the current packaged skill is `houmao-agent-loop-generic`, not `houmao-agent-loop-relay`.

**Non-Goals:**

- No compatibility alias for `houmao-agent-loop-relay`.
- No new runtime loop engine or new transport protocol.
- No rewrite of `houmao-agent-loop-pairwise` or `houmao-agent-loop-pairwise-v2` beyond any references needed to point at the generic planner.
- No expansion of `houmao-adv-usage-pattern` back into graph planning; it remains elemental protocol guidance.

## Decisions

### 1. Hard rename instead of aliasing

The implementation will rename the asset directory, skill metadata, catalog key, and docs/spec references from `houmao-agent-loop-relay` to `houmao-agent-loop-generic`.

Rationale: the repository is in active unstable development, and the relay name now communicates the wrong scope. An alias would preserve the confusion and would require more catalog/docs support for a deprecated entrypoint.

Alternative considered: keep `houmao-agent-loop-relay` and broaden its description. That would make mixed pairwise/relay planning look like a relay-only feature and would conflict with the new elemental relay boundary.

### 2. Typed component model

The generic plan will describe the communication graph as a set of components. Each component must declare at least:

- `component_id`
- `component_type`: `pairwise` or `relay`
- participating agents and the component root/driver/origin
- downstream targets or lane order
- result-return contract
- policy for delegation or routing
- dependencies on other components, if any

Pairwise components model local-close delegation: the final result for the component returns to the immediate driver. Relay components model forward ownership: the final egress returns to the relay origin.

Rationale: this keeps protocol-specific state and IDs in their elemental protocols while letting the generic planner reason about the whole user-requested graph.

Alternative considered: a single free-form graph with edge labels. That would be flexible but too easy for agents to invent undocumented message routing. Typed components make the allowed protocol choice explicit and reviewable.

### 3. Generic graph policy replaces route-only policy

The old relay `route-policy.md` should become a generic graph/component policy reference. It should cover:

- pairwise delegation authority (`delegate_none`, `delegate_to_named`, `delegate_freely_within_named_set`, `delegate_any`)
- relay routing authority (`fixed_route_only`, `forward_to_named`, `forward_freely_within_named_set`, `forward_any`)
- component dependency rules
- when missing policy requires asking the user instead of inventing free delegation or forwarding

Rationale: generic plans need one policy surface that can normalize both protocol families without hiding their differences.

### 4. Generic graph rendering

The graph page should render typed components and result paths instead of a relay-only lane. The rendered graph should show:

- user agent as control-only
- designated master/root run owner
- pairwise component edges with local-close result return to the immediate driver
- relay component lanes with final-result return to the relay origin
- component dependencies
- supervision loop, completion condition, and stop condition

Rationale: graph rendering is where agents are most likely to collapse pairwise and relay into one arbitrary cycle. The graph should make the protocol type visible per component.

### 5. Run control remains master-owned

The generic skill keeps the `start`, `status`, and `stop` operating lane. The user agent sends a normalized charter to the designated master/root owner, then the master owns liveness, component dispatch, status reporting, completion evaluation, and stop handling.

Rationale: this preserves the existing relay skill’s control-plane boundary and matches the pairwise planner boundary: user agent outside the execution loop, root owner responsible after acceptance.

## Risks / Trade-offs

- **Risk: generic planner becomes too broad and overlaps pairwise-v2.** Mitigation: keep `houmao-agent-loop-pairwise-v2` as the explicit enriched pairwise-only skill; generic plans may include pairwise components but do not inherit v2 lifecycle verbs such as `initialize`, `peek`, `ping`, `pause`, `resume`, or `hard-kill`.
- **Risk: agents may still treat `houmao-adv-usage-pattern` as graph planning.** Mitigation: update advanced-usage chooser text so composed topology, mixed graph planning, graph policy, and run control route to `houmao-agent-loop-generic`.
- **Risk: docs/spec catalog drift after hard rename.** Mitigation: implementation tasks must update catalog, README, docs overview, CLI reference, and OpenSpec specs in the same change.
- **Risk: relay-only users lose an obvious entrypoint.** Mitigation: generic authoring should treat a pure relay request as one relay component and preserve relay-root semantics in the generated plan.
