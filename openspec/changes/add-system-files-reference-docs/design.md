## Context

Houmao's recent runtime and launcher work made the filesystem ownership model much clearer in code and implementation-facing docs:

- shared roots are now resolved through `src/houmao/owned_paths.py`,
- runtime-managed build and session state is centered under `~/.houmao/runtime`,
- shared-registry discovery state is centered under `~/.houmao/registry`,
- CAO launcher artifacts live under `runtime_root/cao_servers/<host>-<port>/launcher/` with sibling `home/`,
- workspace-local destructive scratch now lives separately under `<working-directory>/.houmao/jobs/<session-id>/`.

The repository already documents many of those pieces, but the explanation is split by subsystem:

- `docs/reference/realm_controller.md` mixes CLI behavior with filesystem layout,
- `docs/reference/cao_server_launcher.md` explains launcher artifacts and CAO home selection,
- `docs/reference/agents/**` explains session roots and gateway nesting,
- `docs/reference/registry/**` explains registry roots and `record.json`,
- gateway pages refer to files nested under session roots.

That structure works for subsystem-specific reading, but it is a poor fit for one operator question: "What files and directories will Houmao create on my filesystem, and how should I prepare for them?" The same root or artifact can appear in multiple places, which increases drift risk and makes it harder to tell which paths are stable contracts, which are implementation details, and which roots are Houmao-selected but later written by an external tool such as CAO.

This change is primarily documentation and spec coherence work. It should centralize the filesystem map and then let subsystem pages focus on behavior, contracts, and workflows while linking back to the centralized filesystem reference when readers need storage details. It also absorbs the live `agent_id` cutover leftovers tracked in `context/issues/known/issue-agent-id-cutover-leftovers.md`, because those leftovers now sit in exactly the registry docs and main specs that this change already needs to touch.

## Current duplication and drift to remove

The central subtree is not just new content. It is also a consolidation pass over existing reference pages that currently duplicate or partially drift on filesystem details.

- `docs/reference/realm_controller.md` currently mixes CLI and lifecycle guidance with session-root, gateway-artifact, and `job_dir` path inventories.
- `docs/reference/agents/contracts/public-interfaces.md` repeats a runtime-owned session tree that is better treated as canonical filesystem inventory.
- `docs/reference/agents/internals/state-and-recovery.md` contains the strongest current session and gateway storage tree, but it should become source material for the centralized reference rather than remain the only long-form artifact map.
- `docs/reference/gateway/contracts/protocol-and-state.md` needs to keep gateway-specific artifact semantics while no longer acting like the broader runtime-root filesystem map.
- `docs/reference/cao_server_launcher.md` currently carries both launcher CLI behavior and the most operator-facing description of launcher artifacts, CAO home selection, and filesystem preparation.
- `docs/reference/registry/index.md` still contains stale `agent key` wording from the older canonical-name-keyed layout even though the current contract is `agent_id` keyed.
- `docs/reference/agents_brains.md` still describes `tmp/agents-runtime/` as the default runtime root even though recent implementation moved defaults under `~/.houmao/runtime`.

The implementation should treat those pages as deliberate simplification targets, not just as pages that happen to gain one more cross-link.

## Current `agent_id` cutover leftovers to resolve

The issue file `context/issues/known/issue-agent-id-cutover-leftovers.md` identifies a second class of coherence problems that this change should resolve while it is already editing the same surfaces:

- `docs/reference/registry/index.md` still presents `agent key` and “packaged schema is a follow-up” wording as if the old registry model were still current.
- `docs/reference/registry/internals/runtime-integration.md` still names `LiveAgentRegistryRecordV1` in its publication flow.
- `openspec/specs/registry-reference-docs/spec.md` still normatively requires `agent key` and v1 registry semantics in the main spec.
- `openspec/specs/brain-launch-runtime-pydantic-boundaries/spec.md` still describes the current packaged registry schema as v1 under `live_agents/<agent-key>/record.json` and still treats `LiveAgentRegistryRecordV1` as the current typed boundary.
- `openspec/specs/agent-discovery-registry/spec.md` has one surviving “derive `agent_key`” sentence in an otherwise `agent_id`-based spec.
- `src/houmao/agents/realm_controller/schemas/live_agent_registry_record.v1.schema.json` is still packaged even though the current implementation and tests appear centered on `live_agent_registry_record.v2.schema.json`.

