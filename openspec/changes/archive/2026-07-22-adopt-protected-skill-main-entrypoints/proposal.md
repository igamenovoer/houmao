## Why

The revised Imsight skill-layout contract reserves `SKILL.md` for standalone or host-discoverable roots and requires parent-scoped subskills to use `SKILL-MAIN.md`. Houmao currently composes every protected router and routine as nested `SKILL.md`, so recursive exact-name scanners can register implementation routines independently and bypass the intended public actor entrypoint reminder.

## What Changes

- **BREAKING**: Rename the protected shared-router and routine entrypoints from `SKILL.md` to `SKILL-MAIN.md`; do not leave compatibility copies.
- Keep `houmao-admin-welcome`, `houmao-admin-entrypoint`, and `houmao-agent-entrypoint` as public top-level `SKILL.md` roots, with the welcome skill remaining standalone and free of protected mounts.
- Make the composer and validator role-aware: public roots require `SKILL.md`, parent-scoped roots require `SKILL-MAIN.md`, and ambiguous or legacy nested entrypoints fail validation.
- Require each public entrypoint to load the protected router explicitly and each protected router to load only the selected child routine and its needed local resources.
- Add the standard object-style invocation-notation declaration to instruction pages that use skill, subskill, or subcommand designators.
- Keep generated mailbox and notifier prompts on public `$houmao-agent-entrypoint` or tool-native equivalents while clarifying that protected traversal is parent-controlled and protected files are never standalone triggers.
- Update lifecycle version evidence, tests, fixtures, and documentation so old nested-`SKILL.md` compositions are diagnosed and upgraded safely.

## Capabilities

### New Capabilities

- `houmao-parent-scoped-skill-entrypoints`: Defines public versus parent-scoped entrypoint filenames, explicit parent loading, scanner-safe composition, invocation-notation metadata, generated-prompt boundaries, upgrade behavior, and verification coverage.

### Modified Capabilities

None.

## Impact

This change affects the system-skill manifest and schema, protected skill assets, pack composition and validation, system-skill receipt status, generated mailbox prompts, managed-agent prompt fixtures, system-skill and mailbox tests, and documentation that names protected entrypoint paths. Public skill names and user-facing route arguments remain unchanged. Top-level project, private, generated, auto, and legacy skills continue to use `SKILL.md`.
