## 1. Canonical Protected Layout

- [x] 1.1 Rename the protected audience routers and all protected routine entrypoints to `SKILL-MAIN.md`, update manifest route paths, and advance the system-skill manifest schema to v3.
- [x] 1.2 Add centralized public and parent-scoped entrypoint filename constants and make source, composition, frontmatter, and recursive subskill validation role-aware and ambiguity-safe.
- [x] 1.3 Add scanner-safety validation so a composed public skill contains no nested exact `SKILL.md` entrypoints.

## 2. Routing Instructions and Notation

- [x] 2.1 Update both executable public entrypoints to load the protected router's `SKILL-MAIN.md` explicitly while preserving actor-frame and welcome boundaries.
- [x] 2.2 Update both protected audience routers with exact child `SKILL-MAIN.md` load paths and selective-loading instructions.
- [x] 2.3 Add the standard `skill_invocation_notation` frontmatter declaration to every packaged instruction page that uses object-style designators and validate that declaration.

## 3. Generated Prompts and Upgrade Behavior

- [x] 3.1 Update generated mailbox-operation and notifier prompts to preserve tool-native public entrypoint invocation and state that protected traversal is parent-controlled.
- [x] 3.2 Update managed-agent role prompt fixtures and packaged metadata where they describe protected discovery or traversal.
- [x] 3.3 Mark receipt-owned packs drifted when their recorded manifest schema differs from the current schema and verify transactional upgrade to the new layout.

## 4. Tests and Documentation

- [x] 4.1 Update unit and integration tests for protected `SKILL-MAIN.md` paths, ambiguity rejection, scanner safety, actor routing, and unaffected top-level `SKILL.md` contracts.
- [x] 4.2 Update generated-prompt tests for Codex, Claude, Kimi, installed-pack, and fallback behavior.
- [x] 4.3 Update README and maintained documentation links and explanations to distinguish public `SKILL.md` from protected `SKILL-MAIN.md`.

## 5. Verification

- [x] 5.1 Run focused system-skill, brain-builder, mailbox-support, gateway-prompt, and integration tests.
- [x] 5.2 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test`, then validate the OpenSpec change.

Verification notes: formatting, lint, strict OpenSpec validation, and all change-focused tests pass. The repository-wide type check still reports seven pre-existing literal-type errors in untouched launch-policy modules. The broad 144-worker unit run exposed unrelated baseline and environment failures, including a missing orphan Plotly schema checkout, existing Codex launch-policy assertions, a Click error-text assertion, and headless subprocess timeouts; the two stale protected-skill test paths found by that run were corrected and pass serially.
