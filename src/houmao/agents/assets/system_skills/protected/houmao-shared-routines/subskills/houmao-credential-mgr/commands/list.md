# List Credentials

Use this action only when the user wants to list credentials for one supported tool.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family from the current prompt first and recent chat context second when it was stated explicitly.
3. Recover the target:
   - use `project [--project-dir <dir>] credentials <tool> list` when the request is project-local
   - use `internals native-agent credentials <tool> list --native-agent-root <path>` when the user explicitly targets a native-agent root
4. If the tool family or target is still missing, ask the user in Markdown before proceeding.
5. Run the direct credential list command and report the listed credential names.

## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> list
<chosen houmao-mgr launcher> internals native-agent credentials <tool> list --native-agent-root <dir>
```

## Guardrails

- Do not ask for a credential name when the task is only to list credentials.
- Do not guess the tool family or target when the prompt and recent chat context do not identify them explicitly.
- Do not route listing through `project specialist` or managed-agent lifecycle commands.
- Do not reinterpret the credential list as the set of project profiles or launch dossiers that reference those credentials.
