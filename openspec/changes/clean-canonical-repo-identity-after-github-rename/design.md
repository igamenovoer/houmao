## Context

The repository has already completed the main public rename from `gig-agents` / `gig-agents-cli` / `brain_launch_runtime` to `Houmao` / `houmao-cli` / `realm_controller`, and the GitHub repository itself has now been renamed to `houmao`. Even so, several active-facing files still carry the old project name, old GitHub slug, old runtime path, or the old `gig_agents` Python package root. The package distribution is already named `Houmao`, but the install-time Python module surface, source tree, docs, and repo-owned scripts still mostly teach `gig_agents...`.

That mismatch is deeper than docs. The current package root appears in build metadata, entrypoint targets, `python -m ...` command examples, absolute imports, `importlib.resources.files(...)` package lookups, lazy import strings, subprocess module-launch strings, monkeypatch targets in tests, and generated runtime helper snippets written by the brain builder. The rename therefore has both mechanical and migration-facing consequences.

The repo also contains a large amount of historical material: migration reports, archived OpenSpec changes, review artifacts, discussion records, and context notes with observed local absolute paths. Those references are not all bugs. Some are preserving provenance, and some deliberately describe the old-to-new transition. But the user-facing boundary is now stricter: shipped source under `src/`, shipped documentation under `README.md` and `docs/`, and published CLI/help surfaces are not historical artifacts and should not expose the old names at all.

That means this cleanup needs an explicit policy line. Without one, maintainers will either keep leaking old active guidance forward or overcorrect and rewrite useful history.

## Goals / Non-Goals

**Goals:**
- Define one canonical repository identity for active-facing metadata, contributor guidance, assistant instruction files, and repo-owned instructional docs.
- Align the canonical Python package namespace, source tree, and module-entrypoint examples with `houmao`.
- Remove the historical `gig_agents`, `gig-agents`, and `gig-*` identities from user-facing source code, docstrings, CLI names/help, and shipped documentation.
- Align active metadata and guidance with the current GitHub repository slug and the already-approved Houmao naming surface.
- Define a path-reference policy for active instructional docs so rerunnable examples do not depend on one maintainer's checkout path.
- Preserve clear historical and provenance exceptions only in non-user-facing archive or internal-record material instead of forcing a zero-match grep outcome everywhere.

**Non-Goals:**
- Renaming the local checkout directory in the current workspace.
- Rewriting `context/logs/`, archived OpenSpec history, or other clearly non-user-facing materials whose primary purpose is to preserve observed history.
- Renaming runtime subcommands or the already-approved `realm_controller` module naming.
- Preserving `gig_agents` as a long-lived compatibility namespace for imports or `python -m gig_agents...` entrypoints.
- Replacing machine-required absolute paths in tool-specific contracts unless the consumer can be proven to support a safer alternative.

## Decisions

### 1. Canonicalize the Python package root as `houmao` without a long-lived `gig_agents` compatibility tree

The canonical Python package namespace will become `houmao`, with the source tree under `src/houmao/`. Repo-owned imports, module-entrypoint examples, package-resource lookups, and build metadata will be updated to that namespace.

This change will not keep a mirrored `src/gig_agents/` compatibility package as an ongoing supported surface. A top-level alias would not be enough anyway because nested imports, `python -m gig_agents...` entrypoints, monkeypatch targets, and package-resource discovery all depend on real module paths deeper in the tree. A full compatibility mirror would double the maintained surface area and cut against the repository's bias toward forward progress over compatibility shims.

Alternatives considered:
- Keep the distribution name `Houmao` but preserve `gig_agents` as the import root indefinitely: rejected because it freezes the naming split in the most operationally important surface.
- Add a transitional compatibility package tree under `src/gig_agents/`: rejected because the repo currently allows breaking changes and the alias tree would be broad, fragile, and expensive to maintain.

### 2. Treat all user-facing surfaces as a zero-historical-name zone