This scope expansion is still cohesive because it addresses one reader-facing coherence problem: the repo should not present contradictory answers about whether current registry identity is `agent_key` or `agent_id`, whether the shipped registry contract is v1 or v2, or whether the v1 packaged schema remains current.

## Goals / Non-Goals

**Goals:**

- Add a dedicated `docs/reference/system-files/` subtree that explains Houmao-owned and Houmao-generated filesystem artifacts across runtime-managed agents, shared registry, gateway-adjacent session state, and CAO launcher state.
- Provide one clear ownership model for shared roots, nested directories, generated files, and workspace-local scratch, including precedence between explicit path overrides, env-var overrides, and defaults.
- Distinguish between:
  - Houmao-owned files that Houmao creates and updates,
  - Houmao-selected roots that external tools write into,
  - user-owned workspaces that Houmao touches only for local scratch.
- Make the centralized subtree the canonical place for filesystem preparation guidance such as pre-creating directories, setting permissions, and configuring path redirection.
- Update broader reference pages so they link to the centralized filesystem reference instead of duplicating full path explanations.
- Align live registry docs and live OpenSpec main specs with the implemented `agent_id`-keyed, v2 registry contract.
- Resolve the status of the packaged `live_agent_registry_record.v1.schema.json` artifact so the repo no longer implies that both v1 and v2 are equally current when only v2 appears to be exercised.

**Non-Goals:**

- Changing any runtime, launcher, registry, gateway, or mailbox behavior.
- Re-documenting the mailbox filesystem in this subtree; mailbox remains owned by the mailbox reference docs.
- Exhaustively documenting every opaque tool-created file inside external-tool homes such as CAO's internal state tree.
- Replacing subsystem docs with the system-files docs; subsystem pages still need enough artifact context to explain their own behavior.
- Preserving stale `agent_key` or v1 wording for compatibility if those references are only contradictory leftovers rather than intentional historical notes.

## Decisions

### 1. Create a dedicated `docs/reference/system-files/` subtree with a filesystem-first mental model

**Decision:** Introduce a new reference subtree rooted at `docs/reference/system-files/` instead of expanding `realm_controller.md` or embedding another mixed overview page in existing subsystem trees.

The subtree will be organized around storage ownership and reader intent rather than around one subsystem API:

- `index.md` as the entrypoint and glossary,
- one page for roots and ownership boundaries,
- one page for runtime-managed agent and session files,
- one page for CAO launcher and CAO-home related filesystem state,
- one page for shared registry files,
- one page for operator preparation and filesystem planning guidance.

Expected `docs/reference/` structure after the edit:

```text
docs/reference/
  index.md
  system-files/
    index.md
    roots-and-ownership.md
    agents-and-runtime.md
    cao-server.md
    shared-registry.md
    operator-preparation.md
  agents/
    index.md
    contracts/
      public-interfaces.md
    internals/
      state-and-recovery.md
    operations/
      session-and-message-flows.md
  gateway/
    index.md
    contracts/
      protocol-and-state.md
    internals/
      queue-and-recovery.md
    operations/
      lifecycle.md
  registry/
    index.md
    contracts/
      record-and-layout.md
      resolution-and-ownership.md
    internals/
      runtime-integration.md
    operations/
      discovery-and-cleanup.md
  mailbox/
    ...
  realm_controller.md
  cao_server_launcher.md
  agents_brains.md
  cli.md
  realm_controller_send_keys.md
  cao_interactive_demo.md
  cao_claude_shadow_parsing.md
  cao_shadow_parser_troubleshooting.md
```

