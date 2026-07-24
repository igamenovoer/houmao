---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Clarify

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this page when the operator selects `clarify`, asks to clarify an operator-to-agent message before dispatch, or invokes `houmao-shared-routines->houmao-operator-messaging` with an actionable prompt but no subcommand.

## Purpose

Resolve dispatch intent in chat without sending anything. `clarify` must not create, update, append, or request Markdown decision files, and it must not send direct prompts, mailbox messages, gateway requests, lifecycle commands, or other runtime mutations.

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
- known ambiguity the operator has explicitly accepted.

## Question Protocol

- Start each clarification round by showing what would be sent to the agent(s) in a compact Markdown table.
- Ask only high-impact questions that affect target selection, message content, route, safety, success criteria, or ordering.
- Ask one question at a time.
- Ask exactly one unclear decision-point question per round.
- Provide exactly three concrete answer choices for that question; mark one choice as `(Recommended)`.
- Add a fourth `Other` option so the operator can specify a different answer in their own prompt.
- After the choices, ask whether to dispatch the current plan directly or continue clarifying.
- Prefer at most five accepted clarification answers before summarizing current intent and remaining ambiguity.
- Do not ask wording-only questions while target selection, transport, safety, success criteria, or ordering is materially unclear.
- If the operator accepts ambiguity, note the accepted ambiguity explicitly in chat instead of continuing to question.
- Require an explicit path before writing any durable clarification artifact.
- Do not invent a path for clarification notes or decisions.
- Default to chat memory unless the operator explicitly names a durable output path.
- Do not force `Required`/`Optional` labels onto domain-intent questions. Use that shape only when asking for Houmao runtime inputs.

## Stop Conditions

Stop clarification when:

- target selection is clear enough for dispatch;
- route preference or acceptable route fallback is known;
- safety and authorization boundaries are clear enough;
- success criteria are clear enough;
- remaining ambiguity is explicitly accepted.

End with a concise summary and say whether the intent is ready for `dispatch`.

## Clarification Round Output

For every clarification round, including prompt-only invocation:

- Infer the intended target(s), message, route, and ordering from the prompt and chat context.
- If a target or message is ambiguous, show the ambiguity in the table instead of inventing a value.
- Show a compact Markdown table before asking the next question:

| Target or selection rule | Route | Message to send |
| --- | --- | --- |
| `<agent or rule>` | `prompt` or `mailbox` | `<operator-facing message summary or short exact message>` |

- Ask one unclear decision-point question with three concrete choices plus `Other`:

```markdown
Decision point: <one question that materially affects the message or route>

1. <choice> (Recommended) - <short reason>
2. <choice> - <short reason>
3. <choice> - <short reason>
4. Other - The operator specifies a different answer in their prompt.
```

- Then ask: "After that choice, should I dispatch this plan or continue clarifying?"
- Do not dispatch until the operator explicitly chooses dispatch.
