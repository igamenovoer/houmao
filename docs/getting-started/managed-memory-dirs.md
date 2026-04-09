# Managed Memory Dirs

Managed memory dirs give a tmux-backed managed agent one durable filesystem location for notes, downloaded source material, experiment logs, extracted knowledge, or any other long-lived working state that should survive restarts.

This is separate from the per-session scratch `job_dir`. `job_dir` is runtime-owned scratch under `.houmao/jobs/`; a memory dir is durable operator-owned or agent-owned state that Houmao discovers and publishes, but does not structure internally.

## Default Behavior

When memory is enabled in the default `auto` mode and the launch runs inside a project overlay, Houmao resolves:

```text
<project-root>/.houmao/memory/agents/<agent-id>/
```

For example, managed agent `researcher` in `/repo` gets:

```text
/repo/.houmao/memory/agents/researcher/
```

Houmao creates that directory if needed, persists the resolved absolute path in the runtime manifest, and publishes it into the live tmux session as `HOUMAO_MEMORY_DIR`.

## Three Outcomes

Each managed session resolves to exactly one of these outcomes:

- `auto`: Use the conservative default per-agent directory under `.houmao/memory/agents/<agent-id>/`.
- `exact`: Use one explicit absolute directory from `--memory-dir <path>`.
- `disabled`: Bind no memory directory for this session with `--no-memory-dir`.

When memory is disabled, Houmao does not create a directory and does not publish `HOUMAO_MEMORY_DIR`.

## Typical Uses

- Keep a durable per-agent research notebook that survives relaunch.
- Point multiple agents at one shared directory when you intentionally want shared context.
- Disable memory completely for disposable agents that should only use `job_dir`.

## Launch Examples

Default auto memory:

```bash
houmao-mgr agents launch --agents researcher
```

Explicit shared directory:

```bash
houmao-mgr agents launch --agents researcher --memory-dir /shared/agent-memory/research
```

No memory dir:

```bash
houmao-mgr agents launch --agents researcher --no-memory-dir
```

The same controls also exist on:

- `houmao-mgr agents join`
- `houmao-mgr project easy instance launch`
- `houmao-mgr project easy profile create`
- `houmao-mgr project agents launch-profiles add`

Launch profiles and easy profiles can store memory-dir intent so later launches reuse it by default.

## What Houmao Owns

Houmao owns:

- path resolution,
- creation of the resolved directory when memory is enabled,
- manifest persistence of the resolved result,
- publishing `HOUMAO_MEMORY_DIR` into the live tmux session,
- inspection output such as `houmao-mgr agents state`.

## What Houmao Does Not Own

Houmao does not define:

- required subdirectories,
- Markdown file naming,
- metadata sidecars,
- index files,
- cleanup semantics for the contents.

That means agents should inspect the directory they receive and work with whatever structure already exists there. If operators want one shared layout or one custom taxonomy, they can create it directly in the memory dir.

Stop and cleanup flows do not delete the memory dir just because the managed session stopped.

## Inspecting The Resolved Path

Use `houmao-mgr agents state` or the easy-instance inspection surfaces to see the resolved `memory_dir`.

Inside the running session, use `HOUMAO_MEMORY_DIR` when it is present. If it is absent, the session was launched without a memory dir.

## See Also

- [Launch Profiles](launch-profiles.md)
- [Agents And Runtime](../reference/system-files/agents-and-runtime.md)
- [Project-Aware Operations](../reference/system-files/project-aware-operations.md)
