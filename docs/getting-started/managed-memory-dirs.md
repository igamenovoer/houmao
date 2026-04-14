# Managed Agent Workspaces

Managed agent workspaces give every tmux-backed managed agent one operator-addressable workspace root with three stable parts:

- `houmao-memo.md`: a fixed memo file at the workspace root for durable initialization notes, standing instructions, and operator-visible context.
- `scratch/`: a scratch lane for mutable short-lived working state.
- `persist/`: a persist lane for durable agent-owned or operator-selected state when persistence is enabled.

## Default Behavior

When persistence is enabled in the default `auto` mode and the launch runs inside a project overlay, Houmao resolves:

```text
<project-root>/.houmao/memory/agents/<agent-id>/
```

For example, managed agent `researcher` in `/repo` gets:

```text
/repo/.houmao/memory/agents/researcher/
  houmao-memo.md
  scratch/
  persist/
```

Houmao creates the workspace root, memo file, and scratch lane for every managed agent. It creates the persist lane only when persistence is enabled. The runtime manifest stores `workspace_root`, `memo_file`, `scratch_dir`, `persist_binding`, and optional `persist_dir`.

## Environment Variables

Live tmux sessions receive:

- `HOUMAO_AGENT_STATE_DIR`: the workspace root.
- `HOUMAO_AGENT_MEMO_FILE`: the fixed memo file path.
- `HOUMAO_AGENT_SCRATCH_DIR`: the scratch lane.
- `HOUMAO_AGENT_PERSIST_DIR`: the persist lane when persistence is enabled.

The old `HOUMAO_JOB_DIR` and `HOUMAO_MEMORY_DIR` variables are not part of the current managed-agent workspace contract.

## Persist Outcomes

Each managed session resolves to exactly one persist outcome:

- `auto`: use the default per-agent `persist/` lane under `.houmao/memory/agents/<agent-id>/`.
- `exact`: use one explicit absolute persist directory from `--persist-dir <path>`.
- `disabled`: bind no persist directory for this session with `--no-persist-dir`.

When persistence is disabled, Houmao still creates the workspace root, memo file, and scratch lane, but it does not create or publish a persist lane.

## Launch Examples

Default auto persist lane:

```bash
houmao-mgr agents launch --agents researcher
```

Explicit shared persist directory:

```bash
houmao-mgr agents launch --agents researcher --persist-dir /shared/agent-memory/research
```

No persist lane:

```bash
houmao-mgr agents launch --agents researcher --no-persist-dir
```

The same controls also exist on:

- `houmao-mgr agents join`
- `houmao-mgr project easy instance launch`
- `houmao-mgr project easy profile create`
- `houmao-mgr project agents launch-profiles add`

Launch profiles and easy profiles can store persist intent so later launches reuse it by default.

## Workspace Commands

Use `houmao-mgr agents workspace` to inspect and operate the workspace:

```bash
houmao-mgr agents workspace path --agent-name researcher
houmao-mgr agents workspace memo show --agent-name researcher
houmao-mgr agents workspace memo set --agent-name researcher --content-file ./init-notes.md
houmao-mgr agents workspace tree --agent-name researcher --lane scratch
houmao-mgr agents workspace read --agent-name researcher --lane scratch --path notes/todo.txt
houmao-mgr agents workspace write --agent-name researcher --lane scratch --path notes/todo.txt --content "next step"
houmao-mgr agents workspace append --agent-name researcher --lane scratch --path notes/todo.txt --content "\nfollow-up"
houmao-mgr agents workspace delete --agent-name researcher --lane scratch --path notes/todo.txt
houmao-mgr agents workspace clear --agent-name researcher --lane scratch --dry-run
```

Lane operations accept only relative paths and reject traversal outside the selected lane. Persist-lane operations fail when persistence is disabled.

## Ownership

Houmao owns path resolution, lane creation, fixed memo creation without overwriting existing content, manifest persistence, environment publication, inspection output, and lane-scoped workspace commands.

Houmao does not define arbitrary file taxonomies inside `scratch/` or `persist/`. Agents and operators may create their own files there, but durable notes that must be easy to find should go in `houmao-memo.md` or the persist lane.

Stop and session cleanup flows do not delete the persist lane just because the managed session stopped. To remove scratch contents explicitly, use `houmao-mgr agents workspace clear --lane scratch`.

## See Also

- [Launch Profiles](launch-profiles.md)
- [Agents And Runtime](../reference/system-files/agents-and-runtime.md)
- [Project-Aware Operations](../reference/system-files/project-aware-operations.md)
