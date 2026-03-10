## Context

The repo already supports building Codex runtime homes from reusable brain components, but the checked-in Codex fixture set is still centered on the default first-party Codex setup. The default Codex config profile does not declare a custom provider, the default recipe still points at `personal-a-default`, and the current Codex adapter expects both allowlisted env vars and a projected `files/auth.json` in the selected credential profile.

At the same time, the local Codex setup guidance for custom OpenAI-compatible providers now expects `requires_openai_auth = false`, `env_key = "OPENAI_API_KEY"`, and `wire_api = "responses"`. The Yunwu-backed agent work therefore needs a repo-owned fixture profile that fits the existing brain-builder contract without embedding secrets into committed files.

## Goals / Non-Goals

**Goals:**

- Add an implementation-ready Codex fixture profile for the Yunwu OpenAI-compatible endpoint.
- Keep all secrets local-only under `tests/fixtures/agents/brains/api-creds/`.
- Preserve the existing default Codex profile and recipe so current local workflows are not broken.
- Make the Yunwu-backed setup discoverable through repo-owned config, recipe, and docs artifacts.
- Prove the profile works through a live Codex smoke prompt that sends `Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK` and expects the exact reply `YUNWU_CODEX_SMOKE_OK`.

**Non-Goals:**

- Changing Codex runtime backend semantics or headless session behavior.
- Generalizing the Codex adapter to provider-specific env var names in this change.
- Replacing the existing default Codex profile with the Yunwu-backed variant.
- Solving long-term removal of the Codex `auth.json` compatibility requirement unless validation shows it is necessary to unblock this change.

## Decisions

### 1. Add a dedicated `yunwu-openai` Codex config profile instead of mutating `default`

The change will add a separate secret-free Codex config profile under `tests/fixtures/agents/brains/cli-configs/codex/yunwu-openai/` rather than editing the existing `default` profile in place.

Rationale:

- Existing local flows and demos already reference `default` plus `personal-a-default`.
- A dedicated profile makes the custom-provider workflow explicit and reversible.
- It keeps the change narrowly scoped to the new Yunwu-backed agent path.

Alternative considered:

- Reuse `default` and rewrite it for Yunwu.
- Rejected because it would silently change current Codex behavior for anyone already relying on the existing default profile.

### 2. Normalize local credential env names to `OPENAI_*`

The Yunwu credential profile will store plain-text key/value entries in `env/vars.env`, but it will use `OPENAI_API_KEY` and `OPENAI_BASE_URL` rather than provider-specific names such as `YUNWU_OPENAI_API_KEY`.

Rationale:

- The current Codex tool adapter already allowlists `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_ORG_ID`.
- Reusing those names avoids code changes in the adapter, launch-plan construction, and runtime env overlay logic.
- It keeps the fixture aligned with the repo’s existing Codex env-injection contract.

Alternative considered:

- Extend the adapter and launch code to support `YUNWU_OPENAI_*` names directly.
- Rejected for this change because it adds runtime-surface churn without improving the initial developer experience meaningfully.

### 3. Preserve current `auth.json` compatibility in the first implementation

The Yunwu credential profile will continue to include the local compatibility file required by the current Codex adapter (`files/auth.json`) so that brain construction and demo flows remain compatible with the existing projection contract.

Rationale:

- The builder currently fails if a required credential file mapping is missing.
- Demo and fixture flows already treat `auth.json` as required for Codex credential profiles.
- Keeping compatibility lets this change land as a fixture/config/docs addition first.

Alternative considered:

- Remove or relax the `auth.json` mapping as part of this change.
- Rejected for now because it expands the scope from profile provisioning into adapter/runtime behavior, and it would require separate validation across existing Codex flows.

### 4. Add a dedicated Yunwu-oriented recipe or equivalent documented invocation

The change will add a secret-free recipe or clearly documented explicit builder command that references the `yunwu-openai` config and credential profile names.

Rationale:

- Developers should not have to infer the right profile names from multiple directories.
- Recipes are already the repo’s preferred mechanism for named brain compositions.

Alternative considered:

- Document only the raw `build-brain` flags.
- Rejected as the sole path because it makes the new profile less discoverable and less reusable.

## Risks / Trade-offs

- [Codex may still inspect `auth.json` contents even with custom-provider login disabled] -> Validate the minimum safe local file contents before calling the fixture fully working.
- [Config/profile duplication between `config.toml` base URL and credential env `OPENAI_BASE_URL`] -> Keep both values aligned and document the env file as the local operator-controlled source for launch injection.
- [Developer confusion between `default` and `yunwu-openai`] -> Add recipe/docs examples that name both the config profile and credential profile explicitly.
- [Scope creep into adapter refactors] -> Treat any `auth.json`-optional work as follow-up unless testing proves it is required immediately.
- [Live smoke verification can fail for reasons outside the fixture wiring] -> Treat the exact-match smoke prompt check as the final acceptance gate with valid credentials and working network access, and record provider/auth failures separately from static fixture mistakes.

## Migration Plan

1. Add the new secret-free Codex config profile for `yunwu-openai`.
2. Add the local-only Codex credential profile directory for `yunwu-openai`, including `env/vars.env` guidance and the current compatibility file layout.
3. Add a recipe or explicit docs entry that binds the Yunwu-backed Codex profile into the brain-first workflow.
4. Verify that build-time projection and runtime launch guidance remain secret-free in committed artifacts.
5. Run a live Codex smoke test using the Yunwu-backed profile, submit `Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK`, and confirm the agent returns exactly `YUNWU_CODEX_SMOKE_OK` without falling back to first-party login.

## Open Questions

- What is the minimum safe `files/auth.json` content for a Codex profile that uses `requires_openai_auth = false` with a custom provider?
- Should the initial recipe live alongside the existing default recipe as a second named preset, or should the change only add docs plus explicit builder invocation?
