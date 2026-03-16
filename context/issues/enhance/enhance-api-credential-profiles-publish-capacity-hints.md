# Enhancement Proposal: API Credential Profiles Should Publish Advisory Capacity And Rate-Limit Hints

## Status
Proposed

## Summary
Add an optional, structured metadata file for each local API credential profile so callers can plan agent creation using declared capacity hints such as:

- `max_concurrent_agents`
- `requests_per_minute`
- `tokens_per_minute`
- optional provider/account notes

The goal is not to hard-enforce provider quotas in the first step. The goal is to let demos, wrappers, schedulers, and operator tooling make better launch decisions before they oversubscribe one credential profile by accident.

## Why
Today the credential-profile contract only defines local credential material:

- `files/...`
- `env/vars.env`

That is enough to launch agents, but it does not tell callers anything about how much load a given profile is intended to carry.

This creates a practical planning gap:

- a demo wrapper cannot tell whether one credential profile is meant for one agent or several,
- a future orchestrator cannot pick between multiple blueprints using the same provider account intelligently,
- concurrent launch flows cannot distinguish "safe to share this profile" from "keep this lane reserved for one expensive worker",
- operators have no structured place to record provider-side limits or local policy such as "use this key for at most two active agents".

The current docs and schemas confirm that this metadata surface does not exist yet:

- credential profiles are documented as `files/...` plus `env/vars.env` only,
- brain recipes select `credential_profile` by name only,
- tool adapters allowlist env vars for projection but do not model credential capacity,
- build manifests record which credential profile was used, but not what capacity that profile advertises.

For mailbox demos, CAO-backed tutorial packs, and future multi-agent scheduling, that missing planning contract becomes noticeable quickly.

## Requested Enhancement
### 1. Add an optional per-profile capacity metadata file
Define one optional metadata file under each credential profile, separate from `env/vars.env`, for example:

```text
<agent-def-dir>/brains/api-creds/<tool>/<cred-profile>/limits.yaml
```

or another explicitly named structured file with the same purpose.

This file should remain local-only and uncommitted by default, just like the credential profile itself.

### 2. Keep the contract advisory-first
The first version should be planning metadata, not a hard scheduler or rate-limit enforcement system.

The runtime and callers should be able to treat the declared values as:

- advisory capacity hints,
- local operator policy,
- optional input into launch planning and demo defaults.

They should not be required to reject launches automatically in v1.

### 3. Define a minimal typed schema
The schema should be small and generic enough to work across providers. At minimum it should support fields like:

```yaml
schema_version: 1
provider: anthropic
account_label: personal-a
capacity:
  max_concurrent_agents: 2
  requests_per_minute: 50
  tokens_per_minute: 200000
  advisory_only: true
notes: "Shared personal key; avoid running more than one long-context worker at a time."
```

Exact field names can change, but the contract should cover:

- a maximum concurrent-agent hint,
- request-rate information,
- token-rate information when relevant,
- an explicit marker that these values are advisory/local policy rather than guaranteed provider truth,
- optional freeform notes.

### 4. Expose the metadata to callers
Once loaded, the metadata should be easy for callers to inspect without re-parsing ad hoc files.

At minimum, one of these should exist:

- a builder/runtime helper that loads credential-profile capacity metadata,
- build-manifest summary fields that record the selected profile's advertised capacity,
- a small CLI inspection surface for profile metadata.

The key requirement is that launch-planning code can consume this information cheaply and consistently.

### 5. Document how blueprints and recipes relate to the metadata
Recipes should continue to select `credential_profile` by name, and blueprints should continue to inherit that choice through their bound recipe.

This enhancement should document clearly that:

- the recipe chooses the credential profile,
- the credential profile may publish advisory capacity metadata,
- a caller can inspect that metadata before deciding how many agents to launch from blueprints that resolve to that profile.

### 6. Enable caller-side planning decisions
At least one repo-owned caller flow should be able to use the metadata for planning, for example:

- a demo runner choosing a safe default number of agents,
- a multi-agent wrapper deciding whether to reuse one blueprint lane or switch to another,
- an inspection/report command surfacing "this profile advertises `max_concurrent_agents: 1`".

The first implementation can stay lightweight. The important step is making the data available in a structured form.

## Acceptance Criteria
1. The credential-profile contract supports an optional structured metadata file for advisory capacity and rate-limit hints.
2. The metadata schema includes at least a concurrent-agent hint plus request-rate information.
3. The schema is documented in repo-owned docs for agent brains / credential profiles.
4. Recipes and blueprints continue to reference credential profiles by name; no secrets move into recipes or blueprints.
5. Builder/runtime code can load and validate the metadata when present.
6. Malformed metadata fails with a clear validation error instead of being silently ignored.
7. At least one caller-facing surface can inspect or report the advertised capacity for the selected credential profile.
8. Tests cover valid metadata loading plus at least one malformed-metadata failure case.

## Likely Touch Points
- `tests/fixtures/agents/brains/api-creds/README.md`
- `tests/fixtures/agents/README.md`
- `docs/reference/agents_brains.md`
- `src/houmao/agents/brain_builder.py`
- any runtime/helper model layer used for loading brain recipes and profile metadata
- demo/tutorial runners that want to plan multi-agent startup from blueprint or recipe selections

## Non-Goals
- No requirement to build a full distributed quota manager in the same enhancement.
- No requirement to enforce provider rate limits at runtime in v1.
- No requirement to make every credential profile declare exact provider quotas.
- No requirement to track real-time token consumption across processes in the first implementation.
- No requirement to move secrets out of `api-creds/` or make credential metadata committed by default.

## Suggested Follow-Up
- Capture the exact metadata schema and loading path in an OpenSpec change.
- Decide whether the preferred file name should be `limits.yaml`, `capacity.yaml`, or another explicit contract name.
- Decide whether build manifests should embed a normalized summary of the selected profile's hints, or only record the source metadata path.
- Add a small inspection command so operators can ask which credential profiles are configured for low-concurrency versus high-throughput use.
