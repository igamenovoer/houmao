# Execute One Behavior Case Attempt

## Workflow

1. **Verify attempt admission.** Require a frozen run manifest, selected case revision, unused attempt directory, and supported context/provider combination.
2. **Prepare the isolated context.** Follow [../references/fixture-contexts.md](../references/fixture-contexts.md) and invoke `snapshot-context` before launch.
3. **Launch a fresh session.** Delegate raw provider launch or use the supported managed-agent lifecycle named by the context; verify the live target.
4. **Start observable capture.** Enable provider-native events and bounded terminal, command, filesystem, and runtime evidence available for this context.
5. **Submit the exact stimulus once.** Preserve whitespace and qualifiers and do not include oracle hints, expected skill names beyond the stimulus, or evaluator commentary.
6. **Observe to the declared boundary.** Stop at the case timeout, terminal result, required clarification, bounded action, or explicit stop condition.
7. **Stop and freeze the attempt.** Invoke `collect-evidence`, preserve partial failures, and record launch and cleanup status.

If the provider requires a case-specific input method, use the native planning tool to adapt only the transport while preserving the exact stimulus, fresh-session boundary, allowed effects, and observation stop condition.

## Failure Handling

Authentication, startup, confirmation, instrumentation, or fixture failures produce `incomplete` evidence. Preserve the attempt; do not resend the stimulus in the same session and call it a clean retry. A retry receives a new attempt number and fresh context.

## Guardrails

- DO NOT reveal expected routes or forbidden behavior to the agent under test.
- DO NOT reuse a provider conversation across attempts unless the case explicitly tests repeated routes in one session.
- DO NOT intervene in agent behavior after the exact stimulus unless the case declares a follow-up event.
