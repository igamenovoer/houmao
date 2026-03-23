## 1. Pack Skeleton And Fixture Wiring

- [x] 1.1 Create `scripts/demo/mail-ping-pong-gateway-demo-pack/` with a thin `run_demo.sh`, `scripts/demo_driver.py`, tracked inputs, helper-script skeleton, and `expected_report/report.json`.
- [x] 1.2 Create `src/houmao/demo/mail_ping_pong_gateway_demo_pack/` with `driver.py`, `models.py`, `server.py`, `agents.py`, `events.py`, and `reporting.py`.
- [x] 1.3 Implement demo layout resolution so `--demo-output-dir` defaults to the pack-local `outputs/` root and relative paths resolve from the repository root.
- [x] 1.4 Implement output-root environment redirection for Houmao runtime, registry, mailbox, and local jobs roots so all generated state stays under the selected output root.
- [x] 1.5 Reuse the tracked dummy-project fixture family to provision `projects/initiator/` and `projects/responder/`, and wire default `AGENT_DEF_DIR` resolution to `tests/fixtures/agents`.
- [x] 1.6 Add tracked `mail-ping-pong-initiator` and `mail-ping-pong-responder` role packages and define the minimum `demo_state.json` field contract in `models.py`.

## 2. Server And Participant Bootstrap

- [x] 2.1 Implement demo-owned `houmao-server` startup with free loopback port selection, a server-private runtime root under `outputs/server/`, bounded health polling, and persisted server ownership metadata.
- [x] 2.2 Implement brain-build bootstrap from the tracked Claude and Codex `mailbox-demo-default` recipes and launch the two managed headless participants with explicit role names and copied workdirs.
- [x] 2.3 Implement gateway attach and mail-notifier enablement for both participants, plus notifier disable and re-enable flows for `pause` and `continue`.
- [x] 2.4 Persist the selected API base URL, participant identities, manifest paths, and other startup results into `control/demo_state.json`.

## 3. Conversation, Inspection, And Verification

- [x] 3.1 Implement thread-key generation, the kickoff prompt template, and the round metadata contract for the initiator and responder workflow.
- [x] 3.2 Implement bounded `wait` polling with visible progress updates and explicit timeout or incomplete diagnostics.
- [x] 3.3 Implement normalized conversation-event capture with the required stable fields and any available request, turn, message, and gateway linkages.
- [x] 3.4 Implement `inspect` to write `control/inspect.json` using the agreed minimum state, gateway, and progress summaries.
- [x] 3.5 Implement `report.json`, `report.sanitized.json`, and snapshot-refresh helpers that assert one-thread, ten-message, eleven-turn success without depending on exact notifier poll counts.
- [x] 3.6 Implement idempotent stop and cleanup behavior for partial runs so agents and the demo-owned server are torn down without losing run artifacts.

## 4. Documentation And Coverage

- [x] 4.1 Write the demo-pack README covering prerequisites, tracked fixture sources, the headless-first workflow, stepwise commands, the kickoff and thread contract, bounded wait behavior, the `outputs/` ownership model, and the explicit v1 autotest deferral.
- [x] 4.2 Add pytest-based regression coverage for startup defaults, output-root containment, persisted-state resumability, and successful completion plus report sanitization.
- [x] 4.3 Add pytest-based regression coverage for pause and continue behavior together with wait timeout and incomplete-run diagnostics.
