## Why

Houmao already demonstrates multi-agent pairwise writing workflows in `../agentsys2` and in the README, but the reusable material is mixed with live project state, generated outputs, mailbox state, and older memory configuration. A clean checked-in example would give users a concrete three-agent team they can inspect, copy, and materialize without inheriting runtime artifacts.

## What Changes

- Add a template-first `examples/writer-team/` example for a three-agent writing team.
- Include reusable role prompts for `story-writer`, `character-designer`, and `story-reviewer`.
- Include a relative-path pairwise loop plan and start charter that mirror the proven `agentsys2` story-chapter workflow.
- Include placeholder story artifact directories for chapters, character profiles, and reviews.
- Document setup, launch, and run-start commands using supported `houmao-mgr` project/easy/profile surfaces.
- Exclude live `.houmao/` runtime state, mailbox contents, credentials, generated story outputs, and legacy memory fields from the committed example.
- Update top-level documentation to point readers from the README story-writing quick start to the reusable example.

## Capabilities

### New Capabilities
- `writer-team-example`: Defines the repository example for a reusable three-agent story-writing team template.

### Modified Capabilities
- `readme-structure`: Add a requirement that the README story-writing loop section links to the reusable writer-team example when it exists.

## Impact

- Adds files under `examples/writer-team/`.
- Updates README and/or nearby documentation references so users can find the example from the existing agent-loop quick start.
- Does not change runtime behavior, CLI APIs, credential formats, memory storage, or mailbox protocols.
