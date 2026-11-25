# Instructional Test Report: CCCC Receiver v2 Queue Rerun

Date: 2026-11-25 14:48 UTC | Overall Status: PASS | Mode: audit-cases

## Run Identity and Environment

- **Realwork checkout**: `/data/huangzhe/code/houmao` (branch `devel`, commit `555e4f2d693c95fcd7046baa7779e63e3ac009e8`, working tree dirty with audited instructional-bundle updates)
- **Enclosing metaproj**: none (standalone realwork)
- **Instructional output dir**: `/data/huangzhe/code/houmao/tests/instructional`
- **Case bundle**: `/data/huangzhe/code/houmao/tests/instructional/agent-cccc`
- **Project-local temp workspace**: `/data/huangzhe/code/houmao/tmp/instructional-tests/20261125T140656Z-agent-cccc-v2-queue`
- **Evidence root (verified post-cleanup)**: `tmp/instructional-tests/20261125T140656Z-agent-cccc-v2-queue/evidence/agent-cccc`
- **Temporary scripts used**: `scripts/run.env`, `scripts/run-context.json`, `scripts/run_queue_case.sh`
- **Harness and tool versions**: `houmao-mgr 3.0.0rc8`, `houmao-cccc 0.3.0`, DSH Web `0.2.2-rc.3`, self-hosted `Qwen/Qwen3.8-27B-FP8` with `xhigh`
- **Receiver environment**: isolated CCCC receiver protocol 2 at `127.0.0.1:18852`, upstream `d12732ebd6dfdbc260a59a286bd5e510d04d4832` plus four tracked patches, verified binary SHA-256 `a55d121555b794130ffd2065c97d8612cbc3637d721646e5716ddb69b924d71e`
- **Stand-in or environment deltas**: the suite used the documented local self-hosted Qwen lane and an isolated receiver-v2 service. No product behavior was mocked. The persistent v1 services on 8848/8849 and the prior interactive pair were not touched.

## Audit Outcome

**`changed`**

The earlier instructional bundle corrections were present, and additional drift was corrected for the new queue case and four-patch receiver. The live run validates the fixes for #101 and #102: `houmao-cccc --version` reports `0.3.0`, both agents used `members --group`, both agents used `chat deliveries --handle`, and their receipt identities matched the independent provider lookup.

## Summary Table

