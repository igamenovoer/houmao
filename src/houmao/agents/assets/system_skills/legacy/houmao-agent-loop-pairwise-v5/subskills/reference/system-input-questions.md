# System Input Questions

Use this page before asking the operator for Houmao loop system-operation inputs.

## Scope

Apply this shape to Houmao runtime and artifact-location inputs:

- `<loop-dir>` and generated artifact paths;
- project root or project-context root;
- execplan validation, update, or generation target;
- prepared agent/profile facts;
- workspace preparation target and readiness evidence;
- mailbox, gateway, notifier, memory, harness, state, run, launch, lifecycle, or operator-control posture.

Do not force this shape onto user-task or domain-intent questions such as objective, acceptance criteria, participant reasoning, algorithm choices, content scope, or business semantics unless the question is specifically about Houmao runtime behavior.

## Shape

Use concise Markdown:

```markdown
Required:
- `<field>`: why it blocks this operation.

Optional:
- `<field>`: default, skip behavior, or supported modifier.
```

If no optional input applies, say `Optional: none for this step.`

Ask only for the missing fields needed for the selected operation. Name the routed operation or generated command/harness path you intend to use when that helps the operator answer.
