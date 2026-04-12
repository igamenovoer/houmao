## Why

Three doc gaps remain after the recent `specialist set` and Codex CLI config override features landed: the README and system-skills-overview skill tables still describe `houmao-specialist-mgr` without the `set/edit` verb, and the launch policy reference page is missing the new `codex.append_unattended_cli_overrides` hook. The detailed guide and CLI reference were already updated in the implementing commits; these are the residual high-visibility entry points.

## What Changes

- **README.md line 383**: Add "set" to the `houmao-specialist-mgr` skill verb list so the table reads "Create, **set**, list, inspect, remove, launch, and stop".
- **docs/getting-started/system-skills-overview.md line 37**: Add "set" to the `houmao-specialist-mgr` skill description so it reads "Create, **set**, list, inspect, remove easy specialists".
- **docs/reference/build-phase/launch-policy.md lines 53-58**: Add a row for `codex.append_unattended_cli_overrides` to the Codex hooks table, describing its purpose (appends `-c` override arguments for `approval_policy`, `sandbox_mode`, and `notice.hide_full_access_warning` so project-local config cannot weaken unattended posture).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `readme-structure`: The `houmao-specialist-mgr` skill table row adds the "set" verb.
- `docs-system-skills-overview-guide`: The `houmao-specialist-mgr` skill description adds the "set" verb.
- `docs-launch-policy-reference`: The Codex hooks table adds the `codex.append_unattended_cli_overrides` hook row.

## Impact

- **README.md** — one table cell reworded (~2 words added).
- **docs/getting-started/system-skills-overview.md** — one table cell reworded (~1 word added).
- **docs/reference/build-phase/launch-policy.md** — one table row added.
- No code, no tests, no API changes.
