## 1. Request Models And Validation

- [ ] 1.1 Add request-scoped `execution.model` fields and validation to the relevant gateway and managed-agent request models using the unified normalized model-selection shape.
- [ ] 1.2 Add shared resolution helpers that merge launch-resolved model defaults with partial request overrides and reject out-of-range reasoning values.
- [ ] 1.3 Add target-aware validation that rejects execution overrides for TUI-backed prompt routes instead of silently dropping them.

## 2. Gateway And Server Prompt Plumbing

- [ ] 2.1 Thread the execution override through direct gateway prompt control and queued gateway `submit_prompt` request payloads.
- [ ] 2.2 Thread the same execution override through managed headless `/turns`, managed-agent `submit_prompt`, and managed gateway prompt routes in `houmao-server`.
- [ ] 2.3 Extend gateway execution adapters and server direct-fallback headless execution paths to accept one effective per-turn model configuration without persisting it as live agent state.

## 3. Headless Runtime Projection

- [ ] 3.1 Implement per-turn model and reasoning projection for supported headless backends, preferring native CLI flags or env when available and temporary patch-and-restore otherwise.
- [ ] 3.2 Ensure per-turn projection and restore preserve the existing runtime home and provider session continuity instead of switching to a cloned per-turn home.
- [ ] 3.3 Add failure-path cleanup so interrupted or failed overridden turns do not leave stale temporary execution config behind.

## 4. CLI, Docs, And Verification

- [ ] 4.1 Add `--model` and `--reasoning-level` to `houmao-mgr agents turn submit`, `houmao-mgr agents gateway prompt`, and `houmao-mgr agents prompt`, with clear failure for TUI-backed targets.
- [ ] 4.2 Update the managed-agent API and CLI reference docs to describe request-scoped headless execution overrides, route coverage, and rejection semantics.
- [ ] 4.3 Add automated coverage for request validation, headless versus TUI routing, gateway direct versus queued prompt parity, and no-persistence behavior across consecutive turns.
