## Context

`houmao-mgr project` is the ordinary project workflow, but the current command tree still exposes top-level target-variant commands such as `houmao-mgr credentials --project` and `houmao-mgr credentials --agent-def-dir`. This happened because project commands do not yet have a group-level selector, so explicit project targeting leaked into individual top-level command families.

The same tree now treats provider-aligned file-tree material as `internals native-agent` material. That makes direct agent-definition-directory operations a poor fit for a public top-level command family. Operators should use project concepts for project work and internals concepts for direct native-agent material.

Current target model:

```text
houmao-mgr credentials --project ...        # duplicates project credentials
houmao-mgr credentials --agent-def-dir ...  # direct native-agent material
houmao-mgr project credentials ...          # actual project workflow
houmao-mgr brains build ...                 # direct build plumbing
```

Target model:

```text
houmao-mgr project [--project-dir DIR] credentials ...
houmao-mgr project [--project-dir DIR] specialist/profile/agents/skills/mailbox ...

houmao-mgr internals native-agent [--native-agent-root DIR] credentials ...
houmao-mgr internals native-agent [--native-agent-root DIR] brain build ...
```

## Goals / Non-Goals

**Goals:**

- Make `houmao-mgr project --project-dir <dir> ...` the maintained explicit project selection surface for every project subcommand.
- Remove public top-level command families whose primary purpose is choosing between project and native-agent storage targets.
- Keep project credentials public under `project credentials`.
- Keep direct native-agent credentials and brain-build plumbing available only under `internals native-agent` when they remain useful for tests, fixtures, or advanced maintenance.
- Update command templates, docs, and packaged skills so agents learn one coherent routing rule.

**Non-Goals:**

- Do not redesign credential storage schemas, project catalog tables, provider login behavior, or brain home construction internals.
- Do not add a long-lived compatibility shim for removed top-level `credentials` or `brains` commands unless a short diagnostic-only transition is selected during implementation.
- Do not make ordinary project commands mutate direct native-agent roots except through the existing one-way project compatibility projection.
- Do not change top-level runtime surfaces such as `houmao-mgr agents`, standalone `mailbox`, `admin`, or `system-skills`.

## Decisions

### `--project-dir` Selects A Human Project Directory

`houmao-mgr project --project-dir /repo ...` SHALL treat `/repo` as the project root and resolve the overlay as `/repo/.houmao`. This is more ergonomic than asking users to pass the overlay directory directly and aligns with the command name: users select a project, not an implementation directory.

Alternative considered: `--project-overlay-dir /repo/.houmao`. This matches the existing env var and resolver internals, but it keeps implementation vocabulary in the public workflow and makes commands feel like low-level storage operations.

### Project Group Context Flows Through Click Context

The project group SHOULD parse `--project-dir` once and store the resolved selector in `ctx.obj` or a project-specific context object. Project helper functions SHOULD read that selector before falling back to current working directory discovery. This avoids adding a duplicate option to every project leaf command.

Alternative considered: Add `--project-dir` to every project subcommand. That keeps helpers local but recreates the replication problem in option form.

### Explicit Selection Precedes Discovery

Resolution for project commands SHALL be:

1. group-level `--project-dir <dir>` when supplied,
2. existing supported environment selection if retained for automation,
3. automatic discovery from the invocation directory,
4. actionable missing-project failure for stateful commands.

`project init` SHALL use the selected project directory as the place to create or validate `.houmao`.

### Top-Level `credentials` Becomes Unmaintained Public UX

Project credentials SHALL be managed through `houmao-mgr project [--project-dir <dir>] credentials <tool> ...`. Direct native-agent credential management, if retained, SHALL move under `houmao-mgr internals native-agent credentials <tool> ...` and use `--native-agent-root` rather than `--agent-def-dir`.

Alternative considered: Keep top-level `credentials` because credentials are a cross-cutting concern. The problem is that the command is not actually a neutral workflow; it multiplexes storage targets. Keeping it means the same logic would justify top-level wrappers for `skills`, `mailbox`, `profile`, and other project subcommands.

### Top-Level `brains` Moves Under Internals

`brains build` consumes native-agent recipe/setup/auth material and emits runtime brain homes. Ordinary users reach this through `project agents launch` or `agents launch`; direct build is construction plumbing. The maintained direct surface SHALL be `internals native-agent brain build` or an equivalent internal native-agent subgroup chosen during implementation.

Alternative considered: Keep `brains build` top-level because brain construction is a named domain. That preserves discoverability for developers but weakens the top-level rule that public groups are user workflows.

## Risks / Trade-offs

- Removed command paths may break existing scripts -> mitigate by updating tracked docs, tests, system skills, command templates, and demo launchers in the same change.
- `--project-dir` and existing `HOUMAO_PROJECT_OVERLAY_DIR` may create two names for similar selection -> mitigate by documenting `--project-dir` as public and treating overlay-env selection as automation/internal compatibility if retained.
- Moving direct credential CRUD under internals may make advanced fixture setup less discoverable -> mitigate with explicit docs and system-skill guidance for advanced native-agent work.
- Click context propagation can miss project helpers called outside project commands -> mitigate with focused tests for every project subgroup and for helper fallback behavior.
- Removing top-level `brains` may hide useful developer tooling -> mitigate by documenting the internal path and ensuring command templates can render it for agents that need build plumbing.
