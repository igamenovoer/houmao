## 1. Establish the new reference structure

- [x] 1.1 Create the new `docs/reference/agents/` and `docs/reference/gateway/` subtree structures with `index.md` entrypoints plus `contracts`, `operations`, and `internals` subdirectories.
- [x] 1.2 Add short index pages for both subtrees that explain the documentation structure, introduce key terms, and link readers to the detailed pages by goal.
- [x] 1.3 Establish a consistent page pattern for both subtrees that includes page purpose, mental model, exact technical detail, representative examples or artifact shapes, Mermaid sequence diagrams for important procedures, and source references.

## 2. Document runtime-managed agents

- [x] 2.1 Add agent contract documentation covering session identity and targeting behavior, runtime-managed control surfaces, and the runtime-owned storage or manifest concepts relevant to public control.
- [x] 2.2 Add agent operations documentation covering session lifecycle plus message-passing mode differences across direct prompt turns, raw control input, mailbox prompt flows, and gateway-routed requests, with Mermaid sequence diagrams where the flow materially helps understanding.
- [x] 2.3 Add agent internals documentation covering runtime state management, tmux environment publication, authoritative runtime artifacts, and runtime error or recovery boundaries.

## 3. Document the agent gateway

- [x] 3.1 Add gateway contract documentation covering gateway-capable versus live-gateway states, attach contracts and tmux env bindings, implemented HTTP routes and status payloads, and durable gateway state artifacts with representative examples.
- [x] 3.2 Add gateway operations documentation covering launch-time auto-attach, attach-later, detach, status inspection, stale live-binding invalidation, and the difference between direct runtime control and gateway-routed queued control, with Mermaid sequence diagrams for the important flows.
- [x] 3.3 Add gateway internals documentation covering durable queue behavior, current-instance state and epochs, gateway-local health versus managed-agent availability, recovery or reconciliation boundaries, and current v1 live-adapter scope.

## 4. Align overview pages and verify clarity

- [x] 4.1 Update `docs/reference/index.md`, `docs/reference/brain_launch_runtime.md`, and `docs/reference/agents_brains.md` so they point readers to the new agent and gateway reference subtrees instead of duplicating deep detail.
- [x] 4.2 Ensure every detailed page identifies the source files or tests it reflects and clearly distinguishes implemented current behavior from deferred or future-facing behavior.
- [x] 4.3 Do a final clarity pass across both subtrees to ensure terminology is introduced clearly, important procedures use readable Mermaid sequence diagrams, examples are present where needed, and the docs remain approachable for both first-time readers and developers.
