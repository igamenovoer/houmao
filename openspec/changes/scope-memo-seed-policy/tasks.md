## 1. Runtime Semantics

- [x] 1.1 Refactor launch-profile memo seed payload loading so application code can distinguish represented memo content, represented pages content, and omitted components.
- [x] 1.2 Update `initialize` and `fail-if-nonempty` checks to inspect only represented targets.
- [x] 1.3 Update `replace` application to mutate only represented targets, preserving pages for memo-only seeds and preserving `houmao-memo.md` for pages-only seeds.
- [x] 1.4 Preserve intentional empty memo text as represented memo content and intentional empty `pages/` directories as represented page content.
- [x] 1.5 Ensure memo seed application result metadata reflects only components that were represented and written.

## 2. Launch Integration

- [x] 2.1 Verify explicit launch-profile-backed launch passes scoped memo seed application results through the existing launch completion payload.
- [x] 2.2 Verify easy profile-backed launch uses the same scoped memo seed application behavior.
- [x] 2.3 Confirm direct launches without a selected reusable profile still do not apply stored memo seeds.

## 3. Tests

- [x] 3.1 Add unit coverage for memo-only `initialize`, `replace`, and `fail-if-nonempty` seeds preserving existing pages.
- [x] 3.2 Add unit coverage for empty memo text with `replace` writing an empty `houmao-memo.md` without clearing pages.
- [x] 3.3 Add unit coverage for pages-only directory seeds preserving existing memo content.
- [x] 3.4 Add unit coverage for empty `pages/` directory seeds with `replace` clearing pages without rewriting memo.
- [x] 3.5 Add or adjust CLI/runtime tests for explicit launch-profile and easy profile launch paths where feasible without broad integration cost.

## 4. Documentation And Skills

- [x] 4.1 Update `docs/getting-started/launch-profiles.md` to describe component-scoped memo seed policies.
- [x] 4.2 Update `docs/reference/cli/houmao-mgr.md` to distinguish `--clear-memo-seed` from an intentional empty memo seed.
- [x] 4.3 Update `houmao-memory-mgr` guidance so agents explain that memo-only `replace` does not clear pages.
- [x] 4.4 Update project/easy launch-profile skill guidance if it describes memo seed policies.

## 5. Verification

- [x] 5.1 Run focused memo seed, project command, and docs tests covering the changed behavior.
- [x] 5.2 Run `pixi run openspec status --change scope-memo-seed-policy` and confirm the change remains apply-ready.
