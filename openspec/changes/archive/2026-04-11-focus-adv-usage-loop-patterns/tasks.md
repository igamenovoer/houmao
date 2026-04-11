## 1. Top-Level Skill Boundary

- [x] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/SKILL.md` to describe the pairwise and relay pages as elemental protocol patterns.
- [x] 1.2 Update the multi-agent loop chooser to route composed topology, graph rendering, route/delegation policy, and run-control needs to dedicated loop-planning skills.

## 2. Pairwise Pattern Revision

- [x] 2.1 Revise `patterns/pairwise-edge-loop-via-gateway-and-mailbox.md` so the primary model is one driver, one worker, and one `edge_loop_id` for a two-node local-close round.
- [x] 2.2 Remove recursive child edge-loop, `parent_edge_loop_id`, and multi-edge graph-planning guidance from the elemental pairwise page.
- [x] 2.3 Preserve pairwise receipt, final-result, final-result acknowledgement, local `HOUMAO_JOB_DIR` ledger, mailbox-check-first retry, downstream-worker read-only peek-before-resend handling through `houmao-agent-inspect`, last-resort active status probing, timing-policy, supervisor reminder, and optional self-mail checkpoint guidance where it still applies to the elemental two-node round.

## 3. Relay Pattern Revision

- [x] 3.1 Revise `patterns/relay-loop-via-gateway-and-mailbox.md` so the primary model is one ordered N-node relay lane with one master/loop origin and one final egress.
- [x] 3.2 Remove fan-out, many-outbound-loop, multi-lane, and graph-of-loops guidance from the elemental relay page.
- [x] 3.3 Preserve relay handoff, receipt, final-result, final-result acknowledgement, local `HOUMAO_JOB_DIR` ledger, mailbox-check-first retry, downstream read-only peek-before-resend handling through `houmao-agent-inspect`, last-resort active status probing, timing-policy, supervisor reminder, and optional self-mail checkpoint guidance where it still applies to one ordered relay lane.

## 4. Validation

- [x] 4.1 Run `openspec validate focus-adv-usage-loop-patterns --strict`.
- [x] 4.2 Run the relevant project validation for packaged system-skill assets or targeted text checks around the revised advanced-usage skill pages.