**Rationale:** Readers who need storage guidance are asking a cross-cutting question that spans multiple subsystems. A subtree makes that question discoverable at the top-level reference index and gives it a stable home.

**Alternatives considered:**

- Expand `docs/reference/realm_controller.md` into the central filesystem guide. Rejected because it is already broad and runtime-specific, while the new filesystem question spans the launcher and registry too.
- Leave filesystem details embedded in subsystem docs. Rejected because path ownership is already duplicated and at risk of drifting again.
- Create one single long `system-files.md` page. Rejected because the topic has enough surface area that roots, runtime artifacts, launcher artifacts, and operator guidance deserve separate pages.

### 2. Define one explicit ownership vocabulary and use it consistently

**Decision:** The new subtree will explicitly classify filesystem surfaces into three categories:

- **Houmao-owned**: paths Houmao creates and whose contract it owns, such as session manifests, registry `record.json`, and launcher `ownership.json`;
- **Houmao-selected**: paths whose root Houmao chooses or derives, but whose detailed contents are owned by another tool, such as the CAO `home/` tree;
- **Workspace-local scratch**: paths Houmao creates in the user's working directory for destructive or session-local scratch, such as `.houmao/jobs/<session-id>/`.

The docs will also call out contract strength for artifacts using language like:

- stable path and meaning,
- stable path with opaque payload or tool-owned contents,
- current implementation detail, not a compatibility promise.

**Rationale:** The current docs are accurate in places but do not always help readers answer whether they can rely on a path, ignore a subtree, pre-create a directory, or inspect the contents safely.

**Alternatives considered:**

- Treat every mentioned path as equally "owned." Rejected because it blurs the critical difference between runtime manifests and CAO's internal state under `HOME/.aws/cli-agent-orchestrator/`.
- Avoid contract-strength labeling to keep docs shorter. Rejected because operator preparation is one of the explicit motivations for this change.

### 3. Keep mailbox explicitly out of scope and say so in the new subtree

**Decision:** The new subtree will exclude mailbox filesystem state except for brief out-of-scope callouts that point readers to `docs/reference/mailbox/`.

The system-files docs will still mention that mailbox exists as a separate filesystem subsystem when clarifying ownership boundaries, but they will not absorb mailbox root layout, mailbox helpers, or mailbox storage contracts.

**Rationale:** Mailbox already has a dedicated reference tree with its own filesystem model and rules. Pulling it into the centralized system-files docs would make the new subtree too large and would undercut the user's stated goal of focusing on Houmao runtime and launcher storage.

**Alternatives considered:**

- Fold mailbox into the centralized filesystem tree for completeness. Rejected as unnecessary scope expansion and contrary to the requested boundary.

### 4. Make subsystem docs link out for broad filesystem maps and keep their own pages behavior-focused

**Decision:** Existing docs will be adjusted so that:

- top-level reference navigation links to the new system-files subtree,
- `realm_controller.md` and `cao_server_launcher.md` point readers to the centralized system-files reference when discussing roots and artifact trees,
- agent, registry, and gateway reference pages keep subsystem-specific artifact semantics but link out for the broader Houmao filesystem map and operator preparation guidance.

The subsystem docs will still include small representative artifact snippets where needed for local comprehension, but they will stop trying to be the full filesystem reference.

**Rationale:** Centralization only works if the old pages stop competing with it. The goal is not to remove useful local examples, but to remove duplicated full-tree explanations.

**Alternatives considered:**

- Leave existing docs unchanged and only add the new subtree. Rejected because readers would still encounter multiple "sources of truth" for path guidance.
- Replace all local artifact examples with links. Rejected because some pages genuinely need small local examples to explain behavior.

### 5. Use artifact tables and tree diagrams as the core explanatory format

**Decision:** The new pages will rely on a consistent documentation pattern:

- a short mental model,
- a representative tree,
- a filesystem artifact table with columns such as path pattern, created by, later written by, purpose, relocation surface, and cleanup expectation,
- source references back to implementation files and tests.

