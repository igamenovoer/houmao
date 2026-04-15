## Context

Houmao-managed tmux-backed agents already receive a per-agent memory root with a fixed `houmao-memo.md` file and a contained `pages/` directory. The runtime publishes `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`, and the CLI, gateway, and pair-server surfaces already expose memo and page operations.

The managed launch prompt header is also already section-based. It resolves whole-header policy plus per-section policy, renders deterministic XML-like sections under `<managed_header>`, and persists secret-free section metadata in build artifacts and manifests. That is the right place to add a short cue that tells every managed agent where its durable memo lives and when to consult it.

The missing piece is agent-facing behavior: agents are not told in the launch prompt to read the memo every prompt turn, and the packaged system-skill catalog does not include a concise memory-management skill that routes user requests such as "add this to the agent memo" or "remove this from houmao memo" to supported memory operations.

## Goals / Non-Goals

**Goals:**

- Add a default-enabled `memo-cue` managed-header section rendered as `<memo_cue>`.
- Include the resolved absolute `houmao-memo.md` path in the prompt at launch time.
- Instruct the agent to read the memo at the start of each prompt turn and to follow relevant authored `pages/...` links when needed.
- Preserve existing whole-header and per-section controls so operators can disable `memo-cue` with the same `--managed-header-section memo-cue=disabled` shape.
- Add a compact `houmao-memory-mgr` packaged system skill for memo and page editing through the maintained memory surfaces.
- Add a dedicated system-skill set that makes `houmao-memory-mgr` available in managed launch, managed join, and CLI-default installations.

**Non-Goals:**

- Do not add a new memory storage layout or new directories under the memory root.
- Do not add generated memo indexes, automatic page-link maintenance, or page taxonomy rules.
- Do not make Houmao inspect memo content during memory creation, launch, join, or relaunch.
- Do not store live retry counters, dedupe ledgers, mailbox receipts, or runtime supervision state in managed memory pages.
- Do not add a new memory CLI family; use the existing `houmao-mgr agents memory ...`, gateway `/v1/memory/*`, and pair-server memory proxy surfaces.

## Decisions

### Decision: `memo-cue` is a managed-header section, not role prompt text

The new cue will join the existing managed-header section list as policy key `memo-cue` and rendered tag `<memo_cue>`.

Rationale:

- The managed header already owns durable Houmao-managed launch facts such as identity, runtime guidance, and automation behavior.
- Section policy, profile storage, launch overrides, metadata, and documentation already exist for this class of prompt content.
- Embedding the cue in role prompts would require every role and specialist to repeat a path that is only known after managed identity and memory resolution.

Alternatives considered:

- Add the cue to `houmao-runtime-guidance`: rejected because the memo path is a concrete per-agent path and deserves independent opt-out.
- Add it as launch appendix text: rejected because appendices are operator-supplied one-shot content and should not become a hidden Houmao-owned default.

### Decision: Render order is `identity`, `memo-cue`, then runtime guidance

The section order will become:

1. `identity`
2. `memo-cue`
3. `houmao-runtime-guidance`
4. `automation-notice`
5. `task-reminder`
6. `mail-ack`

Rationale:

- The memo path is part of the managed agent's own identity envelope.
- Placing it before general runtime guidance keeps the concrete per-agent context visible before broader Houmao workflow guidance.
- Default-disabled mailbox helper sections remain at the end.

Alternatives considered:

- Put `memo-cue` after runtime guidance: workable, but less direct because the agent sees abstract runtime rules before the concrete memo it should consult every turn.

### Decision: Prompt composition receives the resolved memo path explicitly

Managed launch code will resolve `AgentMemoryPaths` before composing the effective prompt and pass `memo_file` into the prompt composer. The prompt composer will only render `<memo_cue>` when the whole header is enabled, the `memo-cue` section resolves enabled, and a memo file path is available.

