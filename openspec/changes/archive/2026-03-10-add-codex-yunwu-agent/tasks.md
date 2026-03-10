## 1. Codex profile assets

- [x] 1.1 Add a secret-free Codex config profile under `tests/fixtures/agents/brains/cli-configs/codex/yunwu-openai/` that selects provider `yunwu-openai` and configures the custom provider with `env_key = "OPENAI_API_KEY"`, `requires_openai_auth = false`, and `wire_api = "responses"`.
- [x] 1.2 Add a Yunwu-oriented Codex brain recipe or equivalent repo-owned build guidance that references the `yunwu-openai` config and credential profile names without embedding secrets.

## 2. Local credential profile

- [x] 2.1 Create the local-only credential profile layout at `tests/fixtures/agents/brains/api-creds/codex/yunwu-openai/` with `env/vars.env` guidance that uses `OPENAI_API_KEY` and `OPENAI_BASE_URL`.
- [x] 2.2 Validate the minimum `files/auth.json` compatibility artifact required by the current Codex adapter and add the local-only file layout or documentation needed to keep brain construction working.

## 3. Docs and verification

- [x] 3.1 Update the relevant brain fixture and Codex setup docs to explain the `yunwu-openai` profile workflow, the required env var names, the current `auth.json` compatibility constraint, and the final live smoke-test procedure.
- [x] 3.2 Run a targeted build verification for the Yunwu-backed Codex profile and confirm that the resulting committed config, recipe, and manifest artifacts remain secret-free.
- [x] 3.3 Launch a Codex CLI instance using the Yunwu-backed profile and valid local credentials, submit `Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK`, and verify that the agent returns exactly `YUNWU_CODEX_SMOKE_OK`.
