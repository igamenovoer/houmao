## Context

The repository currently has two CAO-era demo packs that are still treated as active user-facing workflows: `scripts/demo/cao-server-launcher/` and `scripts/demo/cao-interactive-full-pipeline-demo/`. That no longer matches the product posture. The standalone launcher CLI is already a fail-fast retirement shim, and the interactive workflow has a maintained replacement at `scripts/demo/houmao-server-interactive-full-pipeline-demo/`.

This retirement needs a narrow boundary. Some code under `src/houmao/demo/cao_interactive_demo/` is still imported by maintained packs, and the internal launcher library under `houmao.cao.server_launcher` is still used by pair-owned child-CAO behavior. The user explicitly wants the retirement limited to the demo packs and demo-owned source, without touching shared code used by other modules.

## Goals / Non-Goals

**Goals:**
- Remove the two retired demo-pack directories and their active docs/test/spec surfaces.
- Remove workflow-specific source code that exists only for the retired interactive CAO demo.
- Preserve repo coherence by updating active docs and OpenSpec requirements to stop describing the retired packs as supported workflows.
- Keep any shared or internally reused helper code in place when maintained modules still depend on it.

**Non-Goals:**
- Removing or refactoring `houmao.cao.server_launcher` or other shared CAO support code used outside the retired demos.
- Migrating maintained tutorial packs away from shared helper imports or away from the internal launcher library.
- Cleaning historical archives, resolved issues, or archived OpenSpec changes that reference the retired demos.
- Broadly redesigning CAO compatibility strategy outside the scope of these two demo packs.

## Decisions

### 1. Retire the demo packs by deleting their active surfaces rather than leaving dormant wrappers

The change will remove the tracked demo-pack directories, active docs links, active tests, and active spec contracts for the two retired CAO demo packs.

Rejected alternative: keep the directories with failure-only wrapper scripts. That still advertises a supported surface and forces the repo to keep tests, docs, and spec language around a workflow we want gone.

### 2. Preserve shared helpers even if they currently live under the retired interactive demo package

The change will only remove source modules in `src/houmao/demo/cao_interactive_demo/` that are exclusive to the retired workflow. Helper modules or helper functions that maintained packs still import will remain in place for now, even if they still live under the legacy package path.

Rejected alternative: delete the entire `cao_interactive_demo` package. That would force unrelated maintained packs to migrate in the same change and violates the requested scope boundary.

### 3. Treat the maintained Houmao-server interactive demo as the replacement path for active operator guidance

Active docs that currently point to the retired interactive CAO pack will be redirected to `scripts/demo/houmao-server-interactive-full-pipeline-demo/` or to existing retirement-reference pages where appropriate.

Rejected alternative: replace retired references only with generic retirement text. That removes the stale guidance but leaves no maintained walkthrough for the same operator use case.

### 4. Retire demo-only tests instead of rewriting them around failure behavior

Tests whose only purpose is to validate the retired CAO demo packs will be removed with the demos. This change will not replace them with assertions that the deleted packs fail or remain absent.

Rejected alternative: keep tests around absence or failure stubs. That adds maintenance cost without preserving useful behavior.

## Risks / Trade-offs

- [Risk] Some interactive-demo modules are partly reused outside the retired demo. -> Mitigation: only remove workflow-exclusive modules and audit imports before deleting package files.
- [Risk] Active docs may still contain stale links after the scripts are removed. -> Mitigation: update README and active docs indexes in the same change that removes the demo directories.
- [Risk] The maintained Houmao-server replacement is less discoverable today than the retired CAO demo. -> Mitigation: redirect active docs to the maintained replacement rather than only deleting old links.
- [Risk] Historical files will still mention the retired demos. -> Mitigation: keep archival and provenance material unchanged and limit this change to active surfaces.

## Migration Plan

1. Remove the active OpenSpec requirements for the two demo packs and their dedicated interactive-demo sub-capabilities.
2. Update active docs and indexes to remove the retired pack links and route readers to maintained replacements or retirement notes.
3. Delete the retired demo-pack directories and their dedicated tests.
4. Delete only the interactive-demo workflow modules that are exclusive to the retired pack, leaving shared helper modules untouched.
5. Verify that active searches no longer show the retired packs as supported workflows.

## Open Questions

- Which exact modules in `src/houmao/demo/cao_interactive_demo/` are still needed as shared helpers after the demo workflow is removed, and should they gain a follow-up migration change later?
- Should a dedicated docs reference page be added for the maintained Houmao-server interactive demo, or is redirecting active links straight to the demo-pack README sufficient for this retirement?
