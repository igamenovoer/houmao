## 1. Registry Reference Scaffold And Navigation

- [x] 1.1 Create the `docs/reference/registry/` subtree with the planned page layout (`index.md`, `operations/`, `contracts/`, and `internals/`).
- [x] 1.2 Write `docs/reference/registry/index.md` as the landing page with motivation, key terms, reading path, and related-reference links.
- [x] 1.3 Update `docs/reference/index.md` and `docs/reference/realm_controller.md` so the new registry subtree is discoverable and the old embedded registry section becomes a concise summary plus links.

## 2. Contracts And Operations Pages

- [x] 2.1 Write `docs/reference/registry/contracts/record-and-layout.md` to document the effective root, override environment variable, hashed on-disk layout, and strict v1 record shape with representative examples.
- [x] 2.2 Write `docs/reference/registry/contracts/resolution-and-ownership.md` to explain canonical naming, `agent_key`, `generation_id`, freshness, duplicate-publisher conflicts, and malformed-or-expired record semantics.
- [x] 2.3 Write `docs/reference/registry/operations/discovery-and-cleanup.md` to explain tmux-local discovery versus shared-registry fallback, `cleanup-registry`, and operator-facing interpretation of removed, preserved, and failed cleanup results.
- [x] 2.4 Add embedded Mermaid `sequenceDiagram` blocks to the procedure-heavy registry pages where they materially clarify discovery fallback, cleanup, or other multi-step flows.

## 3. Runtime Integration Page

- [x] 3.1 Write `docs/reference/registry/internals/runtime-integration.md` to explain registry publication hooks, manifest persistence interaction, gateway and mailbox refresh paths, and stop-time record clearing.
- [x] 3.2 Document the persisted `registry_generation_id` behavior and the non-fatal warning boundary for registry refresh or cleanup failures after successful runtime actions.
- [x] 3.3 Add source-reference sections to the detailed registry pages so each one points to the defining implementation files and behavior-pinning tests.

## 4. Consistency Review

- [x] 4.1 Re-read the new registry doc set against the active registry specs, implementation, and tests to confirm terminology, authority boundaries, and hardening semantics match current behavior.
- [x] 4.2 Verify Markdown structure, Mermaid blocks, examples, and internal links render cleanly and follow repository documentation conventions.
