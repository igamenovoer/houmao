# Credential Routing

Use this page when a request mentions credentials, auth, API keys, vendor login files, env vars, or credential discovery.

## Boundaries

- `specialists` and the specialist-create step inside `create-agent-fast-forward` may create or import one credential bundle as part of `project easy specialist create`.
- Specialist patching may change which existing credential display name the specialist references.
- `profiles` and `raw-profiles` authoring may store an `--auth` override by display name.
- Credential bundle CRUD, secret mutation, auth-file edits, login flows, and credential rename belong to `houmao-credential-mgr`.

## Specialist Creation Modes

Use discovery only when creating a specialist, including the specialist-create step inside `create-agent-fast-forward`.

- Explicit Auth Mode: use user-provided auth values or files.
- Env Lookup Mode: inspect only env names or explicit patterns the user named.
- Directory Scan Mode: scan only the user-provided directory.
- Auto Credentials Mode: only when the user explicitly says `auto credentials`.
- No Discovery Mode: do not scan; reuse only a confirmed existing credential bundle, otherwise ask for auth input.

## Tool References

Load only the selected tool's page:

- Claude lookup: [../../references/credentials/claude-lookup.md](../../references/credentials/claude-lookup.md)
- Codex lookup: [../../references/credentials/codex-lookup.md](../../references/credentials/codex-lookup.md)
- Gemini lookup: [../../references/credentials/gemini-lookup.md](../../references/credentials/gemini-lookup.md)
- Claude kinds menu: [../../references/credentials/claude-kinds.md](../../references/credentials/claude-kinds.md)
- Codex kinds menu: [../../references/credentials/codex-kinds.md](../../references/credentials/codex-kinds.md)
- Gemini kinds menu: [../../references/credentials/gemini-kinds.md](../../references/credentials/gemini-kinds.md)

## Guardrails

- Do not scan env vars, directories, repo-local tool homes, home-dir tool configs, or redirected tool homes unless a supported discovery mode is explicitly active.
- Do not execute browser login flows, `codex login`, `claude auth login`, `gemini` interactive login, `apiKeyHelper`, or other auth-generation flows.
- Do not infer auth identity from `.houmao/content/auth/...` or `.houmao/agents/tools/<tool>/auth/...` directory basenames.
- Do not treat profile `--auth` changes as credential-bundle content mutation.
