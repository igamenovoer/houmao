## Why

The current `houmao-agent-loop-pairwise-v2` guidance still mixes two different prestart models and leaves `initialize` and `start` instructions too dependent on transient message text. We need one consistent contract where pairwise-v2 writes durable per-run guidance into managed memory pages, keeps memo updates replaceable and bounded, and makes the default `initialize` and `start` behavior match the current routing-packet-first design.

## What Changes

- Revise `houmao-agent-loop-pairwise-v2` so the default `initialize` flow for routing-packet-backed runs validates prestart readiness and writes durable per-run guidance into managed memory pages instead of relying on standalone operator-origin initialization mail as the primary carrier.
- Revise `start` so the master-facing run charter is baked into a dedicated managed memory page and the live start message becomes a compact control-plane trigger that points at that durable page.
- Revise pairwise-v2 authoring so the skill asks for a plan output directory when one is not already known and writes generated plans under that directory with `plan.md` as the canonical entrypoint.
- Define a pairwise-v2-owned memo note convention with exact begin/end sentinels so callers can replace only the run-owned memo block for a given `run_id` and slot without introducing a global Houmao memo metadata system.
- Align the packaged skill guidance, supporting references, and docs with the existing routing-packet-first semantics: `precomputed_routing_packets` is the default prestart strategy, while participant preparation mail remains an explicit `operator_preparation_wave` lane.
- Keep page content and memo note content caller-authored and skill-owned rather than changing the general managed-memory free-form ownership contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v2-skill`: change the initialize/start contract to use durable memo-linked pages with replaceable run-owned memo blocks, and align the default prestart strategy with routing-packet validation instead of email-first initialization.

## Impact

- Affected packaged skill assets under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/`
- Affected pairwise-v2 OpenSpec behavior contract under `openspec/specs/houmao-agent-loop-pairwise-v2-skill/`
- Affected documentation for loop authoring and pairwise-v2 usage
- No new runtime dependency is required; replacement behavior uses exact string sentinel matching within caller-authored memo text