Where a lifecycle or resolution sequence matters, the docs may include Mermaid sequence diagrams, but the primary representation for the new subtree will be tree diagrams and artifact tables rather than workflow-heavy sequence diagrams.

**Rationale:** Readers asking "what files appear?" benefit more from a stable inventory than from prose alone. Tables also make it easier to compare contract strength and ownership across artifacts.

**Alternatives considered:**

- Pure prose pages. Rejected because the topic is fundamentally structural and benefits from a scan-friendly shape.
- Heavy use of Mermaid for everything. Rejected because ownership maps are more naturally represented as trees and tables.

### 6. Simplify existing subsystem pages in place instead of moving or deleting them

**Decision:** The only new reference location introduced by this change is `docs/reference/system-files/`. Existing subsystem pages will mostly stay at their current paths for navigability and link stability, but several sections will be trimmed or rewritten so they stop competing with the new canonical filesystem inventory.

Consolidation map:

| Existing page | Keep local to the page | Move or simplify into `docs/reference/system-files/` |
| --- | --- | --- |
| `docs/reference/realm_controller.md` | CLI entrypoints, lifecycle behavior, high-level registry and gateway overview | Full session-root, gateway-file, and `job_dir` inventory |
| `docs/reference/agents/contracts/public-interfaces.md` | command roles, targeting rules, representative command output | canonical runtime-owned artifact tree |
| `docs/reference/agents/internals/state-and-recovery.md` | recovery authority boundaries, tmux discovery pointers, cleanup semantics | canonical session-root and gateway artifact inventory |
| `docs/reference/gateway/contracts/protocol-and-state.md` | gateway-specific artifact semantics and protocol behavior | broader relationship between `gateway/` files and the full Houmao filesystem map |
| `docs/reference/cao_server_launcher.md` | launcher CLI semantics, proxy rules, startup and health behavior | launcher artifact tree, derived `home/` subtree placement, and general operator preparation guidance |
| `docs/reference/registry/index.md` | mental model, navigation, registry scope | broader filesystem placement explanation and legacy directory-key terminology |
| `docs/reference/registry/contracts/record-and-layout.md` | exact registry layout and `record.json` contract | broader root-family comparison and operator preparation that is not registry-specific |
| `docs/reference/agents/index.md` and `docs/reference/agents_brains.md` | mental model for built homes and runtime-managed sessions | canonical generated-home/runtime-root placement and storage-preparation guidance |

**Rationale:** Most duplication lives in otherwise useful pages. Keeping those pages in place but reducing them to local behavior, contract, and workflow context improves structure without creating a second navigation churn problem.

**Alternatives considered:**

- Merge large existing pages into the new subtree and remove the old pages. Rejected because those pages already carry stable reader expectations and useful non-filesystem behavior documentation.
- Leave the old sections mostly intact and simply add "see also" links. Rejected because it would preserve competing canonical path inventories.

### 7. Fix stale filesystem terminology while centralizing

**Decision:** The same change will correct known stale filesystem wording while simplifying duplicated content.

This includes, at minimum:

- replacing legacy `agent key` directory-language in the registry landing docs with current `agent_id`-keyed terminology,
- correcting outdated statements that present `tmp/agents-runtime/` as the default runtime root in general guidance pages,
- making sure retained examples are clearly examples or explicit override paths rather than implied defaults.

**Rationale:** Centralizing the filesystem inventory but leaving stale terminology behind would still produce reader confusion and undercut the point of having one authoritative storage reference.

**Alternatives considered:**

- Treat stale wording cleanup as a follow-up editorial pass. Rejected because the duplication-removal change already touches the affected pages and should leave them internally consistent.

### 8. Fold live `agent_id` cutover cleanup into the same change instead of creating a second editorial change

**Decision:** This change will also update the live registry docs and live OpenSpec main specs that still describe `agent_key` or v1 registry semantics as current behavior.

Affected non-archival surfaces include:

