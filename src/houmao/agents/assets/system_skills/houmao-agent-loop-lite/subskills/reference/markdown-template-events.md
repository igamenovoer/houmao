# Markdown Template Events

## Template Rules

- Every lite execplan has at least one template under `execplan/specs/templates/`.
- Each template is plain Markdown.
- Each template begins with a body-local prologue containing `Loop-Template-Type` and `Loop-Template-Version`.
- The prologue ends at the first blank line.
- Template bodies use literal `<placeholder ...>` tokens for values to fill.
- Do not use JSON Schema, Jinja2, conditionals, loops, filters, or expression language.
- Do not duplicate Houmao mail envelope fields in template bodies.

## Example

```markdown
Loop-Template-Type: task-request
Loop-Template-Version: 1

# Task Request

Work item: <placeholder work_item_id>
Goal: <placeholder task_goal>
Required output: <placeholder expected_result>
State ref: <placeholder state_ref>
Artifact ref: <placeholder artifact_ref>
```

## Skill Dispatch

- Generated receiver skills trigger from exact `Loop-Template-Type` values.
- Generated sender skills must check for unresolved `<placeholder` tokens before sending.
- Sender, receiver, subject, message id, thread id, timestamps, reply refs, and headers come from Houmao mailbox metadata.
