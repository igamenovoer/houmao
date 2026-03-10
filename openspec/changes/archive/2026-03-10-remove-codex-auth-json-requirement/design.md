## Context

The current brain-builder contract treats every credential file mapping declared by a tool adapter as mandatory. For Codex, that means the selected credential profile must always provide `files/auth.json`, because the Codex adapter currently lists that mapping and the builder fails if the file is absent.

We now have direct evidence that the Yunwu-backed custom-provider path does not need `auth.json` for Codex itself: brain build failed only because of the repo-owned mapping contract, while Codex still completed the exact-match smoke prompt when launched without `auth.json` in `CODEX_HOME`. That means the requirement lives in our builder/adapter layer, not in the Codex runtime path we are trying to support.

## Goals / Non-Goals

**Goals:**

- Allow env-backed Codex credential profiles to omit `files/auth.json`.
- Preserve backward compatibility for profiles that still carry a local `auth.json`.
- Keep the change generic at the builder/adapter contract level instead of hard-coding a Yunwu-only exception.
- Remove repo docs that currently tell users to create an empty placeholder file that Codex does not need.
- Fail fast before Codex launch when neither a valid `auth.json` login state nor `OPENAI_API_KEY` is available.
- Reconcile the existing Yunwu change docs with the new optional-file contract.

**Non-Goals:**

- Changing how Codex itself authenticates to custom providers.
- Removing support for projecting credential files when a tool really does need them.
- Allowing Codex launches to proceed with neither login-state auth nor env-based API-key auth.
- Reworking non-Codex tool adapters unless required for backward-compatible schema support.
- Archiving the earlier Yunwu change as part of this follow-up.

## Decisions

### 1. Add explicit optionality to credential file mappings

The builder will grow explicit support for optional credential file mappings via a per-mapping `required` boolean with backward-compatible default behavior. Mappings remain required unless they explicitly set `required: false`.

Rationale:

- It solves the actual contract problem instead of special-casing one file name.
- It preserves the current strict behavior for adapters that truly require a file.
- It gives the adapter schema an honest way to represent env-only versus file-backed auth paths.

Alternative considered:

- Remove Codex `auth.json` projection entirely without changing the schema.
- Rejected because it would make the behavior implicit and could break any existing local Codex profiles that still rely on file projection.

### 2. Mark the Codex `auth.json` mapping optional

Once the schema supports optional mappings, the Codex adapter will mark `auth.json` optional so env-backed profiles can omit it while existing profiles that still provide it keep projecting it.

Rationale:

- This matches the observed runtime behavior: Codex does not need the file for the custom-provider path.
- It minimizes disruption to existing local profiles by keeping projection available when the file exists.

Alternative considered:

- Keep the builder strict and continue documenting `{}` as the required workaround.
- Rejected because it preserves a repo-owned requirement that has already been disproven by live verification.

### 3. Reframe docs around env-backed credentials as the primary contract

Codex docs and fixture guidance will describe `env/vars.env` plus provider config as the required auth path for custom OpenAI-compatible providers, and will stop describing empty `auth.json` as a required compatibility step.

Rationale:

- The current docs encode an implementation artifact as if it were a functional requirement.
- Updating the docs keeps future profiles from cargo-culting unnecessary files.

Alternative considered:

- Keep the docs vague and rely on code changes alone.
- Rejected because users will keep copying the old pattern unless the written guidance changes too.

### 4. Add explicit Codex pre-launch auth validation

Codex launch preparation in `src/gig_agents/agents/brain_launch_runtime/backends/codex_bootstrap.py` will treat authentication as satisfied only when at least one of these is true:

1. a valid `auth.json` login state is present in the runtime home, or
2. `OPENAI_API_KEY` is present in the effective runtime environment.

The bootstrap helper will follow the existing Claude bootstrap pattern and accept the effective runtime environment so it can check `OPENAI_API_KEY` at launch time. `auth.json` will count as a valid login state only when it parses as a non-empty top-level JSON object; placeholder files such as `{}` will not satisfy the requirement. If neither condition is met, the system will fail before launching Codex with an explicit error.

Rationale:

- Removing the mandatory placeholder file must not turn into “launch with no usable auth configured”.
- This matches the real Codex contract surfaced by validation: login-state auth and env-key auth are both valid, but at least one must exist.

Alternative considered:

- Rely on Codex itself to fail later with whatever message it emits.
- Rejected because the repo runtime can provide a clearer, earlier operator error and can keep the launch contract explicit.

### 5. Reconcile the earlier Yunwu change spec in this follow-up

This follow-up will update the earlier `add-codex-yunwu-agent` change spec so it no longer requires `files/auth.json` for env-backed Codex profiles.

Rationale:

- The review surfaced a direct contradiction between the earlier Yunwu change and this follow-up.
- Reconciling that spec here keeps the OpenSpec tree internally consistent instead of leaving the contradiction for a later cleanup.

Alternative considered:

- Leave the earlier Yunwu change untouched and rely on future archive/sync work to resolve the contradiction.
- Rejected because it leaves two active change artifacts disagreeing about the same contract.

## Risks / Trade-offs

- [Schema compatibility drift] -> Default optionality to “required” so existing adapters behave the same until they opt in.
- [Hidden dependence on Codex `auth.json` in older local setups] -> Preserve projection when the optional file exists, and verify one env-only path plus one file-present path in tests.
- [Auth validation false positives] -> Use a minimal content-aware `auth.json` heuristic: only a non-empty top-level JSON object counts as login state; placeholder `{}` remains invalid and still requires `OPENAI_API_KEY`.
- [Spec drift with the unarchived Yunwu change] -> Update the earlier Yunwu change spec in this follow-up so the new contract is reflected in both active changes.
- [Implementation complexity leaking into docs] -> Keep user-facing docs simple: env vars are required, `auth.json` is optional for Codex custom providers.

## Migration Plan

1. Extend the builder’s credential-file mapping schema and parser to support a `required` boolean on credential file mappings, defaulting to `true`.
2. Mark the Codex adapter’s `auth.json` mapping optional.
3. Update `ensure_codex_home_bootstrap()` to accept the effective runtime environment and fail fast unless a non-empty `auth.json` object or `OPENAI_API_KEY` is present.
4. Update tests so missing optional files are skipped while missing required files still fail, and so Codex launch validation enforces the “usable auth.json or OPENAI_API_KEY” rule.
5. Remove the empty-`auth.json` requirement from Codex/Yunwu fixture docs, update the earlier Yunwu change spec to the new contract, and re-verify the env-only Yunwu flow.
