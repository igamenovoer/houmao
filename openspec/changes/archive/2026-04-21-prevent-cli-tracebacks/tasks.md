## 1. Root CLI Safety Net

- [x] 1.1 Expand the top-level `houmao-mgr` wrapper so uncaught exceptions from maintained command trees render as non-zero CLI error text without a Python traceback.
- [x] 1.2 Add root-wrapper regression tests that prove leaked mailbox and project-recipe exceptions are rendered without tracebacks.

## 2. Mailbox Command Normalization

- [x] 2.1 Add shared mailbox command/helper normalization so expected mailbox-root state failures become `click.ClickException` for the generic `houmao-mgr mailbox` family.
- [x] 2.2 Update project mailbox command paths to preserve selected-overlay wording and recommend `houmao-mgr project mailbox init` for uninitialized selected-overlay roots.
- [x] 2.3 Add regression tests for generic and project mailbox bad-state flows, including missing mailbox indexes and unsupported or unbootstrapped roots.

## 3. Project Agent-Definition Normalization

- [x] 3.1 Add shared project recipe/preset parsing helpers that convert malformed stored preset-file failures into explicit CLI errors.
- [x] 3.2 Route project role inspection and preset-reference flows through the normalized helpers so malformed preset trees fail as CLI errors instead of raw exceptions.
- [x] 3.3 Add regression tests for `project agents recipes|presets` and `project agents roles` commands when `.houmao/agents/presets/` contains malformed files.

## 4. Audit and Verification

- [x] 4.1 Audit maintained `houmao-mgr` command families for remaining raw-exception paths touched by the new shared boundaries and normalize any confirmed sibling leaks in scope.
- [x] 4.2 Run the targeted `srv_ctrl` test coverage for the root wrapper, mailbox commands, and project command families affected by this change.
