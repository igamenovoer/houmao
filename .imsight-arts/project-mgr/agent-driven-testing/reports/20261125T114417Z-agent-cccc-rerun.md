# Instructional Test Report: agent-cccc Receiver v2 Rerun

Date: 2026-11-25 11:53 UTC | Overall Status: PASS | Mode: audit-cases

## Run Identity and Environment

- **Realwork checkout**: `/data/huangzhe/code/houmao` (branch `devel`, commit `437fe2f95c1e4cb8dd0c8816d513e195d68e901b`, working tree dirty with the audited instructional-bundle revisions plus concurrent documentation/OpenSpec edits not authored by this run)
- **Enclosing metaproj**: none (standalone realwork)
- **Instructional output dir**: `/data/huangzhe/code/houmao/tests/instructional`
- **Case bundle**: `/data/huangzhe/code/houmao/tests/instructional/agent-cccc`
- **Project-local temp workspace**: `/data/huangzhe/code/houmao/tmp/instructional-tests/20261125T114417Z-agent-cccc-v2`
- **Evidence root (verified post-cleanup)**: `tmp/instructional-tests/20261125T114417Z-agent-cccc-v2/evidence/agent-cccc`
- **Temporary scripts used**: `scripts/run.env`, `scripts/run-context.json`, and `scripts/verify-protocol-usage.py`
- **Harness and tool versions**: `houmao-mgr 3.0.0rc8`, `houmao-cccc 0.3.0`, DSH Web `0.2.2-rc.3`, self-hosted `Qwen/Qwen3.8-27B-FP8` with `xhigh`
- **Receiver environment**: isolated CCCC receiver protocol 2 at `127.0.0.1:18851`, upstream `d12732ebd6dfdbc260a59a286bd5e510d04d4832` plus all three tracked patches, verified binary SHA-256 `160600a9585a1263e5df7bf5b723773b8299b1f0d0882031f44bd499b7984797`
- **Stand-in or environment deltas**: the suite used the documented local self-hosted Qwen lane and an isolated receiver-v2 service. No product source behavior was mocked. The persistent v1 CCCC services on 8848 and 8849 and the earlier interactive pair were not touched.

## Audit Outcome

**`changed`**

Issue #100 behavior is implemented and passed live: incoming chat is a compact fenced request carrying sender, timestamp, mode, body, and a scoped handle; sends use a current connection token; replies use the exact delivered handle. Proven corrections were limited to the instructional bundle plus its top-level index.

## Summary Table

| Bundle / Scenario | Entry Point(s) Tested | Verdict | Triage | Doctor | Surviving Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `agent-cccc/two-agent-chat-round-trip` | Managed DSH Web agents, gateway, CCCC chat | `PASS` | `none` | pass | `two-agent-chat-round-trip/` | Pull transport, compact single request, handle reply, accepted handoff |
| `agent-cccc/push-batch-replies-by-handle` | Managed DSH Web agents, gateway, timed push batch | `PASS` | `none` | pass | `push-batch-replies-by-handle/` | One fence, two ordered handles, two exact-parent replies |
| `agent-cccc/busy-push-waits-for-idle` | Managed DSH Web agents, gateway, ASAP delivery | `PASS` | `none` | pass | `busy-push-waits-for-idle/` | Zero busy-time admission, later accepted delivery and reply |
| `agent-cccc/gateway-reconnect-pending-delivery` | Managed DSH Web agents, gateway detach/attach, receiver recovery | `PASS` | `none` | pass | `gateway-reconnect-pending-delivery/` | Same attempt moved `pending` to `accepted`; body preserved |

## Per-Case Details

### `agent-cccc/two-agent-chat-round-trip` - `PASS`

- **Preconditions & Doctor**: Both agents were healthy, idle, available, and connected; pull delivery was effective and active.
- **Executed path**: Doctor, set B to pull, prompt A to delegate a file read through one CCCC `request_reply`, verify the round trip, and verify the compact native request.
- **Expected vs. observed**: Request `7d05b5da27c840ba824eab9cad9f9ee8` used native handle `msg_cccc.5_m-LM8MDhvjRjeh` and had one accepted attempt. Reply `299dbe5604924fe8a13b834836d3b9ee` contained `cobalt desk-304acb` and named the request as its exact parent.
- **Read-only cross-check**: The native request contained one fenced `request_reply` entry with no binding ID, event ID, signed event reference, connection token, or repeated gateway URL. A used a current connection token for the send; B used the exact handle for the reply without a connection token. The channel audit passed.
- **Artifacts**: `two-agent-chat-round-trip/` includes `doctor.json`, `delivery.json`, `a-prompt.json`, `round-trip.json`, `native-request.json`, `history.json`, `deliveries.json`, both transcript sets, `channel-audit.json`, and `gateway-protocol-usage.json`.
- **Triage & follow-up**: none.

