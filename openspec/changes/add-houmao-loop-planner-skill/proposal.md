## Why

Houmao now has packaged loop skills for pairwise and relay run control, but it does not yet provide a packaged planning skill for the earlier operator workflow where the operator authors one reusable loop bundle in a user-designated directory and hands those artifacts to participants without relying on agent-local Houmao runtime directories. Users need one supported skill that turns high-level loop intent into a static operator-owned bundle that is easy for humans to author and review, with Markdown as the main format and TOML reserved only for the simple metadata fields that benefit from a machine-shaped format.

## What Changes

- Add a packaged Houmao-owned system skill named `houmao-loop-planner` for authoring operator-owned loop bundles in a user-designated directory.
- Define the loop bundle as a simplified Markdown-first directory rooted at `plan.md`, `participants.md`, `execution.md`, and `distribution.md`, with TOML kept only for `profile.toml` and `runs/charter.template.toml`.
- Require the planning lane to normalize loop kind, designated master, participant set, per-agent calling boundaries, execution flow, completion policy, stop policy, and reporting posture explicitly in structured Markdown.
- Require the planning lane to keep distribution of artifacts as an explicit operator responsibility, documented in `distribution.md` rather than hidden behind planner-owned delivery mechanics.
- Require the planning lane to render a Mermaid graph that shows the operator outside the execution loop, the master role, the execution topology, and the supervision, completion, and stop checkpoints.
- Require the planning lane to keep the authored bundle static and operator-owned rather than mixing it with mutable run ledgers or agent-local runtime state.
- Require the skill to prepare a run-charter template and route later runtime activation to the existing loop runtime skills rather than introducing a new loop execution engine or direct live-control API.

## Capabilities

### New Capabilities
- `houmao-loop-planner-skill`: packaged system-skill guidance for authoring operator-owned loop bundles, documenting participant and execution contracts in Markdown, and preparing runtime handoff templates for pairwise or relay loop execution.

### Modified Capabilities

None.

## Impact

- Affected skill assets under `src/houmao/agents/assets/system_skills/`, including a new packaged skill directory for `houmao-loop-planner`
- Affected system-skill packaging and projection tests under `tests/unit/agents/`
- Cross-skill composition with existing Houmao-owned skills, especially `houmao-agent-loop-pairwise`, `houmao-agent-loop-relay`, and `houmao-adv-usage-pattern`
- No new gateway, mailbox, or manager runtime API surface; this change defines an operator-facing authoring and handoff skill over existing loop runtime primitives
