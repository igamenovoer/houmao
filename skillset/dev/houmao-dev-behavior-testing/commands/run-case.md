# Run One Committed Behavior Case

## Workflow

1. **Invoke `plan-run`** for one exact case revision or stable variant, selected providers, and context overrides.
2. **For every planned fresh attempt, invoke `execute-case`.** Preserve incomplete attempts and use a new context for retries.
3. **Invoke `adjudicate-case`** after each attempt's evidence is frozen.
4. **Stop when all configured attempts have verdicts or explicit incomplete reasons.** Do not add opportunistic attempts after seeing an unfavorable result.
5. **Invoke `report-run`** and return the aggregate case outcome, evidence root, limitations, and cleanup status.

If the case requires a declared multi-turn stimulus, use the native planning tool to execute only the recorded turn sequence while keeping one attempt and one session boundary.

## Guardrails

- DO NOT reduce the configured repetition count after a failure.
- DO NOT reuse one conversation for independent repetitions.
