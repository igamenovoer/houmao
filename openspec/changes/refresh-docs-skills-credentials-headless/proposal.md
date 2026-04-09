## Why

Three recent landed changes — the two agent-loop skills, the first-class `houmao-mgr credentials` command family, and request-scoped headless execution overrides — have drifted out of sync with the README, the system-skills narrative guide, and the CLI reference. Users are told there are "twelve" system skills when the catalog ships fourteen, agents routed by `houmao-credential-mgr` reference a top-level `houmao-mgr credentials` group that does not appear in the CLI reference, and the `agents prompt` prompt surface silently accepts `--model`/`--reasoning-level` without any documentation of the flags or their TUI-target rejection semantics.

## What Changes

- Update the README "System Skills" subsection so the catalog table enumerates all fourteen packaged system skills, including `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay`, and so the narrative count and auto-install wording match `src/houmao/agents/assets/system_skills/catalog.toml`.
- Update `docs/getting-started/system-skills-overview.md` so the "Packaged Skills" table, the narrative count, the auto-install ASCII diagram, and the per-set expansion table all reflect the fourteen-skill catalog and the resolved `managed_launch_sets` / `managed_join_sets` / `cli_default_sets` contents.
- Add a first-class `### credentials — Dedicated credential management` section to `docs/reference/cli/houmao-mgr.md` under "Command Groups" with a subcommand table, per-tool option summaries, and a clear statement of how `credentials` relates to `project credentials`.
- Add a `credentials` entry to the README "CLI Entry Points" table and to the `docs/index.md` "CLI Surfaces" list so the new surface is discoverable from both entry points.
- Document the request-scoped headless execution overrides (`--model`, `--reasoning-level`) on the three supported prompt surfaces — `houmao-mgr agents prompt`, `houmao-mgr agents turn submit`, and `houmao-mgr agents gateway prompt` — inside `docs/reference/cli/houmao-mgr.md`, and confirm the TUI-target rejection semantics and no-persistence contract are stated on the operator-facing page.
- Cross-check `docs/reference/managed_agent_api.md` so the extended payload shape for `POST /houmao/agents/{agent_ref}/turns`, `/gateway/control/prompt`, `/gateway/requests`, and `POST /v1/control/prompt` / `POST /v1/requests` (`submit_prompt`) carries the same request-scoped `execution.model` object used by the CLI.
- Keep the loop-skill narrative depth to **catalog rows only** for this change. A dedicated narrative subsection or reference page for the loop skills is out of scope and may be proposed as a follow-up.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `docs-readme-system-skills`: Strengthen the README system-skills requirements so the catalog row table and the narrative skill-count wording SHALL track `catalog.toml` and SHALL enumerate both agent-loop skills.
- `docs-system-skills-overview-guide`: Strengthen the overview-guide requirements so the per-skill table, the narrative count, and the install-defaults diagram SHALL reflect the fourteen-skill catalog and the resolved auto-install set contents.
- `docs-cli-reference`: Add requirements that the `houmao-mgr` CLI reference SHALL include a dedicated `credentials` command-group section under "Command Groups", SHALL document the request-scoped headless execution overrides on all three supported prompt surfaces, and SHALL state the TUI-target rejection and no-persistence semantics on the operator-facing page.

## Impact

- Affected docs: `README.md`, `docs/index.md`, `docs/getting-started/system-skills-overview.md`, `docs/reference/cli/houmao-mgr.md`, and potentially `docs/reference/managed_agent_api.md`. A new `docs/reference/cli/credentials.md` is **not** in scope; the credentials coverage lives as a section of `houmao-mgr.md` plus cross-links, matching the shape of `brains`, `system-skills`, and `mailbox` today.
- Affected specs: `openspec/specs/docs-readme-system-skills/spec.md`, `openspec/specs/docs-system-skills-overview-guide/spec.md`, `openspec/specs/docs-cli-reference/spec.md`.
- No code changes. No CLI surface changes. No user-visible behavior changes outside documentation. Managed runtime, system-skills projection, credential catalog, and headless override plumbing are already in place — this change is a pure docs sync to close the gap with the current shipped surface.
- Affected workflows: any operator or agent who reaches for `houmao-mgr credentials ...` through the packaged `houmao-credential-mgr` skill routing, any operator reading the README or overview guide to count or discover shipped system skills, and any operator reaching for per-turn model or reasoning overrides on `agents prompt`, `agents turn submit`, or `agents gateway prompt`.
