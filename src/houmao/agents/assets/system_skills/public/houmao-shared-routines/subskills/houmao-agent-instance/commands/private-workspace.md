# Private Workspace

## Purpose

Operate one optional, definition-owned private workspace for an individual agent. This is separate from multi-agent workspace topology. The stable TOML manifest maps semantic labels such as `workspace.artifacts` to relative directories. A SQLite index owns generation and growing record state.

## Workflow

1. Preserve the inherited admin or verified-agent actor frame.
2. Confirm this is one individual definition-owned workspace, not multi-agent topology.
3. Select the read-only agent branch or explicit-target admin branch below.
4. Validate manifest, SQLite, registry, instance-state, path, and Git posture before mutation.
5. Run one maintained operation and report identity, generation, semantic mapping, tracking, projection, or cleanup evidence.

If the request does not map cleanly to these operations, use the native planning tool to build a step-by-step plan from the actor frame, workspace contract, semantic bindings, Git posture, and user request, then execute the plan.

## Agent Branch

After fresh verified-self identity, use read-only commands:

```bash
houmao-mgr agents self instance-state workspace inspect
houmao-mgr agents self instance-state workspace resolve workspace.artifacts
```

Always resolve a semantic label through the manifest. Do not guess a directory name from the label or scan for an alternative root.

## Admin Branch

Require an explicit agent id or name:

```bash
houmao-mgr agents single --agent-id <id> instance-state workspace inspect
houmao-mgr agents single --agent-id <id> instance-state workspace validate
houmao-mgr agents single --agent-id <id> instance-state workspace doctor
houmao-mgr agents single --agent-id <id> instance-state workspace materialize workspace.artifacts
houmao-mgr agents single --agent-id <id> instance-state workspace remap \
  workspace.artifacts \
  records/review \
  --expected-generation <generation>
```

Tracking posture is explicit:

```bash
houmao-mgr agents single --agent-id <id> instance-state workspace tracking local-untracked
houmao-mgr agents single --agent-id <id> instance-state workspace tracking tracked-permitted
```

`untracked` owns a marked `.git/info/exclude` block and must verify effective ignore behavior. `tracked-permitted` removes only Houmao's owned block. It does not add files to Git. Project a named mindset only when the definition permits it:

```bash
houmao-mgr agents single --agent-id <id> instance-state workspace project-mindset <name> \
  --label workspace.mindsets
```

Destructive cleanup requires a successful doctor result, no drift or unowned content, and explicit confirmation:

```bash
houmao-mgr agents single --agent-id <id> instance-state workspace cleanup --confirm
```

## Contracts

- Default agent work remains the user project. A private workspace exists only when the definition and deployment selection enable it.
- The workspace root stays under the user project, normally `.houmao/private-agents/<agent-id>/`.
- `houmao-agent-workspace.toml` has a strict stable schema and changes only for semantic mapping or posture changes.
- `houmao-agent-workspace.sqlite` stores identity, generation, materialization, projection, and cleanup records.
- The manifest, index, agent registry, and instance-state association must agree on agent id, generation, definition revision, and workspace id.

## Guardrails

- DO NOT route this individual workspace to `houmao-utils-workspace-mgr`.
- DO NOT let an agent mutate workspace mappings, tracking posture, materialization, projection, or cleanup through self commands.
- DO NOT map paths outside the private root, through symbolic links, onto reserved files, or into collisions.
- DO NOT add broad Git ignore patterns or modify the repository's tracked `.gitignore`.
- DO NOT delete a workspace with drift, tracked content, unowned content, or missing confirmation.
