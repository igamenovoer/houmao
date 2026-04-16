## 1. Inventory And Boundaries

- [x] 1.1 Audit `src/houmao` for maintained migration, upgrade, legacy import, and legacy alias-adoption paths.
- [x] 1.2 Classify each match as in scope or out of scope, keeping pure current-schema validators, deprecated-surface fail-fast guidance, archived demos, and provider-required current config seeding out of scope.

## 2. Project And Mailbox State

- [x] 2.1 Replace project catalog migration behavior with current-schema creation plus validation of existing catalog version and required current-format invariants.
- [x] 2.2 Remove old catalog schema transformation branches, including v7/v8/v9/v10/v11 upgrade logic and table rebuild helpers used only for compatibility migration.
- [x] 2.3 Remove automatic legacy `.houmao/agents/` and `.houmao/easy/` import from maintained project catalog operations.
- [x] 2.4 Remove mailbox-local SQLite population from obsolete shared mutable mailbox-state rows.
- [x] 2.5 Keep current-format mailbox-local SQLite initialization, deterministic default state creation, and recovery from canonical Markdown message files.

## 3. Runtime And Gateway State

- [x] 3.1 Remove session manifest v2/v3 upgrade logic and require current session manifest schema on load.
- [x] 3.2 Remove legacy manifest authority synthesis helpers used only to derive current runtime fields from old manifest payloads.
- [x] 3.3 Remove gateway queue/notifier SQLite in-place schema upgrade logic and validate existing gateway storage against the current schema.
- [x] 3.4 Ensure incompatible runtime/gateway diagnostics direct operators to start a fresh session or recreate the gateway root.

## 4. Source Parsing And System Skills

- [x] 4.1 Remove legacy brain recipe loading from the maintained brain construction path.
- [x] 4.2 Remove hidden legacy builder CLI aliases such as `--recipe`, `--config-profile`, and `--cred-profile`.
- [x] 4.3 Remove tool-adapter legacy field aliases such as `config_projection` and `credential_projection`.
- [x] 4.4 Remove system-skill install-state migration for old copy-only state versions, family-namespaced paths, and renamed/superseded skill records.
- [x] 4.5 Ensure incompatible source or install-state diagnostics direct operators to rewrite current source files, rebuild homes, reinstall system skills, or use a clean target home.

## 5. Tests

- [x] 5.1 Remove or rewrite project catalog tests that assert old catalog schemas, removed columns, or legacy project trees migrate successfully.
- [x] 5.2 Add or update project catalog tests for fresh catalog creation and fail-fast handling of unsupported existing catalog versions or obsolete current-version table shapes.
- [x] 5.3 Remove or rewrite mailbox tests that assert legacy shared mutable mailbox state migrates into mailbox-local SQLite.
- [x] 5.4 Add or update mailbox tests showing local state initializes from current-format inputs or deterministic defaults without consulting obsolete shared mutable state.
- [x] 5.5 Remove or rewrite runtime manifest tests that assert v2/v3 manifests are upgraded into the current model.
- [x] 5.6 Add or update tests for current-schema-only manifest loading and unsupported old manifest rejection.
- [x] 5.7 Remove or rewrite construction/system-skill/gateway tests that assert legacy source aliases, old install-state migration, or gateway schema upgrade behavior.
- [x] 5.8 Add or update tests for current source parsing, current install-state handling, and unsupported gateway storage failure.

## 6. Documentation And Audit

- [x] 6.1 Update docs and user-facing guidance that mention source or persisted-state migrations so they describe recreate/rebootstrap/rebuild behavior for incompatible state.
- [x] 6.2 Audit source and docs for migration-path references; remove maintained migration behavior while preserving unrelated deprecated-surface guidance and archived historical references.
- [x] 6.3 Confirm packaged system skills do not instruct agents to rely on project, mailbox, runtime, gateway, source, or system-skill migration behavior.

## 7. Validation

- [x] 7.1 Run `openspec validate remove-source-migration-paths --strict`.
- [x] 7.2 Run focused project catalog tests with `pixi run pytest tests/unit/project/test_catalog.py`.
- [x] 7.3 Run focused mailbox tests with `pixi run pytest tests/unit/mailbox/test_managed.py tests/unit/mailbox/test_filesystem.py`.
- [x] 7.4 Run focused runtime/gateway/system-skill/construction tests that cover the touched modules.
- [x] 7.5 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test`.