Shipped source code, exported docstrings, CLI binary names, CLI help text, and shipped documentation should not expose `gig_agents`, `gig-agents`, or `gig-*` names after this change. This includes the remaining launcher CLI binary, which should be renamed from `gig-cao-server` to `houmao-cao-server`.

Rationale:
- A user should not need to learn or even notice the historical project/module name to use the current project.
- Leaving the old names in user-facing strings would make the rename feel partial and internally inconsistent even if imports were updated.

Alternatives considered:
- Allow historical names in some user-facing docs as migration breadcrumbs: rejected because the stated product goal is that users should not be expected to know the old name.
- Rename imports but keep `gig-cao-server` as a convenience binary: rejected because CLI tool names are among the most visible user-facing surfaces.

### 3. Treat active metadata and assistant guidance as highest-priority canonical surfaces

Files that actively shape future edits or external consumers should be fully canonical after this change. That includes `pyproject.toml` project URLs, `CLAUDE.md`, `.github/copilot-instructions.md`, and similar contributor or AI-assistant guidance.

Rationale:
- These files are read repeatedly and can reintroduce stale naming into future work.
- Metadata URLs are externally visible and should match the canonical GitHub repository rather than relying on redirects.

Alternatives considered:
- Only update human-facing docs and leave assistant guidance alone: rejected because those files are among the strongest drift multipliers.
- Rely on GitHub redirects for old URLs indefinitely: rejected because redirects are not the canonical contract and can be invalidated later.

### 4. Treat module-path strings and generated helpers as first-class rename surfaces

The rename will explicitly cover not just `import ...` statements, but every string-encoded module reference that acts like part of the public or runtime contract. That includes:
- `python -m ...` command examples in docs and scripts
- subprocess module-launch strings
- lazy import/export tables
- `importlib.resources.files(...)` package names
- monkeypatch targets and asserted module names in tests
- generated bootstrap helper snippets emitted into built runtime homes

Rationale:
- These surfaces do not get fixed automatically by moving the directory tree.
- Missing even one of them can leave the package rename apparently complete while runtime behavior or packaged assets still break.

Alternatives considered:
- Limit the rename to directory moves and import rewrites only: rejected because too much of the runtime and demo surface uses string-based module references.

### 5. Use repo-relative paths or explicit `<repo-root>` placeholders for active instructional guidance

When a file is teaching the reader how to run commands, inspect files, or navigate the repo, it should avoid host-specific absolute checkout paths when a repo-relative path or `<repo-root>` placeholder conveys the same meaning.

Rationale:
- Host-specific absolute paths are hard to copy, stale after checkout renames, and make active docs look more historical than instructional.
- Relative paths and placeholders travel better across machines and clones.

Alternatives considered:
- Keep all current absolute paths because they are technically accurate in one checkout: rejected because they do not generalize and invite future stale references.
- Eliminate every absolute path everywhere: rejected because some files intentionally preserve observed output or machine-specific state.

### 6. Generated runtime homes may require rebuild, but persisted launcher ownership records can remain readable

Previously built runtime homes may contain bootstrap helper snippets that import `gig_agents...`. After the package rename, those generated helpers should be treated as rebuild-required artifacts rather than something the repo must keep compatible forever.

For CAO standalone launcher ownership artifacts, new writes should use the canonical module identifier `houmao.cao.server_launcher`. Existing ownership files can remain readable because the current parser validates `managed_by` as a non-empty string rather than matching a single exact value.

Rationale:
- Brain homes and generated helpers are disposable runtime artifacts and align well with rebuild-on-change expectations.
- Ownership artifact parsing is already tolerant enough to carry old records across the rename without extra compatibility code.

Alternatives considered:
- Freeze ownership metadata at the old string forever: rejected because it would intentionally preserve stale identity in newly written runtime artifacts.
- Keep runtime-home compatibility by carrying the old package tree: rejected for the same reasons as the general compatibility-tree alternative.

### 7. Preserve history-oriented references only in non-user-facing provenance material

