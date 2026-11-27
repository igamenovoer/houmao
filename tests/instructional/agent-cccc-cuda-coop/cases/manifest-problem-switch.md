# Spontaneous CCCC Chat During Fused MoE Optimization

The tester selects the fused top-k MoE SwiGLU block and repeats the same five-minute communication experiment with four fresh Qwen 3.8 peers. This case samples Houmao and CCCC under a second workload while keeping the prompts, model, private-workdir convention, and delivery policy constant.

## Sub-cases

- **Workload selection.** The explicit override seeds four private MoE workdirs with the selected starter and driver while the manifest default stays GDN.
- **Independent discussion.** Observe any peer-initiated chat, including direct, multi-recipient, or threaded exchanges if they occur. Audit all observed attempts, including ones that never produced a stored event.
- **Cutoff.** Freeze four workdirs and capture the native journal boundaries. Assess the communication evidence from this run independently of the GDN outcome.

## How to get to it (user POV)

Set `PROBLEM_ID=fused_moe` in a fresh Bash shell. Follow Launch and Doctor to provision a new group, four fresh sessions, and four physical working directories under the same OS user. Once all four are ready, the tester issues one identical kernel task to each and observes for five minutes. [Launch](../README.md#launch) · [Doctor](../README.md#doctor)

## Driving it with cuda_coop_lab

1. Check `jq -e '.default_problem == "gdn_prefill" and .selected_problem == "fused_moe" and .problem_override == "fused_moe"' "$EVIDENCE/manifest-resolved.json"`. Confirm `configure.json` shows the same override and four workdirs.
2. Use `pixi run python "$LAB" run-window --run-meta "$RUN_META"` via Drive. Let each peer decide when and how to discuss optimization. At the common cutoff the helper snapshots the four sources and requests interrupts. [Drive](../README.md#drive)
3. Collect per-actor histories and bounded native journals before stopping the group. For messages with multiple recipients, check each addressed peer separately. If threads occur, check their parent event IDs. Then run the independent MoE verification and record this case’s own evidence directory and verdict. [Evidence](../README.md#evidence) · [Cleanup](../README.md#cleanup)

## Expected Outcome

**Quantified checks**

- Four distinct sessions and actor bindings share one group and `Qwen/Qwen3.8-27B-FP8`. Check all four MoE starter hashes and native kickoffs. Expect one identical tester assignment per peer, one 300-second window, and zero tester discussion messages, relays, nudges, or consuming queue operations.
- Apply the same in-window delivery and integrity criteria as GDN. Report attempted and confirmed routes out of 12 for **this** group. For every stored send, preserve its event ID and count each intended recipient once. Record late or uncertain handoffs explicitly. With zero attempted sends record `0/12` and `FAIL (insufficient evidence)`. [Grading communication](../README.md#grading-communication)
- Record all four peers’ cutoff source hashes or capture errors, locked-file mismatches, and each distinct implementation’s independent result. Check `moe_skewed_512`, `moe_balanced_1024`, `extended_small_odd_37`, and `extended_heavy_skew_1536` for output accuracy at `atol = rtol = 1e-3` and input immutability. Record workload timings and geomean speedup for correct implementations independently of the communication verdict.

**Qualitative checks**

Explain any ambiguity in the intended audience or in matching a native message to its CCCC event. Cite the sender operation, group routing data, and native input or tool result. Differences in topic, strategy, and frequency of discussion are observations about this run.

## Gotchas

Select MoE for both `show-manifest` and `configure`. A correct MoE implementation or a successful GDN handoff cannot supply missing MoE delivery evidence. If the peers use shared filesystem access, report it separately from CCCC traffic.

## Blinding and Transcript Checks

Give peers the same neutral assignment and their private system-prompt additions in the same order as GDN. Keep the previous run, scoring rules, and evidence paths out of the launch prompts. Review all four native transcripts for actual sends, receipt of messages, and any operator intervention. Verify the frozen code using the authoritative MoE fixture.