- `docs/reference/registry/index.md`,
- `docs/reference/registry/internals/runtime-integration.md`,
- `openspec/specs/registry-reference-docs/spec.md`,
- `openspec/specs/brain-launch-runtime-pydantic-boundaries/spec.md`,
- `openspec/specs/agent-discovery-registry/spec.md`.

**Rationale:** Those files are part of the same reader journey as the new system-files subtree. Leaving them stale would mean the repo still gives contradictory answers even after the new reference pages land.

**Alternatives considered:**

- Create a separate docs/spec cleanup change for the `agent_id` leftovers. Rejected because it would split one consistency problem across parallel editorial changes touching the same registry surfaces.

### 9. Resolve the packaged v1 registry schema artifact explicitly

**Decision:** The implementation will inspect the still-packaged `live_agent_registry_record.v1.schema.json` artifact and resolve its status explicitly instead of leaving it ambiguous.

Preferred resolution order:

1. remove the file if code, tests, and live docs confirm it is not part of the active supported contract,
2. otherwise retain it only with explicit historical or non-current labeling in the surrounding docs/specs so readers do not mistake it for the active registry schema.

The change does not need to preserve the file merely because it exists today, because repository guidance already allows breaking cleanup when legacy compatibility is not an explicit requirement.

**Rationale:** The issue is not just wording. A packaged schema artifact can itself imply support. The repo should make that support status unambiguous.

**Alternatives considered:**

- Leave the v1 schema file untouched and only adjust prose. Rejected because the package contents would still imply a current supported structural contract.
- Remove the file unconditionally without checking for live uses. Rejected because the repo should still confirm that it is truly non-current before deleting a shipped artifact.

## Risks / Trade-offs

- **[Risk] The centralized subtree could become a second vague overview instead of a concrete operator reference.** → Mitigation: require explicit path trees, artifact tables, and contract-level labeling on each page.
- **[Risk] Subsystem pages may still drift if they keep repeating too much layout detail.** → Mitigation: update those pages in the same change so they link out for full filesystem maps and keep only local examples.
- **[Risk] Readers may expect the new subtree to document every file CAO or tool CLIs create under selected homes.** → Mitigation: explicitly mark external-tool-owned subtrees as opaque beyond the parts Houmao selects or depends on.
- **[Trade-off] The new subtree adds another reference section to navigate.** → Mitigation: add it to the top-level reference index and make it the clear destination for filesystem preparation questions.
- **[Trade-off] Some existing pages will become slightly more link-heavy.** → Mitigation: keep concise local artifact references where they materially help understanding and use links only for the broader filesystem map.

## Migration Plan

1. Add the new `docs/reference/system-files/` subtree and write the entrypoint plus the detailed pages for ownership boundaries, runtime/session files, CAO launcher files, shared registry files, and operator preparation.
2. Update `docs/reference/index.md` so the new subtree is top-level discoverable.
3. Simplify the broad runtime and launcher pages first: `docs/reference/realm_controller.md`, `docs/reference/cao_server_launcher.md`, and the agent pages that currently carry canonical artifact trees.
4. Update the `docs/reference/registry/` and selected `docs/reference/gateway/` pages so they keep subsystem-specific contracts but defer the broader Houmao filesystem map to the centralized subtree.
5. Update the live OpenSpec main specs that still describe `agent_key` or v1 registry semantics as current.
6. Resolve the status of the packaged `live_agent_registry_record.v1.schema.json` artifact.
7. Remove or tighten duplicated filesystem explanations and correct stale terminology that would otherwise compete with the centralized reference.

Rollback is straightforward because this change does not alter runtime behavior:

- remove the new subtree,
- restore the older inline explanations if needed,
- restore any removed non-current packaged schema artifact if that artifact cleanup turns out to have been premature,
- no runtime or storage migration is required.

## Open Questions

- None for artifact creation. The main follow-through question is editorial: how much local artifact detail each subsystem page should retain after the central reference exists. The implementation can resolve that by keeping only the detail needed for local comprehension and moving broader filesystem maps into `docs/reference/system-files/`.
