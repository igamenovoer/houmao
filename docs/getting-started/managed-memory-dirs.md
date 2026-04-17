# Managed Agent Memory

Managed agent memory gives every tmux-backed managed agent one operator-addressable memory directory with exactly two stable parts:

- `houmao-memo.md`: the fixed memo file at the memory root for durable initialization notes, standing instructions, and operator-visible context.
- `pages/`: the only managed subdirectory. Each page is a normal file that an operator or agent may reference from the memo with an authored relative link such as `pages/notes/todo.md`.

Houmao memory is intentionally small. Provider CLIs such as Claude Code and Codex already maintain their own internal memory, and operators often choose a separate project or artifact directory for real work products. Houmao memory is the shared operator-facing note surface, not an arbitrary state database.

## Default Behavior

When a launch runs inside a project overlay, Houmao resolves:

```text
<project-root>/.houmao/memory/agents/<agent-id>/
```

For example, managed agent `researcher` in `/repo` gets:

```text
/repo/.houmao/memory/agents/researcher/
  houmao-memo.md
  pages/
```

Houmao creates the memory root, memo file, and `pages/` directory for every managed agent. The runtime manifest stores `memory_root`, `memo_file`, and `pages_dir`.

Managed launches also render a default `memo-cue` section in the managed prompt header. That cue contains the resolved absolute `houmao-memo.md` path and makes memo reading mandatory before planning or acting at every prompt turn, new dialog, topic change, compaction, or cleared-context boundary. It tells agents to keep the memo limited to concise working rules, standing constraints, and current facts; never use it as a log, journal, transcript, or scratchpad; move long details into `pages/` with a short memo note and relative link; and update it only on explicit memo prompts or obviously stale facts. Disable only that cue with `--managed-header-section memo-cue=disabled`, or disable the whole managed header with `--no-managed-header`.

## Environment Variables

Live tmux sessions receive:

- `HOUMAO_AGENT_MEMORY_DIR`: the memory root.
- `HOUMAO_AGENT_MEMO_FILE`: the fixed memo file path.
- `HOUMAO_AGENT_PAGES_DIR`: the pages directory.

The previous workspace, scratch, persist, job, and generic memory variables are not part of the current managed-agent memory contract.

## Launch Examples

Use the normal launch and join commands. There are no managed-memory persist flags:

```bash
houmao-mgr agents launch --agents researcher
houmao-mgr agents join --agent-name researcher
```

Work artifacts belong in the launched workdir, an operator-designated project path, or an external directory named in the task instructions.

## Memory Commands

Use `houmao-mgr agents memory` to inspect and operate the memo and pages:

```bash
houmao-mgr agents memory path --agent-name researcher
houmao-mgr agents memory memo show --agent-name researcher
houmao-mgr agents memory memo set --agent-name researcher --content-file ./init-notes.md
houmao-mgr agents memory memo append --agent-name researcher --content "\nFollow repo conventions."
houmao-mgr agents memory tree --agent-name researcher
houmao-mgr agents memory resolve --agent-name researcher --path notes/todo.md
houmao-mgr agents memory read --agent-name researcher --path notes/todo.md
houmao-mgr agents memory write --agent-name researcher --path notes/todo.md --content "next step"
houmao-mgr agents memory append --agent-name researcher --path notes/todo.md --content "\nfollow-up"
houmao-mgr agents memory delete --agent-name researcher --path notes/todo.md
```

Page operations accept only relative paths and reject traversal outside `pages/`. Page writes, appends, and deletes do not edit `houmao-memo.md`. Use `memo set` or `memo append` when you want to author memo text, and use `memory resolve --path <page>` when you need the page-relative path, memo-relative link, absolute path, existence, and kind for a page.

Managed homes also install the `houmao-memory-mgr` system skill by default through the closed `core` set. Use that skill when the agent itself is asked to inspect, append to, prune, or reorganize the managed memo or contained pages; it routes through the same supported `houmao-mgr agents memory ...` commands and preserves the free-form memo model.

## Ownership

Houmao owns path resolution, directory creation, fixed memo creation without overwriting existing content, manifest persistence, environment publication, inspection output, and page-scoped memory commands.

Houmao does not generate, refresh, inspect, or remove page links inside `houmao-memo.md`. The memo is free-form Markdown owned by the operator and agent, and links to contained pages should use memo-relative paths such as `pages/notes/todo.md`. Houmao also does not define arbitrary file taxonomies under `pages/`. Agents and operators may create readable pages there, but mutable retry counters, dedupe databases, mailbox receipts, and live supervision state should use the mailbox, gateway, reminder, runtime, or a pattern-specific mechanism instead.

Stop and session cleanup flows remove runtime session envelopes; they do not delete the managed agent memory directory just because a session stopped.

## See Also

- [Launch Profiles](launch-profiles.md)
- [Agents And Runtime](../reference/system-files/agents-and-runtime.md)
- [Project-Aware Operations](../reference/system-files/project-aware-operations.md)
