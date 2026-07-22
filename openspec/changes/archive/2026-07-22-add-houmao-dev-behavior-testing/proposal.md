## Why

Houmao has structural and deterministic tests for system-skill packaging, but it lacks a maintained way to qualify whether real provider agents activate, route, or deliberately avoid those skills under the intended admin and managed-agent contexts. The existing `houmao-dev-testing` name is also too broad because that skill exclusively qualifies TUI tracking evidence.

## What Changes

- Add a manual `houmao-dev-behavior-testing` development skill that plans, executes, adjudicates, repeats, and reports live system-skill behavior cases without treating hidden reasoning or exact prose as an oracle.
- Commit a versioned case catalog covering implicit and explicit activation, managed auto-prompt bootstrap, admin and managed-agent actor routing, shared-routine delegation, manual loop activation, and generated mailbox/notifier prompts.
- Define isolated context, immutable evidence, dimensional verdict, repetition, and aggregate-result contracts for nondeterministic provider behavior.
- **BREAKING**: Rename `houmao-dev-testing` to `houmao-dev-tui-testing`, including its skill identity, invocation examples, metadata, default artifact root, and qualification references, without changing its TUI recording and replay meaning.
- Keep both development skills outside the packaged Houmao system-skill collection and keep current system-skill behavior unchanged; failures found by behavior qualification become separate fixes.

## Capabilities

### New Capabilities

- `houmao-dev-behavior-testing-skill`: Defines the manual live-agent behavior qualification workflow, committed case catalog, evidence model, verdict model, provider/context matrix, and reporting contract.
- `houmao-dev-tui-testing-skill`: Defines the renamed TUI tracking qualification skill and requires semantic preservation across the breaking rename.

### Modified Capabilities

None.

## Impact

The change affects `skillset/dev/`, development-skill metadata, TUI qualification documentation and temporary-root examples, skill structure validation, focused tests for the development-skill surface, and OpenSpec artifacts. It adds no runtime dependency, does not install development skills into user or managed-agent homes automatically, and does not modify the six public system skills, the managed auto skill, actor packs, generated prompt text, or Houmao runtime authorization behavior.