For normal managed tmux-backed launch and join flows, memory resolution is already required before the session is considered complete. If a non-memory-capable or legacy path attempts to render `memo-cue` without a memo file path, implementation should fail explicitly in maintained managed launch paths rather than silently rendering an incomplete cue.

Rationale:

- The prompt text must contain an absolute filesystem path at launch time.
- Keeping path resolution outside the renderer preserves the renderer's role as deterministic composition over already resolved launch inputs.
- Failing closed catches launch paths that forget to bind memory before asking the agent to read it.

Alternatives considered:

- Let the prompt tell agents to use `HOUMAO_AGENT_MEMO_FILE`: rejected as the primary cue because the user asked for the absolute path in the launch prompt. The skill can still mention the env var for in-agent discovery.

### Decision: `houmao-memory-mgr` is compact and routes to existing memory operations

The new skill will be a single concise `SKILL.md` plus optional minimal agent metadata, without action subpages in the initial version. It will teach:

- current-agent discovery through `HOUMAO_AGENT_MEMO_FILE`, `HOUMAO_AGENT_PAGES_DIR`, and `HOUMAO_AGENT_MEMORY_DIR`,
- selected-agent discovery through `houmao-mgr agents memory path`,
- memo operations through `memo show|set|append`,
- page operations through `tree|resolve|read|write|append|delete`,
- rules for smallest requested edits, page containment, authored links, and non-use for live runtime bookkeeping.

Rationale:

- The skill is loaded when an agent is asked to edit memory; it should be short enough to keep loaded context small.
- The maintained CLI already contains the action vocabulary, so duplicating every command in separate pages would add ceremony before the skill proves it needs that structure.

Alternatives considered:

- Build a multi-page skill like mailbox or messaging: rejected for the first version because the requested behavior is a concise router for one existing command family.
- Fold this into `houmao-agent-inspect` or `houmao-agent-messaging`: rejected because memo editing is neither read-only inspection nor inter-agent communication.

### Decision: Use a dedicated `agent-memory` system-skill set

The packaged catalog will add `houmao-memory-mgr` and a named set such as `agent-memory`. The fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` will include that set.

Rationale:

- Memory management is cross-cutting and should not be hidden inside mailbox, user-control, messaging, or gateway sets.
- A dedicated set keeps future memory-related skill evolution isolated.
- Adding the set to all fixed selections makes the skill available wherever the memo cue is relevant.

Alternatives considered:

- Add the skill to `user-control`: rejected because current-agent memo editing is not mainly project/specialist/credential authoring.
- Add the skill to `agent-inspect`: rejected because the skill mutates memo and page content.

## Risks / Trade-offs

- [Prompt bloat] -> Keep `<memo_cue>` short and only include the absolute memo path plus the per-turn read rule.
- [Stale mental model about "each turn"] -> The cue instructs the model; Houmao does not enforce reads at runtime. Tests should verify prompt content, not impossible model behavior.
- [Launch paths forget memo path] -> Make maintained managed launch composition pass resolved `AgentMemoryPaths.memo_file`; add tests around prompt payload rendering and launch metadata.
- [Skill overlap with raw file editing] -> The skill should prefer `houmao-mgr agents memory ...` and only use direct env-var paths for the current managed agent when that is the supported in-agent path available.
- [Memo treated as generated index again] -> Repeat the free-form memo rule in the skill and docs: links to `pages/` are authored Markdown, and Houmao does not auto-reindex pages into the memo.

## Migration Plan

No data migration is required.

Implementation should:

1. extend managed-header section policy and rendering,
2. pass resolved memo paths from managed launch/join/relaunch composition,
3. add the packaged memory-management skill and catalog set,
4. update docs and tests.

Rollback is straightforward: remove the catalog entry/set, remove the new section from defaults/order, and keep existing memo/page storage unchanged.

## Open Questions

- None for proposal scope. The change assumes `memo-cue` is an instruction cue rather than runtime enforcement that the model actually reads the file on every turn.
