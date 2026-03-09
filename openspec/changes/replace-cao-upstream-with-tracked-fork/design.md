## Context

`gig-agents` currently mixes three different CAO reference styles in active guidance:

1. orphan-path references copied from a host workspace layout such as `extern/orphan/cli-agent-orchestrator`,
2. upstream GitHub URLs under `awslabs/cli-agent-orchestrator`, and
3. generic package-name install hints such as `uv tool install cli-agent-orchestrator`.

That drift shows up in:

- `README.md`,
- launcher and demo troubleshooting strings,
- active issue notes under `context/issues/known/`, and
- OpenSpec specs that still name orphan/upstream CAO sources as the contract reference.

The runtime architecture itself is not changing: `gig-agents` still launches or talks to `cao-server` as an external executable on `PATH`. The problem is the source/install narrative around that external dependency.

## Goals / Non-Goals

**Goals:**

- Establish the CAO fork as the canonical repository source referenced by active `gig-agents` guidance.
- Standardize active CAO install and `uvx --from` guidance on a fork-backed source.
- Remove orphan-path CAO references from active `gig-agents` operational docs/specs/notes.
- Preserve only intentionally required provenance/licensing references to original upstream origin.

**Non-Goals:**

- Changing CAO runtime behavior, API semantics, or process-management logic.
- Rewriting archived OpenSpec history in this repo.
- Making `gig-agents` import CAO directly from a local checkout.
- Solving fork governance/support ownership beyond what must be stated explicitly in active docs.

## Decisions

### 1. Use fork repository references in active `gig-agents` guidance

Active `gig-agents` docs/specs/notes will reference the CAO fork repository identity (`imsight-forks/cli-agent-orchestrator`) rather than orphan-path references from a containing workspace.

Rationale:

- `gig-agents` is a standalone repo, so active guidance should not depend on a host workspace layout that may not exist.
- Repository URLs are portable across standalone use and submodule use.

Alternative considered:

- Replace orphan-path references with another host-workspace local path.
- Rejected because it would keep `gig-agents` docs tied to one embedding layout.

### 2. Keep runtime behavior path-based, but standardize install guidance

The runtime, launcher, and demos will continue to require `cao-server` on `PATH`, but active guidance will standardize on a fork-backed CAO installation source rather than the generic package-name install or upstream Git URL.

Rationale:

- Current launcher design intentionally treats CAO as an external executable.
- The ambiguity is about how users obtain that executable, not how `gig-agents` invokes it.

Alternative considered:

- Change runtime behavior to execute CAO from a local checkout.
- Rejected because it would change ownership boundaries and complicate operator workflows.

### 3. Scope the migration to active guidance plus explicit exceptions

The migration will update active operational docs/specs/issue notes and launcher/demo messages. Provenance/licensing text and archived history may remain explicit where they are intentionally documenting origin rather than serving as current operational guidance.

Rationale:

- Active users need a single current story.
- Provenance and historical context still matter in a forked project.

Alternative considered:

- Rewrite every upstream/orphan mention everywhere.
- Rejected because it would over-scope the change and blur the difference between current guidance and historical record.

## Risks / Trade-offs

- [Mixed support surfaces] -> Separate normal operational links from governance/security links during review so we do not promise ownership the fork has not adopted.
- [Ambiguous install contract] -> Standardize one fork-backed command family in README, docs, demo guidance, and launcher error messages.
- [Issue-note provenance loss] -> Preserve explicit wording when an issue note documents behavior first observed in upstream-derived CAO while still updating its actionable source references.
- [Verification false positives] -> Verify active docs and guidance separately from explicit provenance/archive exceptions.

## Migration Plan

1. Update active `gig-agents` CAO docs/specs/notes to use fork-oriented repository references and remove orphan-path references.
2. Update launcher/demo install and troubleshooting guidance to use the selected fork-backed install contract.
3. Review active issue notes and provenance-facing files to preserve only intentionally explicit upstream-origin wording.
4. Re-run targeted sweeps for orphan/upstream/package-name install references and confirm only approved exceptions remain.

## Open Questions

- Final decision on the exact fork-backed install command and which governance/support links should remain explicit is captured in the discuss doc for this change.