| Bundle / Scenario | Entry Point(s) Tested | Verdict | Triage | Doctor | Surviving Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agent-cccc/two-agent-chat-round-trip` | Managed DSH Web agents, gateway, CCCC chat | `PASS` | `none` | pass | `two-agent-chat-round-trip/` | Pull, handle receipts, Group assertion, accepted round trip |
| `agent-cccc/push-batch-replies-by-handle` | Managed DSH Web agents, timed push batch | `PASS` | `none` | pass | `push-batch-replies-by-handle/` | One fence, two handles, two exact-parent replies |
| `agent-cccc/busy-push-waits-for-idle` | Managed DSH Web agents, ASAP delivery | `PASS` | `none` | pass | `busy-push-waits-for-idle/` | Zero busy-time admission, later accepted delivery |
| `agent-cccc/gateway-queue-wait-and-read` | Managed DSH Web agents, in-turn gateway queue | `PASS` | `none` | pass | `gateway-queue-wait-and-read/` | Peek/pop/ack/result, gateway reads, next ordinary notification |
| `agent-cccc/gateway-reconnect-pending-delivery` | Managed DSH Web agents, detach/attach recovery | `PASS` | `none` | pass | `gateway-reconnect-pending-delivery/` | Same attempt `pending` to `accepted`, body preserved |

## Per-Case Details

### `agent-cccc/two-agent-chat-round-trip` - `PASS`

- **Preconditions & Doctor**: both agents healthy, idle, available, connected; pull delivery active.
- **Executed path**: Doctor, pull policy, operator asks A to delegate file-read work, both agents inspect receipt by handle, verifier checks request/reply ancestry and receipt identity.
- **Expected vs. observed**: request `ffc7e0d823c147b9a51273e392e4f0c2` used native handle `msg_cccc.CQ58yOedNe9tyIMf`, had one accepted attempt `ccded319-4240-4901-8c5d-2713f178172c`, and received reply `7328f32a5f574bbc8b6923e29e3fcf70` containing `cobalt desk-eb5785`. `receipt-identity-match.json` passed for the independent lookup plus both agent-saved receipts.
- **Read-only cross-check**: both agents successfully used `members --group` and `chat deliveries --handle`; the CLI version evidence reports `houmao-cccc 0.3.0`; no `cccc_cli_failed` or `reference_scope_error` occurred on the fixed path. The compact fence had one `msg_` handle and no private routing fields.
- **Artifacts**: `two-agent-chat-round-trip/` includes `cccc-version` at the run evidence root, `doctor.json`, `delivery.json`, `a-prompt.json`, `round-trip.json`, `native-request.json`, `a-send.json`, both agent receipt files, `receipt-identity-match.json`, `history.json`, `deliveries.json`, both transcript sets, and `channel-audit.json`.
- **Triage & follow-up**: none.

### `agent-cccc/push-batch-replies-by-handle` - `PASS`

- **Preconditions & Doctor**: both agents healthy and idle; timed push batch effective at 8-second quiet interval and 20-second maximum wait.
- **Executed path**: Doctor, set batch policy, A sends two requests in one shell call, verify both reply ancestry records and the native fence.
- **Expected vs. observed**: native message `7eba3374-784b-4c4a-8c6c-00dee5a749ac` had one fence with requests `3550587187a440e284c9a14b16ee3155` and `fa3413adafa148d580e9adb7763a0d11` in order. Handles `msg_cccc.x3T622hhEoN8M1pg` and `msg_cccc.LpRb2zOW1NjS-ltM` were distinct. Each request had one accepted attempt and one exact-parent reply.
- **Read-only cross-check**: both delivery lists contained `accepted`; the channel audit passed.
- **Artifacts**: `push-batch-replies-by-handle/` includes both reply/delivery proofs, `native-batch.json`, `history.json`, both transcript sets, and `channel-audit.json`.
- **Triage & follow-up**: none.

### `agent-cccc/busy-push-waits-for-idle` - `PASS`

- **Preconditions & Doctor**: both agents healthy; ASAP push active on B.
- **Executed path**: Doctor, set ASAP, run a real 60-second B shell turn, observe busy, prompt A, verify absence, wait for readiness, verify delayed delivery and reply.
- **Expected vs. observed**: B's native transcript had zero occurrences while busy. After readiness, request `3fd545d909c4483995fc3469f0678d5f` had one accepted attempt and reply `ca8c5b4fcd5b4514961d4c1dd1a96715` containing `busy-8d250a6ca4de`. The post-idle scan found the marker present.
- **Read-only cross-check**: the native request was compact with handle `msg_cccc.a7byYgCQhsHn0xwb`; channel audit passed.
- **Artifacts**: `busy-push-waits-for-idle/` includes busy/readiness observations, absence and presence scans, `round-trip.json`, `native-request.json`, transcripts, and audit.
- **Triage & follow-up**: none.

### `agent-cccc/gateway-queue-wait-and-read` - `PASS`

- **Preconditions & Doctor**: both agents healthy; B capabilities reported `chat_queue: true`; B used ASAP and A used batch for the staged queue scenario.
- **Executed path**: B yielded, A sent an ordinary request, B received and answered it, then B stayed in one turn to perform empty peek, send two requests, populate and pop a queue selection, acknowledge and recover the result, and send exact-parent confirmations. A sent another request while B was active; B released and received it as an ordinary notification.
- **Expected vs. observed**: `queue-proof.json` passed. The active turn was 8. The two staged peer replies recorded `gateway_tool_read` attempts `b436b9fc-00e9-48d6-bb71-0bcb4e5461c6` and `bcd096b8-4705-4883-a0bd-88a16bbb9cf2`, with confirmations `d7453a098f0644e99df0d20bc6355826` and `49184c33f0ec43008559ea4ea76f5add`. The yielded ordinary attempt `739efcdc-8294-43a4-8801-5a1a38b68b18` and follow-up attempt `8ab6958e-9fba-44f9-8bed-5ed63cb2db63` were accepted; the follow-up kept its attempt across release.
- **Read-only cross-check**: `empty.json`, `peek.json`, `pop.json`, `ack.json`, and `result.json` were preserved; no ordinary prompt carried the popped reply markers; channel audit passed.
- **Artifacts**: `gateway-queue-wait-and-read/` includes all queue JSON files, both ordinary round-trip proofs, both native request proofs, readiness/busy observations, transcripts, `queue-proof.json`, and audit.
- **Triage & follow-up**: none.

### `agent-cccc/gateway-reconnect-pending-delivery` - `PASS`

- **Preconditions & Doctor**: both agents healthy and idle; ASAP delivery active; B's gateway detached while its body remained alive.
- **Executed path**: Doctor, detach B, send A's request, verify pending and native absence, attach the same plugin selection, verify accepted recovery, and compare body/attempt identity.
- **Expected vs. observed**: attempt `623c432c-9a4f-4d8e-ad54-1032ded9b2f9` for event `785a6f5af1b9499196e032daa129f33d` moved from `pending` to `accepted`. The body snapshots matched, `attempt-continuity.json` passed, and reply `7c71dfd930b04ed69a2e6631537c11d8` contained `reconnect-dacb2351370e`.
- **Read-only cross-check**: B used the recovered handle `msg_cccc.vTSyJBwqvhe3SOGH`; post-reattachment Doctor and channel audit passed.
- **Artifacts**: `gateway-reconnect-pending-delivery/` includes both Doctor checks, detach/attach snapshots, `pending.json`, `round-trip.json`, `attempt-continuity.json`, `native-request.json`, presence/absence scans, transcripts, and audit.
- **Triage & follow-up**: none.

## Findings and Corrections

### `doc-drift`

- The queue case was added without the required `Sub-cases`, `How to get to it (user POV)`, and `Gotchas` sections. It now follows the four-section contract and documents queue-specific traps.
- The bundle introduction, top-level instructional index, helper table, and receiver self-proof did not reflect the queue case or the complete four-patch receiver. They now do.
- The launch guide now records `houmao-cccc --version`, and the correspondent role directs both agents to use `members --group` with the brief's Group ID.

### `harness-gap`

- `cccc_lab.py` verified only three receiver patches. It now requires `0004-gateway-queue-reads.patch` as well.
- The helper's default manager/plugin fallback pointed at uv tool binaries. It now defaults to the workspace Pixi binaries, matching the guide.
- The queue case's native proof and schema were aligned with the queue implementation and `verify_queue_access.py`.

### `product-regression`

None observed. Both fixed CLI issues passed live: version output, Group assertion, handle-based receipt lookup, and fixed error paths on the exercised route.

### Residual usability observation

- Agent B once invoked `chat deliveries --handle CQ58yOedNe9tyIMf`, omitting the `msg_cccc.` prefix from the exact handle in the request fence. The CLI returned `invalid_message_handle` with the generic guidance `Use the exact message handle.` B recovered on the next call, but the message does not show the expected handle shape. Adding a safe format example such as `msg_<instance>.<token>` to that error would make the failure immediately self-correcting. This did not affect the passing queue or receipt evidence.

## Cleanup Verification

- **Stopped/removed**: both agents stopped, both private tmux sockets killed, both grants revoked, the Group deleted and verified absent, both external credential files deleted, the private run directory absent, and the four-patch receiver PID stopped with port `18852` closed.
- **Preserved**: 121 evidence files remain under `tmp/instructional-tests/20261125T140656Z-agent-cccc-v2-queue/evidence/agent-cccc/`; all five channel audits are `passed`.
- **Residual items**: none from this run. The existing v1 services and the earlier interactive pair were left untouched.

## Unverified Scope and Next Steps

- Coverage remains limited to the self-hosted Qwen lane, DSH Web, loopback CCCC receiver protocol 2 with all four patches, and CCCC chat. Other clients, remote CCCC deployments, provider crash/restart beyond gateway reattachment, and CCCC Mail remain outside this run.
- Product code was not edited during this rerun. The surviving working-tree changes are limited to the instructional bundle and its top-level index.
- Next step: review and commit the instructional-bundle corrections separately from any follow-up product work.
