# Plan a Behavior Qualification Run

## Workflow

1. **Resolve suite selectors.** Read [../references/case-catalog.md](../references/case-catalog.md) and [../references/case-schema.md](../references/case-schema.md); accept area/profile, mode-aware area/profile, global profile, mode-aware global profile, tag, exact case, exact variant, or composite union forms. With no selector, return read-only selection help and stop without creating a run root.
2. **Expand deterministically.** Load only selected functional-area pages, expand cumulative tiers and stable variants in catalog order, apply `manual` or `automatic` mode filters when requested, union and deduplicate `(case_id, variant_id)` cells, and retain every contributing selector. Reject unknown selectors or modes before launch.
3. **Resolve the repository and fresh run root.** Default to `tmp/houmao-dev-behavior-testing/<UTC timestamp>-<scope>` and refuse a non-empty destination.
4. **Resolve providers and contexts separately.** Apply [../references/fixture-contexts.md](../references/fixture-contexts.md) and record unsupported combinations rather than silently dropping them. Never infer providers or repetitions from a coverage profile.
5. **Check catalog drift.** Compare committed route expectations with the current packaged manifest; never rewrite cases or profile membership from manifest content.
6. **Validate invocation integrity.** Require exact `$houmao-*` handles in manual driving stimuli, forbid them in automatic driving stimuli, restrict `not-applicable` to generated-prompt or lifecycle origins, and reject root oracles that contradict packaged activation policy.
7. **Declare cost and boundaries.** Preview resolved case and variant counts by invocation mode and phase, provider/context cells, repetitions, total attempts, timeouts, evidence sources, allowed mutation roots, and cleanup obligations.
8. **Write and freeze `run-manifest.json`.** Include ordered requested selectors, catalog version and digest, resolved cases and variants, functional-area/profile attribution, driver invocation mode, stimulus origin and exact digest, expected initial root, expected delegated roots, expected route, contributing selectors, explicit exclusions, provider/context/repetition matrices, Git/source posture, and content digests.

If the requested slice cannot use one common fixture strategy, use the native planning tool to partition it into explicit context groups under the same run without weakening isolation or evidence requirements.

## Admission Contract

Planning is read-only outside the new run root. A runnable plan needs exact selector expansion, case revisions, variants, invocation provenance, root and route oracles, providers, contexts, repetitions, fixture strategy, and evidence visibility posture. Catalog drift, unavailable credentials, unsupported providers, or unsafe targets produce planned `incomplete` entries before any launch.

## Output Contract

Write `run-manifest.json` and `plan.md` under the run root. Freeze their hashes before `execute-case`; any correction creates a new run id.

## Guardrails

- DO NOT select cases from memory when the committed catalog is available.
- DO NOT launch or create a run root when no selector was supplied.
- DO NOT let profile selection alter provider or repetition defaults.
- DO NOT use the runtime manifest to manufacture a new oracle.
- DO NOT treat an existing non-empty directory as a fresh run root.
