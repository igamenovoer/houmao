# Tasks

## 1. Own the Persistent Service

- [x] 1.1 Add a per-agent service owner under the existing execution-context supervisor. Stand up a private local client channel and verify that two independent controller processes reach one native child with the same service incarnation.
- [x] 1.2 Reuse the owner reservation and request ID from change 02. Persist service incarnation, native session, and current operation at the admission and handoff boundaries. Fault-inject process loss before write, after admission, and before settlement. Assert active or uncertain state and no replay.
- [x] 1.3 Implement continuous bidirectional reading, private stderr collection, bounded reverse-request handling, and targeted cancellation. Use a deterministic peer to test interleaved updates, permissions, late replies, and an interrupt racing the next request.
- [x] 1.4 Integrate authenticated attach, stop, explicit relaunch, and exact native resume with the owner route. Document the service lifetime and private connection boundary; test detached gateway, stale channel or PID, dead provider, and owner-only cleanup on an isolated tmux server.

## 2. Implement Persistent DSH ACP

- [x] 2.1 Move reusable ACP framing and permission handling out of the per-turn closure path and register `dsh_acp` for `(dsh, service)`. Verify real native initialization and exact session selection before readiness and two consecutive prompts in the same process.
- [x] 2.2 Route prompt, `session/update`, permission decisions, `session/cancel`, terminal status, and private diagnostics through the shared owner. Exercise immediate gateway dispatch, bounded native cancellation, unsupported reverse requests, and a stale update arriving after a new turn.
- [x] 2.3 Qualify private home, role, MCP session binding, unattended permission presets, and session-scoped setting restore. Inject failure on set, cancellation and restore; verify the next turn sees the prior model or receives a truthful unavailable result.
- [x] 2.4 Update native refresh and DSH service documentation with verified read boundaries per resource and explicit relaunch requirements. On a live service, edit skills and MCP separately and compare observed state before and after the actual native boundary.

## 3. Qualify DSH Service Lifecycle

- [x] 3.1 Test public manager and gateway prompt, state, usage, idle attachment, mail/plugin wake, owner stop and exact cold resume with DSH `0.2.2-rc.3` against self-hosted `Qwen/Qwen3.8-27B-FP8`. Record process, incarnation, session, request, and journal identities with private test artifacts.
- [x] 3.2 Restart the gateway and passive observer during native work, then simulate loss of the service owner. Verify the former preserve the original operation and the latter fences the obsolete service, reconciles evidence, and refuses automatic resend.
- [x] 3.3 Run the service, DSH, gateway, and refresh suites under Pixi with an isolated tmux server. Record the actual build and selected model and verify the fixture identifies `service` as the tested mode.

## Workflow Follow-up

- Release the coordinated DSH cutover after 01 through 04 have passed. The implementation sequence reviews this change after 03's native headless verification.
