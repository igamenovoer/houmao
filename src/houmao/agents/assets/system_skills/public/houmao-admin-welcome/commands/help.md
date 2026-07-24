# Help

## Workflow

1. **Keep help read-only** and do not inspect operational targets or execute a recommended route.
2. **Explain the welcome boundary** and list its six public subcommands and five guided paths.
3. **Describe the blank-workspace choices**, state-aware reorientation, and context-preserving execution handoff.
4. **Return one representative next prompt** when the user asks how to begin.

If the help request does not map cleanly to these steps, use the native planning tool to build a bounded read-only answer from the welcome subcommands, curated paths, and user question, then answer without execution.

Explain that this skill is a read-only human-operator guide. List `show-options`, `choose-path`, `show-command-map`, `next-step`, and `start-guided-tour`. For execution, produce a context-preserving `$houmao-admin-entrypoint ...` handoff.
