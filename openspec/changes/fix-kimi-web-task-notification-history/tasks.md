# Tasks

## 1. Correct Native Observation and Correlation

- [x] 1.1 Extend the existing Kimi Web backend fixture with a completed managed turn followed by a native task-origin turn and its completion. Use synthetic journal rows carrying the exact same colon-bearing prompt ID at start and settlement. Show that projection succeeds up to the notification and fails on the unpatched reader when that row is included. The fixture must run without any retained run files.
- [x] 1.2 Separate journal prompt identity from component validation in the Kimi adapter. Verify passive state and incremental history preserve the exact native ID, original byte offsets, and completed turn across repeated reads, including an initial read of a journal already containing the notification. Check that observation issues only passive requests.
- [x] 1.3 Exercise admission and managed attribution with the real Kimi projection through the gateway Web observer. Confirm the binding stays available while busy, becomes ready only after native work and interactions clear, and the notification cannot supply output or terminal evidence for an unrelated managed attempt. Include an absent or mismatched native authority case that still closes admission.

## 2. Preserve Exact Targets at the HTTP Boundary

- [x] 2.1 Update targeted interruption to encode the verified native prompt ID once as a single segment, with the action suffix outside it. Extend the existing interrupt test to check the wire target and its decoded ID for a task notification and a literal percent sequence. Verify an ordinary managed ID still yields its existing route.
- [x] 2.2 Check that a stale turn, wrong session or host, and mismatched managed operation all refuse before sending an abort. Confirm that a native refusal of an exact-target abort surfaces as a refusal without retargeting. Run `pixi run pytest -q tests/unit/agents/test_kimi_web_backend.py` with the gateway-observation regressions from group 1.

## 3. Verify the End-to-End Handoff

- [x] 3.1 Use the [busy-recipient instructional case](../../../tests/instructional/agent-cccc/cases/busy-push-waits-for-idle.md) to exercise one genuine Kimi Web task notification and one separately identifiable CCCC message. Capture the pending message while the recipient is busy, the notification’s native terminal record, the subsequent ready state on the same binding, one accepted sender receipt, and exactly one corresponding recipient input. Let normal push delivery complete without an operator resend, queue pop, or reattachment.
