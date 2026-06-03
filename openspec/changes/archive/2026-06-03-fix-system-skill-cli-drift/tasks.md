## 1. Skill Guidance Corrections

- [x] 1.1 Update `houmao-agent-instance` join guidance to use `houmao-mgr agents self join --agent-name ...` and remove stale `houmao-mgr agents join --name ...` wording.
- [x] 1.2 Update `houmao-memory-mgr` live memory guidance to distinguish current-session `agents self memory ...` from selected-agent `agents single --agent-name|--agent-id ... memory ...`.
- [x] 1.3 Update legacy pairwise v2, v3, and v4 routing prose so managed-memory references delegate to current `houmao-memory-mgr` scoped surfaces instead of `houmao-mgr agents memory ...`.
- [x] 1.4 Update `houmao-agent-email-comms` managed-agent fallback guidance so `mail move` uses `--destination-box` rather than `--box`.
- [x] 1.5 Remove surviving generic command-template wording from packaged `houmao-agent-email-comms`, `houmao-agent-gateway`, `houmao-agent-instance`, and `houmao-mailbox-mgr` guidance.

## 2. Regression Coverage

- [x] 2.1 Add or update system-skill content tests asserting packaged skills do not reference removed `houmao-mgr agents join`, removed `houmao-mgr agents memory`, stale `mail move --box`, or command-template support wording.
- [x] 2.2 Add or update focused CLI-shape tests confirming `agents self join`, `agents self memory`, `agents single ... memory`, and `mail move --destination-box` remain exposed by the current `houmao-mgr` command graph.
- [x] 2.3 Ensure the command-template-retirement content tests still pass and remain compatible with the stricter stale-wording checks.

## 3. Validation

- [x] 3.1 Run `openspec validate fix-system-skill-cli-drift --strict`.
- [x] 3.2 Run focused tests for packaged system-skill content and affected `houmao-mgr` CLI command shapes.
- [x] 3.3 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test` or document any validation that cannot be run.
