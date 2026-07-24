# Named Mindsets

## Purpose

Read or administer definition-declared named question sets. Each edit creates a revision. A skill bound to a mindset consumes one atomic snapshot containing the full current question set and revision.

## Workflow

1. Preserve the inherited admin or verified-agent actor frame.
2. Select the read-only agent branch or explicit-target admin branch below.
3. Resolve the named mindset or bound skill without assembling partial state.
4. Run one maintained command and report the exact revision, snapshot, mutation diff, or blocker.
5. Stop required skill work when the atomic snapshot fails.

If the request does not map cleanly to these operations, use the native planning tool to build a step-by-step plan from the actor frame, mindset declaration, authority limits, revision contract, and user request, then execute the plan.

## Agent Branch

After fresh verified-self identity:

```bash
houmao-mgr agents self instance-state mindsets get <name>
houmao-mgr agents self instance-state mindsets snapshot --skill <skill-name>
```

When the definition marks a mindset as required for the selected skill, take the snapshot before substantive skill work. If lookup, authorization, or snapshot creation fails, stop the skill. Do not assemble a mindset through separate question reads.

## Admin Branch

Require an explicit target:

```bash
houmao-mgr agents single --agent-id <id> instance-state mindsets get <name>
houmao-mgr agents single --agent-id <id> instance-state mindsets snapshot --skill <skill-name>
houmao-mgr agents single --agent-id <id> instance-state mindsets set <name> \
  --record-file <mindset-record.json> \
  --expected-revision <revision>
```

The record file contains the exact final mindset object, including its stable question ids, question text, answers, and notes. The update validates size limits, uniqueness, editability, and the definition's authority policy. Show the old-to-new diff before mutation when the user has not supplied an exact final record.

## Guardrails

- DO NOT let an agent edit a mindset through verified self.
- DO NOT bypass low-authority or immutable mindset policy.
- DO NOT treat a private-workspace projection as canonical mindset state.
- DO NOT continue a required mindset-backed skill after snapshot failure.
- DO NOT hand-edit `state.sqlite`.
