# Adjudicate One Behavior Case

## Workflow

1. **Verify adjudication admission.** Require frozen context, stimulus, raw evidence index, and case oracle with matching digests.
2. **Load the evidence contract and verdict rubric.** Read [../references/evidence-contract.md](../references/evidence-contract.md) and [../references/verdict-rubric.md](../references/verdict-rubric.md).
3. **Judge initial activation.** Compare provider-native root-selection evidence with `expected_initial_root`; use `unobservable` when no reliable activation source exists.
4. **Judge delegation, routing, actor, phases, gates, effects, and outcome separately.** Keep `expected_delegated_roots` distinct from initial activation and cite concrete event ids, command records, file/runtime deltas, or transcript spans for every non-incomplete verdict.
5. **Apply hard failures.** Wrong actor selection, identity during an informational phase, skipped or late identity during an operational phase, automatic welcome access, direct implicit explicit-only root selection, or forbidden mutation fails its dimension regardless of prose quality.
6. **Write `verdict.json` and `verdict.md`.** Record uncertainty and limitations without editing raw evidence or the case oracle.

If evidence conflicts, use the native planning tool to map each claim to its authority tier, keep the more authoritative observable source, and mark unresolved dimensions `incomplete` rather than forcing agreement.

## Independence Contract

Adjudication may read the oracle and raw evidence. It must not ask the agent under test to explain its hidden reasoning or retroactively clarify which skill it thought it used.

## Guardrails

- DO NOT infer activation solely from a semantically plausible answer.
- DO NOT collapse unobservable activation into pass or fail.
- DO NOT rewrite the stimulus, context, transcript, or event stream during adjudication.
