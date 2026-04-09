## 1. Catalog And Storage Model

- [x] 1.1 Replace the auth-profile catalog schema with mutable display names, immutable opaque bundle refs, and auth-profile-id-backed relationships for downstream records.
- [x] 1.2 Remove specialist-owned auth-name authority and update catalog views/loaders so specialist inspection derives the current auth display name from the referenced auth profile.
- [x] 1.3 Store managed auth content and derived auth projections under opaque bundle-ref paths and make auth projection materialization prune stale bundle-ref keyed auth directories.

## 2. Auth Command Surface

- [x] 2.1 Refactor `project agents tools <tool> auth list|get|add|set|remove` to resolve auth profiles through catalog-backed helpers instead of scanning `.houmao/agents/tools/<tool>/auth/` as the source of truth.
- [x] 2.2 Implement `houmao-mgr project agents tools <tool> auth rename` with display-name uniqueness checks and rename-stable auth identity semantics.
- [x] 2.3 Preserve the existing Claude, Codex, and Gemini env/file patch behavior while writing those payloads through the new catalog-owned auth storage model.

## 3. Downstream Auth Relationships

- [x] 3.1 Update explicit launch-profile persistence and inspection so auth overrides are stored by auth profile identity and continue to resolve after auth rename.
- [x] 3.2 Update `project easy` specialist/profile/instance flows so `--credential` and `--auth` remain display-name inputs while runtime resolution uses the referenced auth profile identity.
- [x] 3.3 Update packaged system-skill assets and related CLI help text so auth-management guidance includes `rename` and stops treating auth directory names as meaningful identity.

## 4. Verification And Docs

- [x] 4.1 Update unit tests, integration tests, and maintained fixtures that currently assume name-derived auth directories or name-keyed auth relationships.
- [x] 4.2 Update maintained docs covering auth bundle layout, credential naming, easy specialist behavior, launch-profile auth overrides, and credential-management routing to the new catalog-owned scheme.
- [x] 4.3 Run targeted verification for the new auth model, including relevant `pixi run` test suites and a final OpenSpec status check for the change.
