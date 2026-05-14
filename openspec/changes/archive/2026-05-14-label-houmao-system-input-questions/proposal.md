## Why

Houmao system skills ask users for missing platform inputs in several different styles, which can obscure which values block execution and which values are optional defaults or modifiers. System-operation questions should consistently show required and optional information without imposing that format on task-intent or domain-design clarification.

## What Changes

- Add a shared Houmao system-skill contract for user questions about Houmao platform, setup, routing, launch, mailbox, credential, workspace, loop-execution, and lifecycle inputs.
- Require those questions to separate `Required` inputs from `Optional` inputs, including explicit default or skip behavior when optional inputs are not needed.
- Keep the rule out of user-task/domain-intent questions such as objectives, acceptance criteria, algorithm choices, content preferences, or loop business semantics unless the question is specifically about Houmao runtime behavior.
- Update direct-operation, touring, agent-definition, credential, mailbox, gateway, messaging, instance, workspace, and loop-operation skill guidance where those skills ask for Houmao system inputs.
- Add focused tests that verify the shared guidance and representative skill pages preserve the required/optional system-input contract.

## Capabilities

### New Capabilities
- `houmao-system-skill-input-questions`: Shared question-format contract for Houmao-owned system skills when asking users for Houmao system-operation inputs.

### Modified Capabilities
- `houmao-agent-loop-pro-skill`: Clarifies that loop authoring/execution subcommands use required/optional labels for Houmao runtime and artifact-location inputs, while intent clarification remains domain-focused.
- `houmao-agent-loop-pairwise-v5-skill`: Applies the same system-input question boundary to the existing generated-loop authoring and execution guidance.
- `houmao-touring-skill`: Aligns first-time-user system questions with required/optional labeling while preserving explanations, examples, defaults, and skip paths.

## Impact

- System skill Markdown under `src/houmao/agents/assets/system_skills/`, especially shared missing-input guidance and pages that ask for Houmao system inputs.
- OpenSpec specs for the shared system-input question contract and loop/touring skill behavior.
- Unit tests under `tests/unit/agents/test_system_skills.py`.
- No CLI/API behavior changes and no dependency changes.