### `agent-cccc/push-batch-replies-by-handle` - `PASS`

- **Preconditions & Doctor**: Both agents were healthy and idle; timed push batch was effective at quiet interval 8 seconds and maximum wait 20 seconds.
- **Executed path**: Doctor, set B to `push/batch`, prompt A to send two requests in one shell call, then verify each ancestry and the one-fence native batch.
- **Expected vs. observed**: Native message `e1d584de-3be4-4086-b3e4-9c1581ccf1bd` contained exactly one fence with requests `8a78c0f64d92480da53c17e671310567` and `dfaceba2adf644cda9a75c85e17c6a91` in CCCC order. Handles `msg_cccc.Q2m8CSBeSt0FUzX3` and `msg_cccc.gYMtPUrkNvaqV4jp` were distinct. Each request had one accepted attempt and one exact-parent reply.
- **Read-only cross-check**: A passed one current connection token with both sends. B replied successfully through each exact delivered handle without a connection token. The channel audit passed.
- **Artifacts**: `push-batch-replies-by-handle/` includes `delivery.json`, `a-prompt.json`, both reply and delivery proofs, `native-batch.json`, `history.json`, both transcript sets, `channel-audit.json`, and `gateway-protocol-usage.json`.
- **Triage & follow-up**: none.

### `agent-cccc/busy-push-waits-for-idle` - `PASS`

- **Preconditions & Doctor**: Both agents were healthy; ASAP push was effective on B before the busy turn.
- **Executed path**: Doctor, start a real 60-second shell turn on B, observe real busy state, prompt A to send, verify token absence while busy, wait for readiness, and verify delayed delivery.
- **Expected vs. observed**: B's transcript had zero occurrences of `busy-245ca831dde8` while busy. After the turn ended, request `9dba5e6ddf144e548db128b5b9f348cc` had one accepted handoff and reply `14acccdab7a84f0aa6442cb37f3eb783`. The later transcript scan found the token present.
- **Read-only cross-check**: The delayed native request was one compact fenced entry with handle `msg_cccc.en5tp1qjfxrECFw0`; A used a connection token for the send and B used the delivered handle for the reply. The channel audit passed.
- **Artifacts**: `busy-push-waits-for-idle/` includes `delivery.json`, both busy prompt and observation files, `a-prompt.json`, busy-time absence proof, readiness proof, `round-trip.json`, `native-request.json`, post-idle presence proof, both transcript sets, `channel-audit.json`, and `gateway-protocol-usage.json`.
- **Triage & follow-up**: none.

### `agent-cccc/gateway-reconnect-pending-delivery` - `PASS`

- **Preconditions & Doctor**: Both agents were healthy and idle; ASAP push was effective before detaching B's gateway.
- **Executed path**: Doctor, detach B, prompt A to send, verify pending while detached and native absence, attach the same plugin selection, verify accepted recovery, then verify attempt/body continuity.
- **Expected vs. observed**: Before attachment, attempt `fa2174e9-5536-4db3-84a9-74bac968a0ea` for event `600dc89dca1842b4a9b47f0938bd7620` was `pending` and absent from B. After attachment, the same attempt and event were `accepted`; the body snapshot was unchanged. B minted fresh handle `msg_cccc.ZukvRl9dYXiVHvRX` and reply `64e343f5d6d0470da992da130a0bef99` named the original event as parent.
- **Read-only cross-check**: The run used no `chat retry`. The post-reattachment channel audit and Doctor passed. A used a connection token; B used the recovered handle without a connection token.
- **Artifacts**: `gateway-reconnect-pending-delivery/` includes both Doctor checks, `delivery.json`, detach/attach body snapshots, `pending.json`, detached absence proof, `round-trip.json`, `attempt-continuity.json`, `native-request.json`, post-reattachment presence proof, readiness checks, both transcript sets, `channel-audit.json`, and `gateway-protocol-usage.json`.
- **Triage & follow-up**: none.

## Findings and Corrections

### `doc-drift`

