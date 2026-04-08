## Context

Houmao already has three distinct filesystem roles around a managed session:

- overlay-local reusable source and managed content under `.houmao/catalog.sqlite`, `.houmao/content/`, and `.houmao/agents/`,
- durable runtime-owned session state under `.houmao/runtime/`,
- per-session scratch under `.houmao/jobs/<session-id>/`.

Those layers do not cover the user request for a durable agent-controlled notebook or archive that can outlive one session and hold arbitrary working material such as experiment logs, downloaded files, source notes, and extracted knowledge. Today an operator or agent must choose an ad hoc directory with no supported launch-profile default, no manifest-backed discovery, no `houmao-mgr` inspection field, and no cleanup boundary.

This change is cross-cutting because the memory-dir contract has to be understood consistently by:

- profile authoring,
- direct launch and join,
- runtime manifest persistence,
- relaunch and inspection,
- cleanup and ownership semantics.

The design also needs to preserve one key product constraint from the exploration: Houmao must publish where the memory directory is, but Houmao must not define the internal schema of that directory. The agent, not Houmao, is responsible for inspecting the directory and deciding how to organize its contents.

## Goals / Non-Goals

**Goals:**
- Provide a supported optional memory directory for each managed agent instance.
- Use a conservative project-local default when memory is enabled: `<active-overlay>/memory/agents/<agent-id>/`.
- Allow explicit opt-out so an agent can have no memory directory at all.
- Allow explicit exact-path binding so operators can point one launch or profile at any directory, including a shared directory used by multiple agents.
- Persist the resolved memory binding in runtime-backed session state and publish it to the running session environment.
- Make the resolved memory path discoverable through supported `houmao-mgr` inspection surfaces.
- Keep memory directories out of session cleanup ownership.

**Non-Goals:**
- Defining any fixed subdirectory or file schema inside the memory directory.
- Indexing, searching, syncing, deduplicating, or versioning memory contents.
- Moving agent memory into the project catalog or managed content store.
- Treating memory contents as a reusable source definition like prompts, auth bundles, or skills.
- Introducing a new server-side memory service, API, or registry index in this change.
- Automatically migrating existing ad hoc directories into the new contract.

## Decisions

### Decision: Model memory binding as tri-state resolved runtime state

The resolved runtime state should distinguish three outcomes:

- `auto`: enable memory and derive the default path,
- `exact`: enable memory at one explicit operator-supplied path,
- `disabled`: do not bind a memory directory for this session.

User-facing authoring and launch inputs stay simpler:

- `--memory-dir <path>` means exact external binding,
- `--no-memory-dir` means explicit disable,
- clearing a stored profile field returns that profile to the system default behavior.

This is better than a simple optional string because it lets runtime state preserve the difference between the derived default path, an explicit external path, and a deliberate opt-out. It also lets launch profiles store intentional opt-out separately from "no stored preference". That distinction matters for precedence:

1. source recipe defaults,
2. launch-profile memory intent,
3. direct launch override.

Under this model:

- launch-profile `disabled` means "this profile intentionally launches without memory unless overridden",
- an omitted profile field means "fall back to the system default behavior",
- direct `--memory-dir` wins over profile `disabled`,
- direct `--no-memory-dir` wins over profile defaults or exact-path defaults,
- when nothing explicitly disables memory or chooses an exact path, the session resolves to the conservative default `auto` path.

Alternative considered:
- Store only an optional path string and interpret `null` as disabled.
  Rejected because `null` cannot distinguish "inherit lower precedence" from "explicitly disabled".

### Decision: Use a conservative overlay-local default path keyed by `agent-id`

When memory is enabled in `auto` mode, the resolved path should be:

```text
<active-overlay>/memory/agents/<agent-id>/
```

`agent-id` is the correct key rather than `session-id` because memory is meant to survive relaunch and replacement of the same logical managed agent. Using `session-id` would fragment one logical agent's durable notebook into a new directory on every launch.

The default stays inside the selected project overlay rather than under `jobs/` or `runtime/`:

- not `jobs/` because jobs are scratch and cleanup-owned,
- not `runtime/` because runtime is Houmao-owned session/build state,
- not project root directly because `.houmao/memory/` is the conservative default the user requested.

Alternative considered:
- Default to `<active-overlay>/jobs/<session-id>/memory`.
  Rejected because it ties durable memory to scratch lifetime and cleanup.

Alternative considered:
- Default to a human-visible root outside `.houmao`, such as `<project-root>/agent-memory/`.
  Rejected for v1 because the user explicitly chose the conservative default.

