## Context

Gemini exists as both a nominal interactive provider (`gemini_cli`) and a maintained headless backend (`gemini_headless`). Its support crosses provider adapters, launch planning, runtime dispatch, schemas, gateway and passive-server paths, credentials, project authoring, model selection, launch policy, starter assets, demos, tests, docs, and system-skill projection under `.gemini/skills`.

The repository is under active development. No user will rely on Gemini CLI in the next release, so the provider can be deleted without compatibility or migration work. The desired end state is a maintained provider set of Claude Code, Codex, and Kimi Code.

## Goals / Non-Goals

**Goals:**

- Remove Gemini TUI/local-interactive compatibility and headless runtime support.
- Remove Gemini from every public and internal provider choice used by maintained workflows.
- Delete Gemini-specific modules, launch policy, starter assets, tracked fixtures, demos, tests, docs, and system-skill guidance.
- Make new Gemini requests fail as unsupported input at the nearest typed or CLI boundary.
- Keep Claude, Codex, and Kimi behavior unchanged except where provider lists and shared parametrized tests become smaller.
- Leave no maintained runtime import, enum, schema value, CLI option, skill path, or documentation claim that implies Gemini support.

**Non-Goals:**

- Reading, migrating, cleaning, or explaining state created by older Gemini-capable releases.
- Preserving Gemini aliases, parsers, tombstones, rejection branches, or retirement messages.
- Rewriting archived OpenSpec changes or immutable historical review logs that accurately describe earlier repository behavior.
- Deleting untracked developer state under `.houmao/`, `.pixi/`, caches, or external user homes.
- Removing generic safety advice that mentions `.gemini` only as a third-party local-state directory to avoid copying or symlinking, when that advice does not claim Houmao provider support.

## Decisions

### Delete the provider lane instead of leaving disabled adapters

Gemini-specific backend modules, registry YAML, provider adapters, starter assets, fixture trees, and dedicated reference pages will be deleted. Shared registries, enums, dispatch tables, schemas, and command choices will omit Gemini entirely.

No tombstone or disabled adapter remains. Once shared enums and registries drop Gemini, any raw Gemini value is merely outside the schema, like any other unknown string.

### Put all older Gemini state outside the release contract

Current schemas remove `gemini`, `gemini_cli`, and `gemini_headless`. The implementation does not read old Gemini manifests to provide a better error, clean old Gemini homes, translate old profiles, or test old-state behavior.

### Remove both interactive compatibility and headless support

The implementation will remove Gemini from CAO compatibility providers, native launch resolution, local-interactive process recognition, shared TUI ownership, passive observation, headless bridge choices, runtime dispatch, and all headless backend collections. This prevents a partial removal in which one posture remains reachable through a lower-level API.

Gemini currently lacks an official shared TUI tracker profile, but compatibility and process-recognition code still creates a TUI-facing surface. That residual surface is part of the removal.

### Remove Gemini credentials and generated home construction at the source

Credential commands will accept only Claude, Codex, and Kimi. Gemini flags and file mappings will be deleted from easy specialist creation, auth-profile storage, credential login/import, brain construction, model mapping, starter tool assets, and test fixtures.

The shared encrypted auth fixture archive will be regenerated without Gemini bundle entries when the local archive password is available. If the password is unavailable during implementation, the change cannot claim fixture cleanup complete; the task remains open rather than silently retaining Gemini credentials in the tracked archive.

### Remove Gemini from system-skill targeting and instruction content

System-skill destination resolution, installation, status, synchronization, and uninstall will no longer accept Gemini or target `.gemini/skills`. Gemini-only credential references will be deleted. Active skill pages that list providers, credential routes, profiles, specialist flags, launch modes, or examples will be rewritten for Claude, Codex, and Kimi.

Generic workspace safety guidance may continue to recognize `.gemini` as third-party local state when the rule is about avoiding unsafe copying rather than supporting Gemini as a Houmao provider.

### Update maintained documentation and delete dedicated Gemini material

README files, CLI references, getting-started guides, build/run-phase references, mailbox docs, context feature designs, root agent guidance, and demo indexes will use the remaining provider set. `GEMINI.md`, maintained Gemini issue/knowledge pages, the dedicated legacy Gemini demo, and other Gemini-only current material will be deleted when they exist only to support that provider.

Archived OpenSpec changes remain untouched. Historical context logs may retain factual references, but maintained indexes must not route readers toward retired Gemini workflows.

### Preserve shared behavior with negative and remaining-provider tests

Tests will remove Gemini-positive cases and fixtures. Replacement coverage will assert that public provider choices omit Gemini, raw Gemini identifiers fail validation, Gemini modules/assets are absent, and provider-parametrized paths still cover Claude, Codex, and Kimi.

The verification pass will use repository-wide searches over maintained roots. Search exclusions must be explicit and limited to archives, immutable historical logs, build caches, external dependencies, and untracked runtime state.

### Implement removal from leaves toward shared boundaries

Implementation will first remove dedicated demos, fixtures, skills, assets, registry entries, and backend modules. It will then update dispatch, schemas, shared provider collections, commands, and tests. Documentation and global audits come after the executable surface is coherent.

This order reduces intermediate import failures and makes remaining Gemini references easier to classify.

## Risks / Trade-offs

- [A shared provider tuple keeps Gemini after the backend file is deleted] → Update typed collections, schemas, dispatch tables, and command choices in the same implementation section, then run import and CLI-shape tests.
- [Removing Gemini cases weakens shared headless coverage] → Keep shared tests parametrized across Claude, Codex, and Kimi and add provider-set assertions.
- [Encrypted fixture archive still contains Gemini material] → Regenerate and verify the archive checksum before completing the fixture task.
- [A documentation search reports historical references] → Define maintained-root and historical-root audits separately. Do not rewrite archived OpenSpec history.
- [System skills retain indirect Gemini routing] → Search all packaged `SKILL.md`, action, subskill, and reference files, then run catalog and content tests.
- [Deleting `GEMINI.md` removes a repository agent entrypoint] → This is intentional and requires no replacement.
- [Generic `.gemini` safety references are mistaken for provider support] → Retain only references whose surrounding contract is provider-neutral local-state safety, and document that exception in the audit.

## Migration Plan

There is no migration plan. The change lands as one breaking deletion before the next release:

1. Delete Gemini-only leaves and remove Gemini from shared executable surfaces.
2. Update remaining-provider tests, docs, skills, and fixtures.
3. Regenerate the encrypted auth fixture archive without Gemini entries.
4. Run the full verification and maintained-root audit.

Rollback, if needed during development, is a source-control revert of the complete change.

## Open Questions

- None. Historical archives stay unchanged, maintained Gemini material is deleted, and fixture archive cleanup is required before completion.