- The three new scenario files lacked the required `Sub-cases`, `How to get to it (user POV)`, and `Gotchas` sections. They now follow the four-section contract and preserve the existing user-visible journey.
- The bundle did not pin effective pull, batch, or ASAP policy in every scenario. Each case now sets and records its own policy.
- The round-trip case did not prove the compact request fence or pull transport. It now saves both proofs.
- The launch guide still defaulted to the uv tool environment and v1 receiver paths. It now selects matching workspace Pixi binaries and the protocol-v2 receiver root.
- The launch did not select the intended reasoning level. Both profiles are now set to level 3, and the live native patches report `xhigh`.
- The top-level `tests/instructional/README.md` index still described refusal/retry and no-replay behavior. It now describes push batching, busy waiting, and reconnect recovery.

### `harness-gap`

- `matching_events` treated a later ordinary sender acknowledgement containing the same marker as a second request. It now counts only `request_reply` events as requests.
- `verify-batch` now selects only fences containing the target `request_reply` entries and rejects binding IDs, event IDs, signed event references, connection tokens, and repeated gateway URLs in the model-facing request.
- `verify-batch` was exercised synthetically with a request fence plus a later acknowledgement fence and selected only the request.
- Service identity validation now requires all three tracked receiver patches, including queued receiver v2, instead of checking only the first patch.
- The correspondent role now distinguishes send-time `--connection-token` from reply-time `--handle`; replies do not accept or require a connection token.

### `product-regression`

None observed. Issue #100's compact message-handle and token-based send contract worked on all four live paths.

## Observed Agent-Facing Usability Issues

These did not block any scenario, but Agent A needed five failed CLI probes in the first case before completing the round trip. Agent B had zero CLI usage errors.

- **Delivery inspection still requires long, error-prone targets.** `chat deliveries` in gateway mode requires the scoped `--event-ref`, but the shared command help also advertises `--event-id`, which is direct-mode-only. The gateway-mode mismatch is converted to the generic `cccc_cli_failed`. In the live transcript, A also mistyped the 32-character event ID and received `reference_scope_error`; the current message/reply path uses short handles, but receipt inspection does not. A handle-based receipt lookup, or a short receipt target returned with the message, would remove this copy step.
- **Mode-specific target rules are not visible in help.** The parser advertises both target flags before the CLI knows whether it is in gateway or direct mode. Help or errors should state that gateway mode requires `--event-ref` and direct mode requires `--event-id`.
- **Safe failure detail is still lost.** The CLI maps argument/build failures to `cccc_cli_failed`, while the provider's scoped reference mismatch returns `reference_scope_error` without recovery guidance. This confirms the error-actionability concern already tracked in issue #99.
- **Group scoping invites an unsupported flag.** Agent A tried `members --group <group_id>` even though the binding already fixes the Group. The CLI rejected it through normal argparse. Accepting and validating a matching Group value, or showing that Group selection is implicit, would make actor discovery less trial-driven.
- **The CLI has no version selector.** `houmao-cccc --version` exits with the generic command-required error. Test and operator tooling must inspect installed package metadata instead.

The compact receive contract itself was clear: B needed no CLI discovery to understand the fenced request, and all successful replies used the exact delivered handle.

## Cleanup Verification

- **Stopped/removed**: Both run-owned managed agents stopped. Private tmux sockets for both agents were killed. Both CCCC grants were revoked and both external credential documents were deleted. The run Group was deleted and verified absent. The private run directory was verified absent. The isolated receiver-v2 process PID `484460` was stopped and port `18851` is closed.
- **Preserved**: All 84 evidence files remain under `tmp/instructional-tests/20261125T114417Z-agent-cccc-v2/evidence/agent-cccc/` and were enumerated in `evidence-check.txt`.
- **Residual items**: none from this run. Existing user-owned v1 CCCC services and the earlier interactive pair were deliberately left untouched.

## Unverified Scope and Next Steps

- This run covers only the self-hosted Qwen lane, DSH Web, loopback CCCC receiver protocol 2, and push/pull chat delivery. Other clients, remote CCCC deployments, provider crash/restart beyond gateway reattachment, and CCCC Mail remain outside this verification.
- Product code was not edited. The audited changes are confined to `tests/instructional/agent-cccc/`, `tests/instructional/README.md`, and the test helper/role files.
- Concurrent working-tree changes outside the test bundle (`docs/reference/gateway/cccc.md`, `openspec/specs/cccc-gateway-binding/spec.md`, and `openspec/changes/add-cccc-gateway-queue-access/`) were not authored by this run and were left untouched.
- Next step: review and commit the instructional-bundle corrections separately from the concurrent product-documentation/OpenSpec work.