### Decision: Persist resolved exact runtime truth in the session manifest

Launch profiles should store memory intent, but the runtime session manifest should store the resolved runtime truth:

- whether memory is enabled for this session,
- the resolved absolute directory when enabled,
- enough source metadata to explain how that result was chosen.

This follows Houmao's current pattern where reusable birth-time defaults live in profiles, while the runtime manifest is the authoritative record of what this specific live session actually received.

The resolved manifest record should be absolute-path based so relaunch and inspection do not need to replay relative path resolution from the original CLI context.

Alternative considered:
- Persist memory only in the launch profile and recompute later from profile plus invocation context.
  Rejected because joins, one-off overrides, and relaunch should not depend on reconstructing the original launch call.

Alternative considered:
- Publish memory only through tmux env without manifest persistence.
  Rejected because env-only state is too weak for relaunch, inspection, and offline debugging.

### Decision: Publish `HOUMAO_MEMORY_DIR` only when memory is enabled

When a session has a resolved memory directory, the runtime should export:

```text
HOUMAO_MEMORY_DIR=<absolute-path>
```

When memory is disabled, Houmao should publish no such variable.

This mirrors the existing manifest-first discovery style:

- the manifest is the durable authority,
- the session env is the convenient live discovery surface.

It also gives agents a single stable entry point without forcing them to parse the session manifest directly for the common case.

Alternative considered:
- Always export the variable and use an empty string when disabled.
  Rejected because empty-string environment contracts are easy to mis-handle and do not align with the repository's current "publish only when present" pattern for optional runtime state.

### Decision: Houmao owns discovery, not internal structure

The memory directory is intentionally opaque to Houmao. Houmao may create the root directory when memory is enabled, but Houmao should not impose:

- required subdirectories,
- required Markdown file names,
- catalog indexing,
- metadata sidecars,
- cleanup-time validation of contents.

The only contract Houmao owns is:

- path selection,
- manifest/env publication,
- inspection visibility,
- lifecycle and cleanup boundaries.

The agent is expected to inspect the directory, infer or establish structure, and read or write it accordingly.

Alternative considered:
- Seed a fixed tree such as `sources/`, `knowledge/`, `logs/`, and `index.md`.
  Rejected because the user explicitly wants agents to inspect the directory and decide how to use it, including shared directories with heterogeneous content.

### Decision: Memory is durable user or agent state, not cleanup-owned runtime state

`houmao-mgr agents cleanup ...` and runtime cleanup families should never remove memory directories merely because a session stopped. Memory is closer to operator workspace state than to runtime envelopes.

This design intentionally separates:

- session envelope cleanup for `runtime/` and optionally `job_dir`,
- durable memory outside cleanup ownership.

Alternative considered:
- Add an optional cleanup mode that deletes memory alongside `job_dir`.
  Rejected for this change because it would blur the ownership boundary before the base contract is established.

## Risks / Trade-offs

- [Shared exact paths can let multiple agents overwrite each other's files] → Mitigation: treat shared memory as explicit operator intent only; do not make sharing the default.
- [A durable memory path can be mistaken for structured Houmao-owned data] → Mitigation: document clearly that Houmao owns only path discovery and not directory contents.
- [Operators may expect cleanup to reclaim memory automatically] → Mitigation: make memory non-ownership explicit in docs and CLI/state output.
- [Using `agent-id` for the default path means renaming or replacing an agent under a new id creates a new default memory root] → Mitigation: keep explicit `--memory-dir` and profile-level exact-path binding available when continuity across ids is desired.
- [Joins can bind arbitrary external directories without strong validation] → Mitigation: validate only path usability and persistence semantics; do not attempt content validation.

## Migration Plan

No data migration is required because this is a new optional contract.

Implementation rollout should proceed in this order:

1. Add launch-profile model support for tri-state memory intent.
2. Add direct CLI flags for launch, join, and profile authoring surfaces.
3. Resolve memory intent during launch and join into one absolute runtime result.
4. Persist that result in the session manifest and publish `HOUMAO_MEMORY_DIR` when enabled.
5. Surface the resolved path through `houmao-mgr` inspection outputs.
6. Update cleanup and docs so the non-ownership boundary is explicit.
7. Add coverage for auto, exact, disabled, shared-path, join, relaunch, and cleanup behavior.

Rollback is low risk:

- stop accepting the new flags,
- stop persisting the new manifest section and env var,
- leave any already-created memory directories untouched as ordinary filesystem state.

## Open Questions

None for this change. Project-wide configurable memory roots, indexing, and richer shared-memory coordination are intentionally deferred.
