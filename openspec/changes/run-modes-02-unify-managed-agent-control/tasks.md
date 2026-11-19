# Tasks

## 1. Share Owner Routing and Admission

- [ ] 1.1 Define the runtime operation and capability contract over the mode and backend from 01. Add contract cases for semantic prompt, interrupt, state/events, usage, lifecycle, and unsupported raw input; check each adapter returns its evidence source.
- [ ] 1.2 Route manager post-launch and protected gateway mutations through the verified owner and one admission decision. Race the public manager and gateway against the same agent and assert a single native handoff.
- [ ] 1.3 Keep manager-side owner inspection, stop, and relaunch reachable through the saved execution route. Test gateway outage, stale generations, unreachable routed owners, and absence of fallback to a local namesake.
- [ ] 1.4 Update the manager and gateway API reference with one authenticated prompt and one gateway-down lifecycle example. Exercise those commands and confirm public handoff responses exclude private authority.

## 2. Carry Evidence Through Existing Consumers

- [ ] 2.1 Represent queued, native handoff, terminal, failed, and uncertain outcomes using existing request and event storage. Test caller loss and post-admission disconnect with no replay or fabricated completion.
- [ ] 2.2 Preserve ordinary mail/plugin ready-only delivery and explicitly deferred semantics. Run gateway tests covering a busy human turn, unchanged mailbox storage, and an expired dispatch permission.
- [ ] 2.3 Project compact and detailed passive state by recorded mode, and map only correlated AG-UI events into a run. Exercise actual TUI, headless and DSH Web projections plus a stub service with a dead connection and a live supervisor.
- [ ] 2.4 Update state and AG-UI API examples with evidence freshness, unsupported operations, and surface-specific fields. Validate responses against the public route models and check the TUI detail link remains canonical.

## 3. Qualify the Existing Modes End to End

- [ ] 3.1 Exercise owner-side manager plus authenticated gateway prompt, observation and supported interruption for one native headless tool, a TUI, and DSH Web. Verify a detached gateway can reattach to the same agent with bounded results for each mode.
- [ ] 3.2 Exercise the same flow through a saved executor route and through the passive reader. Run the affected gateway, registry, passive-server, and AG-UI suites under Pixi using isolated tmux for supervised cases.