Archived OpenSpec artifacts, internal review records, internal context notes, and clearly labeled observed diagnostic output may retain old repo names, old module names, or old checkout-local paths when that is necessary to preserve what actually happened.

Shipped source files, exported docstrings, CLI help, `README.md`, and pages under `docs/` are not historical exceptions, even when they describe migrations or prior behavior.

Rationale:
- The repository already relies on archive and discussion artifacts as historical records.
- Rewriting those records into present-tense canonical language would blur chronology and make later investigation harder.

Alternatives considered:
- Demand zero remaining matches for old names: rejected because it conflates active guidance with historical evidence.
- Exempt everything outside top-level docs: rejected because active contributor and assistant guidance would remain inconsistent.

### 8. Use an explicit user-facing-versus-historical policy for borderline files

Files that mix instruction with observed paths or rename history should be judged by their primary purpose:
- if the reader is meant to use the current product or code now, prefer canonical names and portable paths and avoid historical-name leakage entirely;
- if the artifact is a non-user-facing record meant to preserve a past event, preserve the original wording and paths, ideally with clarifying labels.

Rationale:
- Some `context/` and migration files are neither pure docs nor pure history.
- A purpose-based rule is easier to apply consistently than a directory-only rule.

Alternatives considered:
- Classify by directory alone: rejected because `context/` and `docs/migration/` contain both active and historical material.

## Risks / Trade-offs

- [Policy boundary feels subjective for mixed-purpose files] → Mitigation: define the user-facing-versus-historical rule in specs with concrete examples and treat `README.md`, `docs/`, CLI help, and shipped source/docstrings as always user-facing.
- [External consumers using `import gig_agents` or `python -m gig_agents...` will break] → Mitigation: make the break explicit in docs/specs and do not dilute the rename with a partial alias that only handles some cases.
- [Previously generated runtime homes may contain stale bootstrap imports] → Mitigation: document that generated helpers are rebuild-required after the package rename and verify fresh build/start flows only against the new `houmao` package root.
- [Users may still encounter a `gig-*` launcher binary and infer a split identity] → Mitigation: rename the launcher CLI binary to `houmao-cao-server` as part of this change and sweep user-facing docs/help for the old binary name.
- [Some absolute paths remain in machine-oriented local tooling docs] → Mitigation: explicitly document that such exceptions require consumer justification rather than default acceptance.
- [String-encoded module references are easy to miss] → Mitigation: include targeted sweeps for `python -m gig_agents`, `resources.files(\"gig_agents`, asserted module strings, and monkeypatch targets in verification.
- [Future renames may re-open the same cleanup work] → Mitigation: treat canonical repo identity and path portability as an ongoing contract rather than a one-off sweep.
- [Maintainers may still over-clean archive text] → Mitigation: keep archive/provenance exceptions explicit in the new capability requirements.

## Migration Plan

1. Expand the repo-identity proposal/specs to make `houmao` the canonical Python package namespace and to update capability specs that currently declare `gig_agents` package paths as canonical.
2. Rename the source package tree and build metadata from `src/gig_agents` to `src/houmao`, including entrypoint targets, user-facing CLI binaries, and packaged-resource lookup paths.
3. Rewrite internal imports, string-based module references, generated helper snippets, repo-owned scripts, tests, shipped docstrings, CLI help/output references, and docs to the `houmao...` namespace.
4. Apply the path policy to active instructional docs and selected active `context/` notes, using placeholders or repo-relative paths where appropriate, while keeping `README.md` and `docs/` free of historical-name leakage.
5. Verify the new module-entrypoint surfaces (`python -m houmao...`), the renamed user-facing CLI binaries, and confirm remaining `gig_agents`, `gig-agents`, or `gig-*` references are confined to non-user-facing historical/provenance exceptions or machine-required local-path contracts.
6. Document any rebuild-required generated artifacts instead of preserving runtime compatibility shims for the old namespace.

## Open Questions

- Whether `AGENTS.md`-style absolute links used for tool-local clickable references should stay absolute or move to a different portable convention depends on the consumer expectations for those files.
