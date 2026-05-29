# Clarify

Use this page when the operator selects `clarify` or asks to clarify an operator-to-agent message before dispatch.

## Purpose

Resolve dispatch intent without sending anything. `clarify` may update a user-specified Markdown record, but it must not send direct prompts, mailbox messages, gateway requests, lifecycle commands, or other runtime mutations.

## Coverage Map

Build an internal coverage map before asking questions:

- objective and desired outcome;
- target agent, target list, or target-selection rule;
- intended message content;
- relevant context, issue, file, artifact, or prior-decision references;
- constraints, prohibited actions, and authorization boundaries;
- success criteria;
- route preference: default prompt delivery, operator-requested mailbox delivery, or target-specific overrides;
- ordering or priority when multiple targets are possible;
- expected reply, evidence, or acknowledgement;
- record mode: chat memory or external Markdown path;
- known ambiguity the operator has explicitly accepted.

## Question Protocol

- Ask only high-impact questions that affect target selection, route, safety, success criteria, ordering, or record mode.
- Ask one question at a time.
- Prefer at most five accepted clarification answers before summarizing current intent and remaining ambiguity.
- Do not ask wording-only questions while target selection, transport, safety, success criteria, or record mode is materially unclear.
- If the operator accepts ambiguity, record the accepted ambiguity explicitly instead of continuing to question.
- Do not force `Required`/`Optional` labels onto domain-intent questions. Use that shape only when asking for Houmao runtime inputs or an external artifact path.

## Record Modes

Default to chat memory:

- Summarize the accepted operator intent in the current conversation.
- Include unresolved but accepted ambiguity.
- Do not create or update files.

Use external Markdown only when the operator requests it:

- Require an explicit path before writing.
- Do not invent a path under the repository, home directory, current directory, workspace, or task directory.
- Create, update, or append the supplied file with accepted intent.
- Preserve existing user content when appending to an existing record.

Suggested Markdown record shape:

```markdown
# Operator Messaging Intent

## Objective

## Targets

## Message Intent

## Constraints

## Route Preference

## Ordering

## Expected Reply Or Evidence

## Accepted Ambiguity

## Dispatch Readiness
```

## Stop Conditions

Stop clarification when:

- target selection is clear enough for dispatch;
- route preference or acceptable route fallback is known;
- safety and authorization boundaries are clear enough;
- success criteria and expected reply/evidence are clear enough;
- record mode is resolved;
- remaining ambiguity is explicitly accepted.

End with a concise summary and say whether the intent is ready for `dispatch`.
