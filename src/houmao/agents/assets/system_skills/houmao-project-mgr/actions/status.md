# Inspect Project Overlay Status

Use this action only when the user wants to inspect which project overlay is selected, which project-aware roots are in effect, or whether a stateful project-aware flow would bootstrap the overlay.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Run the project status command.
3. Report the selected overlay root, overlay-root source, discovery mode, effective project-aware roots, and `would_bootstrap_overlay`.
4. If the user is trying to understand why another project-scoped command fails before initialization, explain the difference between this status inspection and non-creating selected-overlay commands.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> project status
```

## Guardrails

- Do not describe `project status` as mutating the overlay.
- Do not omit `would_bootstrap_overlay` when the user is asking what happens before initialization.
- Do not present `project easy instance list|get|stop` as having the same bootstrap behavior as `project status`.
