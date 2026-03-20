# Active Reference Inventory

Date: 2026-03-19

Purpose: inventory active demo surfaces that still described the server-backed pack as if the demo owned parser or lifecycle tracking semantics.

Search commands used:

```bash
rg -n "demo-local parser|lifecycle reducer|shadow parser|shadow-watch validation|demo-owned tracking|owner of tracking semantics|CAO-local|local shadow-watch ownership|state observation surface|server-tracked state" \
  scripts src openspec/specs tests docs \
  --glob '!openspec/changes/archive/**' \
  --glob '!src/houmao/demo/cao_dual_shadow_watch/**'

rg -n "case-interactive-shadow-validation|projection-demo|shadow-watch validation|live shadow parser and lifecycle validation" \
  tests/fixtures scripts/demo/houmao-server-dual-shadow-watch
```

Active files updated by this change:

- `scripts/demo/houmao-server-dual-shadow-watch/README.md`
- `scripts/demo/houmao-server-dual-shadow-watch/autotest/case-interactive-shadow-validation.md`
- `scripts/demo/houmao-server-dual-shadow-watch/profiles/projection-demo.md`
- `tests/fixtures/agents/roles/projection-demo/system-prompt.md`
- `tests/fixtures/agents/roles/projection-demo/README.md`

Active files already aligned and left unchanged after review:

- `openspec/specs/houmao-server-dual-shadow-watch-demo/spec.md`

Archived or unrelated references intentionally left untouched:

- `src/houmao/demo/cao_dual_shadow_watch/...`
- `openspec/specs/cao-dual-shadow-watch-demo/spec.md`
- archived change artifacts under `openspec/changes/archive/...`

Notes:

- `case-interactive-shadow-validation` remains the case identifier for automation compatibility.
- `samples.ndjson` and `transitions.ndjson` remain the persisted artifact names because they still describe consumed server payloads and recent server-authored transitions accurately.
- A post-change targeted grep against the active demo surfaces no longer reports stale `shadow parser and lifecycle validation` wording.
