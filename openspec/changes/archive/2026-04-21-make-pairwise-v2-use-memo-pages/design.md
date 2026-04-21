## Context

`houmao-agent-loop-pairwise-v2` currently has three related problems.

First, the packaged skill text still presents default `initialize` as email-first participant preparation, while the live pairwise-v2 spec and loop-authoring docs already describe `precomputed_routing_packets` as the default prestart strategy. That leaves the top-level skill, the prestart page, and the docs disagreeing about what `ready` means and when standalone preparation mail should exist.

Second, the current initialization guidance still treats transient mail or memo appends as the main carrier for per-run participant instructions. That is weak for long-running or resumed runs because `initialize` and `start` information should be easy to reopen in one durable location without asking the operator or the participant to reconstruct the latest message.

Third, the managed-memory contract intentionally keeps `houmao-memo.md` free-form and caller-owned. This change cannot introduce a general Houmao-managed memo metadata system, generated index, or parser-owned memo schema. Any replaceable structure must remain pairwise-v2-owned content that is edited only when the caller explicitly performs memo writes.

## Goals / Non-Goals

**Goals:**
- Make pairwise-v2 default `initialize` match the routing-packet-first design already described in the current spec and docs.
- Make `initialize` write durable per-run participant guidance into managed memory pages.
- Make `start` write a durable master-facing charter page and reduce the live trigger message to a compact control-plane request.
- Make plan authoring write generated plans into one user-selected output directory with a stable canonical entrypoint.
- Define a bounded memo note convention that lets pairwise-v2 replace only its own run-specific memo block for a given `run_id` and slot.
- Keep all memo and page content caller-authored and compatible with the free-form managed-memory model.

**Non-Goals:**
- Introducing a general Houmao memo metadata format, page index, or memo reindex operation.
- Changing the general `agent-memory-freeform-memo` ownership contract.
- Changing the stable `houmao-agent-loop-pairwise` or generic loop skill contracts.
- Adding a new dependency for Markdown parsing or document transforms.

## Decisions

### Decision: Per-run durable content lives in page files, not directly in the memo

Pairwise-v2 will treat managed memory pages as the durable home for rich run material:
- per-participant initialize guidance under a stable per-run page path
- master-facing start-charter guidance under a stable per-run page path

The memo will contain only a short run-owned reference block for each slot, pointing at the relevant page and summarizing the slot at a glance.

Rationale:
- Page files are the smallest durable unit that can be replaced whole without disturbing unrelated memo text.
- This keeps `houmao-memo.md` compact and readable.
- It also fits the repo guidance that long details belong in `pages/` with a short memo note.

Alternatives considered:
- Put the full initialize message and full charter directly in `houmao-memo.md`.
  Rejected because the memo is free-form shared context, not a good home for repeated large run payloads.
- Keep the current mail-first posture and treat memo writes as optional copies.
  Rejected because the durable copy should be the primary contract, not an afterthought.

### Decision: Memo replacement uses exact string sentinels owned by pairwise-v2

Pairwise-v2 will define one exact begin/end sentinel pair for each run-owned memo slot, keyed by `run_id` and slot name such as `initialize` or `start-charter`. Updating a slot means replacing only the text inside that exact owned block, or appending a new block when no owned block exists yet.

Rationale:
- Exact sentinel matching is sufficient for bounded replacement and avoids a new parser dependency.
- The repo already treats memo text as caller-owned ordinary Markdown, so pairwise-v2 should use the smallest possible convention.
- A fail-closed exact match is safer than fuzzy heading or prose matching.

Alternatives considered:
- Markdown AST parsing or a specialized Markdown library.
  Rejected because the problem is targeted block replacement, not general Markdown understanding.
- Heading-based matching.
  Rejected because headings are too easy to duplicate or edit manually.
- A repo-wide memo metadata standard.
  Rejected because it would conflict with the intentional free-form memo contract.

### Decision: Default `initialize` for pairwise-v2 is routing-packet validation plus memory materialization

For `precomputed_routing_packets`, default `initialize` will:
- validate packet coverage and readiness
- materialize or refresh the participant-facing initialize page
- materialize or refresh the corresponding run-owned memo reference block

Default `initialize` will not send standalone operator-origin participant preparation mail. Preparation mail remains the explicit `operator_preparation_wave` lane for acknowledgement-gated or warmup-heavy runs.

Rationale:
- This aligns the packaged skill with the current spec and loop-authoring guide.
- It keeps the default path minimal and deterministic.
- It separates durable prestart material from optional live warmup traffic.

Alternatives considered:
- Preserve email-first default initialization.
  Rejected because it keeps the existing drift and makes durable run material secondary.

### Decision: `start` becomes page-first, with a compact live trigger

Before sending the master trigger, pairwise-v2 will materialize the master-facing charter page and refresh the master memo reference block. The live start action then sends a compact trigger that points the master at the page and requires explicit `accepted` or `rejected`.

Rationale:
- The durable charter belongs in managed memory, where the master can reopen it across turns.
- The live control message should be concise and stable, not a second copy of the full charter.

Alternatives considered:
- Keep the charter only in the live start message.
  Rejected because it makes recovery and reinspection weaker.

### Decision: Plan authoring writes into one user-selected output directory

Pairwise-v2 authoring will require one user-selected plan output directory before it writes plan files. The canonical entrypoint will be `plan.md` inside that directory for both single-file and bundle forms.

Rationale:
- Operators need a predictable place to find the authored plan later during `initialize` and `start`.
- One directory-scoped contract is simpler than having separate path rules for single-file and bundle forms.
- It avoids silently inventing storage locations that the user did not approve.

Alternatives considered:
- Invent a default directory automatically.
  Rejected because the user asked for explicit control over where generated plans land.
- Keep arbitrary single-file names for the compact form.
  Rejected because `plan.md` is the simplest canonical entrypoint for both forms.

## Risks / Trade-offs

- [Risk] Sentinel blocks may be manually edited or duplicated. → Mitigation: require exact `run_id` plus slot matching, fail closed on multiple matches, and instruct the skill to report conflicts rather than guessing.
- [Risk] Stable page paths may leave stale run material behind. → Mitigation: scope pages under a per-run directory and rewrite whole files for the active run instead of mutating ad hoc fragments.
- [Risk] The packaged skill, docs, and spec could drift again if only one layer is updated. → Mitigation: treat this as one coordinated change across skill assets, the pairwise-v2 spec, and loop-authoring docs.
- [Risk] Operators may expect preparation mail in the default path because the current skill text says so. → Mitigation: update the top-level skill wording, prestart page, and docs to make `operator_preparation_wave` the only mail-first lane.

## Migration Plan

This change is documentation and packaged-skill guidance only; no runtime data migration is required.

Implementation should:
1. Update the pairwise-v2 packaged skill assets and supporting references.
2. Update the pairwise-v2 spec delta and loop-authoring docs.
3. Leave existing memo content untouched unless a caller explicitly performs a pairwise-v2 initialize/start write using the new guidance.

Rollback is straightforward: revert the skill assets, docs, and spec delta. Existing memo/page content written by callers remains ordinary Markdown and ordinary page files.

## Open Questions

- Whether the stable per-run page paths should be fully prescribed in the skill text or documented as a recommended pattern with a required run-scoped namespace.
- Whether the compact start trigger should carry only the page path, or also carry a short revision digest so the master can detect stale charter references more explicitly.
