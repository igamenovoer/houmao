## Context

This rename crosses packaging metadata, runtime source layout, tests, docs, scripts, context notes, and OpenSpec artifacts. The current repository still exposes the older public names `gig-agents`, `gig-agents-cli`, and `brain_launch_runtime`, while the naming rationale under `context/design/namings/` has already identified `Houmao` and `realm_controller` as the intended replacements.

The repo is also explicit that breaking changes are acceptable during active development. That makes a one-pass rename preferable to compatibility shims, but the user has requested a narrow scope: rename the project, rename only the main CLI tool, rename `brain_launch_runtime` to `realm_controller`, and update related docs/specs/context without expanding into subcommand, package-root, protocol, or broad class/function renames.

## Goals / Non-Goals

**Goals:**
- Present one consistent project identity, `Houmao`, across packaging, README/docs, contributor guidance, and repository knowledge outside excluded logs.
- Rename the primary operator CLI to `houmao-cli` while preserving the existing runtime subcommand vocabulary.
- Rename the runtime module surface from `gig_agents.agents.brain_launch_runtime` to `gig_agents.agents.realm_controller` across source, tests, docs, scripts, and spec references.
- Keep OpenSpec contracts aligned with the intended public naming so future work does not continue to reference superseded names.
- Make the chosen narrow scope explicit in the rationale docs so future edits do not reintroduce the broader rejected renames.

**Non-Goals:**
- Renaming the Python package/import root `gig_agents`.
- Renaming `gig-cao-server`.
- Renaming runtime subcommands such as `build-brain`, `start-session`, `send-prompt`, `send-keys`, `mail`, or `stop-session`.
- Renaming runtime env var families or identity prefixes such as `AGENTSYS_*`.
- Renaming non-module class or function identifiers solely for lore consistency.
- Rewriting `context/logs/` or historical artifacts whose purpose is to preserve exact prior execution history.

## Decisions

### 1. Rebrand the project and distribution, but keep the Python import root stable

The repository-facing name will become `Houmao`, and the installable distribution / console-script metadata will be updated accordingly. The Python import root will remain `gig_agents` in this change.

Rationale:
- The user explicitly scoped the rename to the project name, the primary CLI, and the runtime module.
- Renaming the import root would expand the change into a separate packaging and downstream-consumer migration.
- Keeping `gig_agents` stable allows a narrower breaking surface while still delivering the intended public rebrand.

Alternatives considered:
- Rename the package root to `houmao`: rejected because it would enlarge the migration significantly and was not requested.
- Keep the existing distribution name while only changing docs: rejected because packaging metadata would continue to advertise the old identity.

### 2. Rename the main console script to `houmao-cli` without changing the command vocabulary beneath it

Only the top-level runtime CLI executable name will change. Existing subcommands and flags will remain intact.

Rationale:
- This matches the user's request to rename the CLI tool only, not its subcommands.
- Preserving subcommands minimizes command-surface churn while still moving the operator entrypoint to the new brand.
- It keeps current docs, demos, and tests close to their existing workflow semantics.

Alternatives considered:
- Adopt the broader lore-driven command set from `context/design/namings/` such as `pluck`, `spawn`, and `recall`: rejected because it exceeds the requested scope.
- Ship both `gig-agents-cli` and `houmao-cli`: rejected because the repo allows breaking changes and the user asked for a rename, not a compatibility alias.

### 3. Rename the runtime module tree to `realm_controller` and update all direct path references

The source tree `src/gig_agents/agents/brain_launch_runtime/` will be renamed to `src/gig_agents/agents/realm_controller/`. Direct imports, `python -m ...` examples, runtime-related doc filenames, test directories, and other explicit path references will move with it.

Rationale:
- The user explicitly requested renaming `brain_launch_runtime` to `realm_controller`.
- Keeping only textual docs updated while leaving source/test paths unchanged would preserve the old public module surface and create ongoing ambiguity.
- Renaming the entire module tree in one pass gives the repo a single authoritative runtime name.

Alternatives considered:
- Keep the directory name and only rename documentation headings: rejected because the old module name would remain the real public surface.
- Add `realm_controller` as an alias module that re-exports `brain_launch_runtime`: rejected because it prolongs mixed naming and adds compatibility code the repo does not need right now.

