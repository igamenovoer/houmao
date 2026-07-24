# Runtime Variables

## Purpose

Read or administer definition-declared, typed, per-instance runtime values in the managed agent's canonical `state.sqlite`. Values are revisioned and isolated by agent identity. Launch-time prompt and memo rendering is a snapshot; a consuming skill that requires live state reads the current value again.

## Workflow

1. Preserve the inherited admin or verified-agent actor frame.
2. Select the read-only agent branch or explicit-target admin branch below.
3. Resolve only the target and variable key required by the selected command.
4. Run one maintained command and report the value, declaration, revision, or compare-and-set outcome.
5. Stop on identity, target, type, bounds, mutability, or stale-revision failure.

If the request does not map cleanly to these operations, use the native planning tool to build a step-by-step plan from the actor frame, variable declaration, revision contract, and user request, then execute the plan.

## Agent Branch

After fresh entrypoint identity verification, use only verified-self read commands:

```bash
houmao-mgr agents self instance-state variables list
houmao-mgr agents self instance-state variables get <key>
houmao-mgr agents self instance-state variables explain <key>
```

Do not accept a user-supplied path or agent id as self authority. If verified-self resolution fails, stop.

## Admin Branch

Require exactly one explicit target selector:

```bash
houmao-mgr agents single --agent-id <id> instance-state variables list
houmao-mgr agents single --agent-name <name> instance-state variables get <key>
houmao-mgr agents single --agent-id <id> instance-state variables explain <key>
houmao-mgr agents single --agent-id <id> instance-state variables set <key> \
  --value <value> \
  --expected-revision <revision>
```

Read the current revision before mutation. Preserve compare-and-swap failures and validation errors; do not retry with a guessed revision. The contract validates type, enum membership, and numeric bounds.

## Guardrails

- DO NOT use `agents self` as an admin target.
- DO NOT let an agent mutate runtime variables through the self surface.
- DO NOT declare or store secret runtime variables.
- DO NOT treat prompt text, memo text, or a previous snapshot as the live value when a skill declares a live consumer.
- DO NOT hand-edit `state.sqlite`.
