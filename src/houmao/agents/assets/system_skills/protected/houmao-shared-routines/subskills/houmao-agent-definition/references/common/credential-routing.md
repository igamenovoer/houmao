# Credential Routing

Use this page when a request mentions credentials, auth, API keys, vendor login files, env vars, or credential discovery.

## Boundaries

- `specialists` and the specialist-create step inside `create-agent-fast-forward` may create or import one credential bundle as part of `project specialist create`.
- Specialist patching may change which existing credential display name the specialist references.
- `profiles` and `launch-dossiers` authoring may store an `--auth` override by display name.
- Credential bundle CRUD, secret mutation, auth-file edits, login flows, and credential rename belong to `<public-entrypoint>->houmao-shared-routines->credential-mgr`.

## Specialist Creation Modes

Use discovery only when creating a specialist, including the specialist-create step inside `create-agent-fast-forward`.

- Resolve the specialist tool and credential from the prompt or nearby explicit context when present.
- If tool or credential is omitted, run Specialist Create Defaulting before any credential discovery.
- Explicit Auth Mode: use user-provided auth values or files.
- Env Lookup Mode: inspect only env names or explicit patterns the user named.
- Directory Scan Mode: scan only the user-provided directory.
- Auto Credentials Mode: use only when the user explicitly requests auto credentials.
- No Discovery Mode: do not scan; reuse only a confirmed existing credential bundle, otherwise ask for auth input.

## Specialist Create Defaulting

Use this only for specialist creation when the user omitted tool or credential inputs.

1. Resolve the Houmao credential target:
   - prefer the active Houmao project overlay;
   - otherwise use `HOUMAO_NATIVE_AGENT_ROOT` when it points at a plain agent-definition directory;
   - stop if neither target is available.
2. Inventory registered credentials across supported tool lanes by running the selected `houmao-mgr` launcher for each supported tool:
   - project target: `<chosen houmao-mgr launcher> project [--project-dir <dir>] credentials <tool> list`;
   - native-agent target: `<chosen houmao-mgr launcher> internals native-agent credentials <tool> list --native-agent-root <path>`.
3. Stop if no credentials are registered.
4. If the prompt or nearby explicit context names a registered tool or credential, use the matching registered credential.
5. Otherwise choose the credential with the latest listed update time across all registered tools and use its tool lane plus credential name.

Use the `credential_records[].updated_at_utc` field from `houmao-mgr ... credentials <tool> list`. For project credentials this is the project catalog timestamp; for native-agent credentials this is best-effort filesystem metadata.

Failure reports must include a direct suggestion:

- no target: initialize/select a Houmao project, set `HOUMAO_PROJECT_OVERLAY_DIR`, or set `HOUMAO_NATIVE_AGENT_ROOT`;
- no registered credentials: add or login one credential through `<public-entrypoint>->houmao-shared-routines->credential-mgr`.

## Tool References

Load only the selected tool's credential-kind page:

- Claude: [../../../houmao-credential-mgr/references/claude-credential-kinds.md](../../../houmao-credential-mgr/references/claude-credential-kinds.md)
- Codex: [../../../houmao-credential-mgr/references/codex-credential-kinds.md](../../../houmao-credential-mgr/references/codex-credential-kinds.md)
- Kimi: [../../../houmao-credential-mgr/references/kimi-credential-kinds.md](../../../houmao-credential-mgr/references/kimi-credential-kinds.md)

## Guardrails

- Do not scan env vars, directories, repo-local tool homes, home-dir tool configs, or redirected tool homes unless a supported discovery mode is active.
- Do not infer specialist tool from installed CLIs, project language, file names, or vendor tool homes.
- Do not execute browser login flows, `codex login`, `claude auth login`, `apiKeyHelper`, or other auth-generation flows.
- Do not infer auth identity from `.houmao/content/auth/...` or `.houmao/agents/tools/<tool>/auth/...` directory basenames.
- Do not treat profile `--auth` changes as credential-bundle content mutation.
