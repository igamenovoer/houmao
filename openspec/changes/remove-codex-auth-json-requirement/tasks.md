## 1. Builder and adapter contract

- [x] 1.1 Extend the brain-builder credential file-mapping schema so `CredentialFileMapping` supports `required: bool = True`, `_load_tool_adapter()` parses that field, and the projection loop skips missing files only when `required: false`.
- [x] 1.2 Update the Codex tool adapter to mark `auth.json` with `required: false` instead of treating it as required, and document the new `required` field in the adapter schema docs.
- [x] 1.3 Update `src/gig_agents/agents/brain_launch_runtime/backends/codex_bootstrap.py` so `ensure_codex_home_bootstrap()` accepts the effective runtime env, follows the existing Claude bootstrap pattern, and refuses launch when neither a non-empty `auth.json` object nor `OPENAI_API_KEY` is available.

## 2. Tests and fixture guidance

- [x] 2.1 Add builder-level tests for the new `required` mapping contract: missing required credential files still fail, missing `required: false` files are skipped, and optional files are still projected when present.
- [x] 2.2 Add Codex runtime tests for launch validation: env-only launch succeeds, populated `auth.json` without `OPENAI_API_KEY` succeeds, empty `{}` `auth.json` without `OPENAI_API_KEY` fails, and launch still fails when both auth paths are absent.
- [x] 2.3 Remove the empty-`auth.json` requirement from the Codex/Yunwu fixture docs and local credential guidance, and update the earlier `add-codex-yunwu-agent` change spec so env-backed Yunwu profiles no longer require `files/auth.json` while still allowing valid login-state files as an alternative.

## 3. Verification

- [x] 3.1 Rebuild the Yunwu-backed Codex brain without `auth.json` present and confirm the build succeeds and the manifest remains secret-free.
- [x] 3.2 Launch Codex with the env-only Yunwu-backed profile, submit `Respond with exactly this text and nothing else: YUNWU_CODEX_SMOKE_OK`, and verify that the agent returns exactly `YUNWU_CODEX_SMOKE_OK`.
