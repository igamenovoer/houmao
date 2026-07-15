## Context

The supported project CLI exposes `project specialist`, `project profile`, and `project agents`; it does not register an `easy` subgroup. Most tests in `test_project_commands.py` already invoke these promoted paths, but 73 test function names still use `test_project_easy_*`. One demo unit test asserts that a mocked runtime constructs `project easy instance launch`, so it passes independently of the real CLI rejecting that command. Two integration test modules also retain obsolete specialist, profile, or instance command vectors; those useful integration cases can be migrated directly to the promoted paths.

The implementation still lives in a module named `project_easy.py`. Renaming production modules, catalog lanes, or persisted paths is broader than removing obsolete tests and is excluded from this change.

## Goals / Non-Goals

**Goals:**

- Remove tests that assert successful use of the retired public prefix.
- Rename retained tests according to the promoted command they actually invoke.
- Preserve coverage of specialist, profile, and project-agent behavior.
- Preserve a focused negative assertion that `project easy` is absent from the public command tree.

**Non-Goals:**

- Rename `project_easy.py`, `easy_profile`, or `.houmao/easy` internals.
- Repair or redesign demo runtime code that still constructs retired commands.
- Remove historical references from archived changes, logs, or the changelog.
- Change public CLI or runtime behavior.

## Decisions

### Delete assertions of obsolete success rather than rewrite them

Delete a test when its sole contract is that a retired `project easy ...` command is constructed successfully. Rewriting such a test would silently turn this test-only cleanup into demo runtime maintenance.

Alternative: update the mocked expectation to `project agents ...`. Rejected because the user requested removal of obsolete tests, while demo repair needs its own implementation scope and end-to-end validation.

### Rename useful tests by the command they exercise

Mechanically rename `test_project_easy_specialist_*` to `test_project_specialist_*`, `test_project_easy_profile_*` to `test_project_profile_*`, and `test_project_easy_instance_*` to `test_project_agents_*`. Apply the same terminology to integration test names and docstrings. Do not delete useful behavioral coverage merely because its test name is stale.

### Keep implementation monkeypatch targets where isolation requires them

Tests may continue patching `houmao.srv_ctrl.commands.project_easy` because that remains the implementation module. Such a patch target does not make `project easy` a supported CLI. A later production refactor can rename the module and persisted vocabulary coherently.

### Preserve one negative command-tree contract

Keep the assertion that `project_group.get_command(None, "easy") is None`. It verifies retirement rather than depending on the retired command.

## Risks / Trade-offs

- [Deleting the demo command-shape test leaves stale demo code without this unit assertion] → Record that limitation explicitly and avoid claiming the demo was repaired.
- [Mechanical renaming may miss a stale test name] → Search test definitions and current test text after editing.
- [Internal `project_easy` references remain visible] → Distinguish internal implementation naming from public command expectations in the change report.
