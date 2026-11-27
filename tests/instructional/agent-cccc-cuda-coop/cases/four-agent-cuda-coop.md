# Spontaneous CCCC Chat During GDN Prefill Optimization

The tester asks four independent Qwen 3.8 peers to optimize Gated Delta Net prefill. Use the default problem to find out whether a message a peer chooses to send reaches the intended teammate during normal CUDA work.

## Sub-cases

- **Default launch.** Four peers receive the same GDN starter, permissions, and kernel assignment in separate working directories.
- **First delivery and subsequent traffic.** Trace the first attempted send, then account for every subsequent attempt until the deadline, including retries and sends to busy peers if they occur.
- **Cutoff.** Preserve the communication evidence and the available GDN implementations at five minutes, including when all four peers are silent.

## How to get to it (user POV)

Leave `PROBLEM_ID` unset and follow Launch and Doctor. Choose the same Web pool entry for all four peers. Each private system prompt expresses a different personality and research preference. The tester submits the common kernel task once to each peer and watches. [Launch](../README.md#launch) · [Doctor](../README.md#doctor)

## Driving it with cuda_coop_lab

1. Confirm the default selection with `jq -e '.selected_problem == "gdn_prefill" and .problem_override == null' "$EVIDENCE/manifest-resolved.json"`. Check the four physical workdirs in `configure.json` and the four ready bindings in `doctor.json`.
2. Run `pixi run python "$LAB" run-window --run-meta "$RUN_META"` as shown in Drive. Any peer can speak first, ask a question, reply, continue independently, or stay silent. Keep the original deadline through idle or busy intervals. [Drive](../README.md#drive)
3. At cutoff collect before teardown. Cross-check sender tool results and CCCC event IDs against delivery attempts and recipient input fences or consuming tool results. Save the route counts and the location of the first confirmable handoff. Follow Cleanup for the independent CUDA build. [Evidence](../README.md#evidence) · [Cleanup](../README.md#cleanup)

## Expected Outcome

**Quantified checks**

- Four distinct sessions and actor bindings join one group using `Qwen/Qwen3.8-27B-FP8`. Four copies of the GDN starter have the same initial hash. Four native journals show one identical tester kickoff apiece. The recorded window spans exactly 300 seconds. Count zero tester discussion messages, nudges, relays, or consuming queue operations.
- Apply the recipient-level checks to all attempted chat. Report confirmed, attempted, and unexercised directed routes out of 12, plus per-recipient delay and anomalies. A pass requires positive in-window delivery evidence. Zero sends gives `0/12` attempted and confirmed routes and `FAIL (insufficient evidence)`. A single confirmed send supports the named route on that occasion. [Grading communication](../README.md#grading-communication)
- Record each peer’s frozen source hash or capture error. For each distinct source, report independent build and accuracy, input immutability, and timing for `prefill_balanced`, `prefill_ragged_init`, `prefill_long`, `extended_odd_tail`, and `extended_empty_and_long`. The driver checks both output and final state at `atol = rtol = 1e-3`. Include the geomean speedup for correct results and any locked-file mismatches.

**Qualitative checks**

If a tool invocation, message match, or retry is ambiguous, quote the relevant sender and recipient rows in redacted form and explain what can be attributed to Houmao, CCCC, or peer behavior. A reply or useful idea can illustrate discussion. Neither is required for a successful delivery.

## Gotchas

A busy peer may receive a batch later. A receipt reporting gateway acceptance alone cannot confirm native delivery before the deadline. Record pending or uncertain handoffs separately. Quiet peers and an unchanged or incorrect GDN kernel are valid observations.

## Blinding and Transcript Checks

Show peers only the kernel task, their own workplace and system prompt, and the CCCC connection brief. Keep grading instructions and evidence paths outside agent prompts. Inspect native input and tool-result records from all four sessions, independently of the peers’ summaries. File access between peers is permitted and supplies no evidence of CCCC delivery.
