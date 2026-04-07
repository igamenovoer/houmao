## Context

Managed launch currently uses one value, `working_directory`, for two different concerns:

- resolving project-aware launch source context such as overlay root, agent-definition tree, runtime root, jobs root, and mailbox root
- setting the runtime cwd recorded in the manifest and used by the launched provider session

That coupling is tolerable when launch always runs from the same project that the agent should work inside, but it breaks as soon as an operator wants to launch from one Houmao project and point the agent at another repository or subdirectory. The same coupling also means `project easy instance launch` cannot safely accept a runtime cwd override through the current shared launch helper because easy launch must stay bound to the selected project overlay and specialist source.

`agents join` already has a cwd override, but its public flag name is `--working-directory`, which diverges from the shorter form the new launch surfaces should use.

## Goals / Non-Goals

**Goals:**
- Add one explicit `--workdir` flag to `houmao-mgr agents launch`.
- Add one explicit `--workdir` flag to `houmao-mgr project easy instance launch`.
- Rename `houmao-mgr agents join --working-directory` to `--workdir`.
- Separate launch source resolution from runtime workdir so a source Houmao project stays authoritative even when `--workdir` points somewhere else.
- Keep relaunch behavior stable by continuing to use the persisted manifest workdir.

**Non-Goals:**
- Renaming internal manifest, schema, or server payload fields from `working_directory` to `workdir`.
- Persisting a default workdir into specialist metadata or preset launch config.
- Adding a relaunch-time workdir override.
- Changing how non-launch commands such as `agents prompt`, `agents state`, or mailbox flows select overlays.

## Decisions

### 1. Public CLI naming uses `--workdir`

All managed launch-adjacent CLI surfaces in scope use `--workdir` as the user-facing flag name:

- `houmao-mgr agents launch --workdir`
- `houmao-mgr project easy instance launch --workdir`
- `houmao-mgr agents join --workdir`

`--working-directory` is removed from the supported join CLI surface instead of preserved as a compatibility alias. This repository already permits intentional CLI cleanup, and a single short option name is clearer than maintaining two public spellings for the same concept.

Alternative considered:
- Keep `--working-directory` on join and add `--workdir` only to new surfaces.
  Rejected because it preserves inconsistency exactly where operators compare launch flows side by side.

### 2. Launch source context and runtime workdir are separate inputs

The implementation will treat these as distinct values:

- **Launch source context**: the authority used to resolve overlay root, agent-definition tree, preset source, runtime root, jobs root, and mailbox root.
- **Runtime workdir**: the cwd used for the launched provider/runtime session and stored in the manifest as the session working directory.

For `agents launch`:
- bare role selectors continue to use the invocation project-aware context as the launch source
- explicit preset-path selectors resolve their launch source from the resolved preset owner tree rather than from `--workdir`
- `--workdir` only changes the runtime cwd

For `project easy instance launch`:
- the selected project overlay and specialist remain the launch source
- `--workdir` only changes the runtime cwd

For `agents join`:
- the same distinction already exists conceptually; the join source remains the adopted tmux session while `--workdir` sets or overrides the adopted working directory value

Alternative considered:
- Continue using one `working_directory` value for both source resolution and runtime cwd.
  Rejected because it makes easy launch source resolution wrong as soon as `--workdir` points outside the selected project.

### 3. Shared launch plumbing must accept explicit source context

The current shared launch helper resolves project-aware local roots and native launch target selection from the runtime `working_directory`. That helper should be refactored so launch callers can pass:

- resolved source context
- resolved target metadata or explicit agent-definition source
- resolved runtime/jobs/mailbox roots
- explicit runtime workdir

`agents launch` can remain a thin wrapper that derives both source context and runtime workdir from invocation inputs.

`project easy instance launch` should use the same lower-level launch path but supply:
- source context from the selected project overlay
- specialist-backed preset source from that same overlay
- runtime workdir from `--workdir` or invocation cwd

Alternative considered:
- Teach the existing helper to special-case easy launch with boolean flags.
  Rejected because it would preserve the conceptual conflation and make later launch paths harder to reason about.

### 4. Internal persisted fields stay `working_directory`

The manifest, runtime models, and server-facing payloads already use `working_directory` broadly. This change will keep those internal field names unchanged and only rename user-facing CLI flags and docs to `workdir`.

This limits blast radius across runtime persistence, passive-server contracts, compatibility tests, and downstream tooling while still delivering the user-visible CLI cleanup requested here.

Alternative considered:
- Rename internal fields and public CLI together.
  Rejected because it turns a launch-surface improvement into a much larger cross-subsystem breaking-contract migration.

## Risks / Trade-offs

- [Source-project inference for explicit preset paths is wrong or ambiguous] → Resolve source context from the resolved preset owner tree explicitly and add focused tests for selectors that launch from one repo into another.
- [Easy launch accidentally follows `--workdir` for overlay resolution] → Keep easy overlay selection in the project command layer and pass that resolved source context explicitly into shared launch plumbing.
- [Operators still use `--working-directory` on join and hit a breaking change] → Update help text, CLI reference, and getting-started docs together, and add regression coverage that the new surface is `--workdir`.
- [Partial refactor leaves runtime roots tied to runtime cwd in one path] → Cover `agents launch`, `project easy instance launch`, and `agents join` with focused tests that assert both source roots and manifest workdir independently.

## Migration Plan

1. Add `--workdir` to `agents launch` and `project easy instance launch`.
2. Rename join help and parsing from `--working-directory` to `--workdir`.
3. Refactor managed launch plumbing so source context and runtime workdir are passed independently.
4. Update operator-facing docs and examples to use `--workdir` and describe source-project pinning.
5. Verify relaunch continues to use the persisted manifest workdir with no new override path.

Rollback is straightforward at the code level because no persisted data format changes are required. The only user-visible migration is the join flag rename and the availability of new `--workdir` launch flags.

## Open Questions

- None. The public contract is to use `--workdir` on all in-scope CLI surfaces while leaving internal persisted `working_directory` fields unchanged.
