## 1. New recovery reference page

- [x] 1.1 Create `docs/reference/run-phase/degraded-stale-recovery.md` with the four design sections: trigger conditions, probe classification, recovery paths, and cleanup integration
- [x] 1.2 Include a Mermaid diagram showing the probe → classify → route flow
- [x] 1.3 Verify all three probe classes (`healthy`, `degraded_missing_primary`, `stale_missing_session`) and both commands (`stop`, `relaunch`) are covered
- [x] 1.4 Run `pixi run format` and `pixi run lint` on the new page

## 2. Update session-lifecycle reference

- [x] 2.1 Add a degraded/stale recovery subsection to `docs/reference/run-phase/session-lifecycle.md`
- [x] 2.2 Update the lifecycle Mermaid diagram to show the recovery branch (or add a note if the diagram becomes too crowded)
- [x] 2.3 Add a cross-reference link to the new `degraded-stale-recovery.md` page

## 3. Update CLI reference

- [x] 3.1 Update `agents stop` description in `docs/reference/cli/houmao-mgr.md` to mention degraded/stale recovery routing
- [x] 3.2 Update `agents relaunch` description in `docs/reference/cli/houmao-mgr.md` to mention degraded/stale recovery routing
- [x] 3.3 Update `agents cleanup session` description in `docs/reference/cli/houmao-mgr.md` to document `--purge-registry` semantics for confirmed broken authority
- [x] 3.4 Add cross-reference links from the CLI page to the new recovery page

## 4. Update registry and subsystem references

- [x] 4.1 Update `docs/reference/registry/operations/discovery-and-cleanup.md` to reference the recovery page when explaining `--purge-registry`
- [x] 4.2 Update `docs/reference/gateway/contracts/protocol-and-state.md` or `docs/reference/gateway/operations/mail-notifier.md` to note gateway degraded-context interaction with recovery
- [x] 4.3 Update `docs/reference/managed_agent_api.md` to cross-reference the recovery page from the attach parameter descriptions

## 5. Update index and getting-started

- [x] 5.1 Add the new recovery page to `docs/index.md` under the Run Phase section
- [x] 5.2 Update `docs/getting-started/overview.md` to mention recovery as part of the two-phase lifecycle
- [x] 5.3 Verify all new and updated internal links resolve (no broken relative paths)

## 6. Validation

- [x] 6.1 Run `pixi run docs-build` and confirm no MkDocs build errors
- [x] 6.2 Run `pixi run lint` on all modified files
- [x] 6.3 Read the rendered recovery page end-to-end for clarity and completeness
