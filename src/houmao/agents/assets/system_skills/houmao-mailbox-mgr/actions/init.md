# Initialize A Mailbox Root

Use this action only when the user wants to bootstrap or validate one filesystem mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. If that lane is still ambiguous after checking the prompt and recent chat context, ask the user before proceeding.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Run the matching mailbox-root initialization command.
5. Report the returned root summary and root-selection detail.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> mailbox init [--mailbox-root <path>]
<chosen houmao-mgr launcher> project mailbox init
```

## Guardrails

- Do not route existing managed-agent late binding through this action.
- Do not ask for `--mailbox-root` when the user explicitly chose the project mailbox lane.
- Do not replace mailbox-root initialization with manual directory creation.