### 4. Treat runtime doc page filenames and link targets as part of the rename

Runtime doc pages and references that currently use `brain_launch_runtime` in filenames or links will be renamed alongside the module, for example `brain_launch_runtime.md` to `realm_controller.md` and `brain_launch_runtime_send_keys.md` to `realm_controller_send_keys.md`.

Rationale:
- Leaving old filenames in place would continue to teach the superseded runtime name even if the page titles were updated.
- The docs already use many direct Markdown links and source-path references, so a coordinated filename update is more coherent than partial title-only edits.

Alternatives considered:
- Keep old filenames and only change page titles: rejected because it bakes mixed terminology into the docs structure.

### 5. Update active and archived OpenSpec/body text carefully, but preserve archive identities and provenance paths where history matters

Active OpenSpec specs and change-local artifacts will use the new names where they define current behavior. Archived OpenSpec body text may be updated when it is describing the current public surface or linking to living files, but archived change IDs, archive directory names, and clearly historical provenance narratives will remain stable.

Rationale:
- The user asked to revise related specs in `openspec/`.
- Archive directory IDs are historical identifiers and renaming them adds churn with little value.
- Some archived body text contains living links or still serves as reference material, so leaving all of it untouched would preserve avoidable confusion.

Alternatives considered:
- Rename all archived change IDs and spec folder names: rejected because it risks breaking historical references and tooling expectations.
- Leave all archived text untouched: rejected because a large amount of archived material still functions as active reference and would keep reintroducing the old names.

### 6. Normalize instructional path examples, but avoid rewriting historical observed absolute paths unless they are meant to be followed

Active instructional docs and context notes that hardcode repo paths should prefer placeholders or updated examples where the reader is expected to execute the steps. Historical notes that record a past observed path may remain verbatim when preserving exact history is more important than renaming.

Rationale:
- Some docs contain literal `/.../gig-agents/...` paths that would become stale or misleading if copied as instructions.
- Other files are explicitly historical issue or review records and should not be cosmetically rewritten in ways that blur what actually happened.

Alternatives considered:
- Replace every absolute path occurrence mechanically: rejected because it would rewrite historical evidence and review context.
- Ignore path literals entirely: rejected because active instructional material would keep teaching outdated paths.

### 7. Rewrite the naming-rationale notes to document the chosen narrow scope

`context/design/namings/` will be updated so it no longer recommends broader CLI, class, and concept renames that conflict with the approved scope.

Rationale:
- Those notes are part of the repository context the user explicitly asked to revise.
- Leaving them as-is would create internal contradiction immediately after the rename lands.

Alternatives considered:
- Leave the rationale docs unchanged as abandoned exploration: rejected because they currently read like active recommendations.

## Risks / Trade-offs

- [Mixed naming remains because `gig_agents` stays] → Mitigation: document the package-root non-goal explicitly in proposal, design, specs, and updated rationale notes.
- [Runtime path rename breaks imports, tests, and doc links] → Mitigation: perform the rename as a coordinated tree move, then run targeted sweeps for import strings, `python -m` examples, and Markdown links.
- [OpenSpec archive edits could blur historical provenance] → Mitigation: preserve archive IDs and obviously historical narratives while limiting text updates to living references or current-surface descriptions.
- [Packaging metadata may become inconsistent across project name, editable dependency name, and scripts] → Mitigation: update the related packaging fields together and refresh lock/build outputs after the rename.
- [Broader lore-driven renames may creep back in later] → Mitigation: record the explicit non-goals and revise `context/design/namings/` to match the approved scope.

## Migration Plan

1. Add change-local specs that define the new project/CLI identity and the renamed runtime surface.
2. Apply the implementation in one pass: packaging metadata, runtime module tree, tests, docs, scripts, context, and relevant OpenSpec text.
3. Rename runtime reference page filenames and update all internal links and source-file references that point at the old names.
4. Refresh generated packaging metadata as needed and run targeted verification for imports, CLI help, docs link surfaces, and runtime tests.
5. If the rename proves problematic before release, revert the change as one unit rather than adding compatibility aliases.

## Open Questions

- No blocking technical questions remain for proposal time. The main scope boundaries are intentionally fixed by this design: package-root stability, no subcommand rename, no CAO launcher rename, and no historical log rewrite.
