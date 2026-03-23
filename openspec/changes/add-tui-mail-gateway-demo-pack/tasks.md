## 1. Pack Skeleton And Startup Flow

- [ ] 1.1 Create `scripts/demo/tui-mail-gateway-demo-pack/` with `README.md`, `run_demo.sh`, tracked inputs, helper wrappers, and `expected_report/report.json`.
- [ ] 1.2 Create `src/houmao/demo/tui_mail_gateway_demo_pack/` with backing modules for command routing, persisted state, runtime startup or teardown, mailbox harness helpers, and reporting.
- [ ] 1.3 Implement tool-selected startup so `start` and `auto` require `--tool claude|codex`, resolve the tracked `mailbox-demo` fixture family, and persist the selected tool in `control/demo_state.json`.
- [ ] 1.4 Implement copied dummy-project provisioning plus output-root environment redirection so runtime, registry, mailbox, jobs, deliveries, and evidence all stay under the selected demo output root.
- [ ] 1.5 Implement mailbox-enabled `cao_rest` session startup, live gateway attach, and mail-notifier enablement for the selected tool using the existing runtime CLI flow.

## 2. Harness Drive Loop And Evidence

- [ ] 2.1 Implement the persisted harness state model for run id, selected tool, delivery count, processed-turn count, and per-turn delivery metadata.
- [ ] 2.2 Implement the five-second `drive` loop so it checks unread state and gateway execution eligibility, injects one new mail only when the gating contract is satisfied, and stops after three processed turns.
- [ ] 2.3 Implement managed mailbox delivery helpers that stage and deliver the tracked turn messages without direct SQLite mutation.
- [ ] 2.4 Implement per-turn state detection so processed-turn completion is recognized from message read transitions and linked back to the injected message id.
- [ ] 2.5 Capture bounded human-review TUI evidence for each processed turn, such as tmux pane snapshots or best-effort projected output tails, and persist those artifacts under the demo output root.

## 3. Inspect, Verify, And Stop

- [ ] 3.1 Implement `inspect` so it writes machine-readable snapshots covering selected tool, session identity, gateway state, notifier audit summary, mailbox unread state, harness progress, and TUI review evidence.
- [ ] 3.2 Implement `report.json`, `report.sanitized.json`, and verification helpers so the stable contract checks three injected messages, three processed read transitions, and final unread count zero without exact transcript assertions.
- [ ] 3.3 Implement the `auto` workflow as `start -> drive -> inspect -> verify -> stop`.
- [ ] 3.4 Implement idempotent `stop` and cleanup behavior for partial runs, including notifier disablement, session stop, and preservation of run artifacts for diagnosis.

## 4. Documentation And Coverage

- [ ] 4.1 Write the pack README covering the single-agent TUI wake-up goal, explicit tool selection, five-second unread-gated harness loop, three-turn success rule, command surface, output-root ownership, and human-review TUI evidence posture.
- [ ] 4.2 Add deterministic regression coverage for tool-selected startup, output-root containment, harness gating, per-turn artifact generation, and sanitized verification behavior.
- [ ] 4.3 Add regression coverage for stepwise state reuse and stop or cleanup behavior after incomplete or partial runs.
