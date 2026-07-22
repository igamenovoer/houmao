# Entrypoint-First Prompting And The `houmao` Trigger Keyword

Status: accepted
Date: 2026-07-22
Related: none

The Houmao system-skill design expects a specific prompting pattern: the first prompt of a session is recommended to invoke the entrypoint skill explicitly, after which the agent has enough routing context to select the right skill itself. For natural-language prompts to trigger Houmao skills reliably through implicit routing, the prompt should contain the keyword `houmao`. The README example dialogues must teach exactly this pattern, or newcomers will learn invocation habits the system is not designed around.

## Current Decision

1. The first example prompt in a README dialogue (or any fresh session) invokes the entrypoint skill explicitly: `$houmao-admin-entrypoint ...` for human-operator work. Explicit-only skills (`$houmao-agent-loop-pro`, `$houmao-agent-loop-lite`, `$houmao-admin-welcome`) always use their handle regardless of session history.
2. Subsequent prompts in the same session use natural language and include the keyword `houmao` so implicit skill routing triggers reliably; they do not repeat the handle.
3. The expected-AI-response contract is unchanged (concrete entities, past-tense steps, state before summary).

## Affected Artifacts

- `openspec/changes/readme-newcomer-revision/imsight-design/usecases/uc-01-first-managed-agent.md`: Event 001 prompt now starts `$houmao-admin-entrypoint`; Event 002 uses natural language with the `houmao` keyword.
- `openspec/changes/readme-newcomer-revision/imsight-design/usecases/uc-02-operator-coordinated-team.md`: both events use natural language with the `houmao` keyword; a note records the fresh-session explicit form.
- `openspec/changes/readme-newcomer-revision/imsight-design/usecases/uc-03-pro-agent-loop-run.md`: Event 001 keeps the explicit-only `$houmao-agent-loop-pro` handle; Event 002 uses the `houmao` keyword.
- `openspec/changes/readme-newcomer-revision/specs/readme-structure/spec.md`: the usage-examples requirement now mandates the entrypoint-first pattern and the `houmao` keyword.
- `openspec/changes/readme-newcomer-revision/tasks.md`: task 3.3 cites this ADR.

## Refinement History

### 2026-07-22 - Initial Decision

- Instruction: "You must show the entrypoint skill invocation. Our system is designed in such a way that the first prompt is recommended to invoke entrypoint skill with; later the agent should be able to find out what to call. And, to reliably trigger our skills, the keyword `houmao` should be used in prompt."
- Applied changes: revised the example events in all three use cases, added the invocation-pattern clauses to the spec delta's usage-examples requirement, and pointed task 3.3 at this ADR.
