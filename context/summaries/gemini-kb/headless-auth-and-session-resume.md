# Gemini CLI Headless Auth and Session Resume for Houmao

## Question

What is essential to know about `gemini-cli` so Houmao can run Gemini reliably for headless, resumable, and unattended-style workflows?

## Short Answer

- Gemini CLI uses `GEMINI_CLI_HOME` as the home root override, and its global state lives under `${GEMINI_CLI_HOME}/.gemini`.
- For OAuth-backed Gemini CLI `0.36.0`, projecting `oauth_creds.json` by itself is not enough for non-interactive runs. Headless mode also requires an auth method selection, either via a minimal `.gemini/settings.json` or via an auth-selecting environment variable.
- The lowest-risk Houmao-friendly auth setup is:
  - project `oauth_creds.json` to `.gemini/oauth_creds.json`
  - either project a minimal `.gemini/settings.json` with `security.auth.selectedType: oauth-personal`
  - or export `GOOGLE_GENAI_USE_GCA=true`
- `google_accounts.json` is not the primary credential. It is account metadata/cache state, not the OAuth token store.
- Headless invocation works with `gemini -p ... -o stream-json`.
- The `stream-json` protocol emits an initial `init` event with `session_id`.
- Gemini can resume by full UUID using `--resume <session_id>`, even though `gemini --help` only advertises `latest` and numeric index. Houmao should preserve and use the UUID it already persists.
- Resume is project-scoped. The same working directory must be used for the resumed turn.

## Empirical Probe

Probe environment:

- installed CLI version: `gemini 0.36.0`
- upstream source checkout: `extern/orphan/gemini-cli`
- upstream commit inspected: `84936dc`
- probe root: `/data1/huangzhe/code/houmao/tmp/gemini-headless-check`

Observed live behavior:

1. A fresh temp Gemini home with only `oauth_creds.json` failed in headless mode.
   Error artifact:
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn1.stderr`

   The relevant error was:

   ```text
   Please set an Auth method in your .../.gemini/settings.json or specify one of the following environment variables before running: GEMINI_API_KEY, GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_GENAI_USE_GCA
   ```

2. Adding a minimal `.gemini/settings.json` with `security.auth.selectedType = oauth-personal` made headless mode succeed.
   Success artifacts:
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/home/.gemini/settings.json`
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn1.stream.jsonl`

3. A separate fresh temp home also succeeded without `settings.json` when run with `GOOGLE_GENAI_USE_GCA=true`.
   Success artifacts:
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/env-auth-select.stream.jsonl`
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/env-auth-select.stderr`

4. The first successful headless turn emitted a `stream-json` `init` event with a UUID `session_id`:

   ```json
   {"type":"init","session_id":"8887b2c9-94fa-4657-a090-a0b0b3c254c5","model":"auto-gemini-3",...}
   ```

5. Resume by full UUID worked:
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn2-resume-uuid.stream.jsonl`

6. Resume by `latest` also worked when run serially in the same workspace:
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn4-resume-latest-serial.stream.jsonl`

7. Sessions were saved under the project-scoped chat store:
   `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/home/.gemini/tmp/workspace/chats/session-2026-04-02T04-22-8887b2c9.json`

8. In this Linux environment, missing `libsecret` did not block execution. Gemini printed a fallback notice and used file-backed secure storage instead:

   ```text
   Keychain initialization encountered an error: libsecret-1.so.0: cannot open shared object file: No such file or directory
   Using FileKeychain fallback for secure storage.
   ```

## Credential Preparation Rule

For Houmao-managed Gemini OAuth runs, treat the following as distinct pieces:

- Required credential file: `oauth_creds.json`
- Optional account metadata file: `google_accounts.json`
- Required auth-type selection for headless OAuth runs:
  - either minimal `settings.json`
  - or `GOOGLE_GENAI_USE_GCA=true`

Minimal settings file that was sufficient in the live probe:

```json
{
  "security": {
    "auth": {
      "selectedType": "oauth-personal"
    }
  }
}
```

Important caution:

- Do not blindly project the user’s full `~/.gemini/settings.json` into Houmao runtime homes.
- A real user settings file can contain unrelated MCP server configuration, local preferences, and secrets.
- Houmao should generate or project a minimal settings file only for the fields Gemini actually needs at runtime.

## Headless Invocation Contract

Recommended headless start shape:

```bash
env GEMINI_CLI_HOME=<home-root> \
  gemini -p '<prompt>' -o stream-json
```

Recommended resumed turn shape:

```bash
env GEMINI_CLI_HOME=<home-root> \
  gemini --resume <session_id> -p '<prompt>' -o stream-json
```

Important runtime facts:

- `-p` is the explicit non-interactive mode.
- `stream-json` is the best machine-readable format for Houmao.
- The first `init` event carries `session_id`.
- The JSON protocol uses `session_id` in output, while the saved chat file uses `sessionId`.
- Resume is project-scoped, not globally scoped across arbitrary directories.
- `gemini --list-sessions` only lists sessions for the current project/workspace.

## Session Continuation Rule

For Houmao, the correct continuation contract should be:

1. Start the first headless turn with `gemini -p ... -o stream-json`.
2. Capture `session_id` from the `init` event.
3. Persist that UUID in the session manifest.
4. Send later turns with `--resume <session_id>`.
5. Reuse the same working directory/project root on resumed turns.

Using `--resume latest` is operationally weaker than using the explicit UUID because:

- it depends on the current project’s most recent session rather than the exact logical session
- it can attach to the wrong thread if multiple Gemini runs happen in the same project
- it loses the precision that Houmao’s manifest already aims to preserve

## What This Means for Unattended Launch in Houmao

The current Houmao Gemini adapter is not quite sufficient for unattended OAuth-backed headless startup on current Gemini CLI:

- current adapter:
  `src/houmao/project/assets/starter_agents/tools/gemini/adapter.yaml`
- current adapter projects only `oauth_creds.json`
- current adapter does not project `settings.json`
- current adapter allowlists:
  - `GOOGLE_API_KEY`
  - `GEMINI_API_KEY`
  - `GOOGLE_GENAI_USE_VERTEXAI`
- current adapter does not allow `GOOGLE_GENAI_USE_GCA`

That means a freshly constructed Houmao Gemini home can still fail headless auth selection even when the OAuth token file exists.

For a maintained unattended lane, Houmao should choose one explicit policy:

- Policy A: generate a minimal `.gemini/settings.json` with `security.auth.selectedType: oauth-personal`
- Policy B: allow and inject `GOOGLE_GENAI_USE_GCA=true` for Gemini OAuth runs

Policy A is more self-contained because it keeps auth-type selection inside the runtime home. Policy B is simpler if the team prefers env-only control.

## What This Means for Resume in Houmao

Houmao’s spec already wants the stronger contract:

- `openspec/specs/brain-launch-runtime/spec.md`

The spec says Gemini follow-up turns should use `--resume <session_id>`.

Current implementation still uses:

- `src/houmao/agents/realm_controller/backends/gemini_headless.py`

which currently returns `["--resume", "latest"]`.

Houmao runtime already enforces two assumptions that are compatible with upstream Gemini:

- the persisted manifest must contain non-empty `headless.session_id` after turn 0
- Gemini resume must use the same working directory as the persisted session

Those checks live in:

- `src/houmao/agents/realm_controller/runtime.py`

So the remaining gap is mainly backend command construction, not overall manifest design.

## Recommended Houmao Changes

1. Keep projecting `oauth_creds.json`.
2. Consider projecting `google_accounts.json` as optional metadata, but do not treat it as the primary credential.
3. Add one supported auth-type selection path for Gemini OAuth runtimes:
   - minimal generated `settings.json`, or
   - `GOOGLE_GENAI_USE_GCA` in the adapter env allowlist
4. Change Gemini headless resume from `--resume latest` to `--resume <persisted_session_id>`.
5. Keep the same-working-directory resume guard.
6. Keep parsing `session_id` from `stream-json` `init`.

## Source References

Upstream source and docs:

- `extern/orphan/gemini-cli/packages/core/src/utils/paths.ts`
- `extern/orphan/gemini-cli/packages/core/src/config/storage.ts`
- `extern/orphan/gemini-cli/packages/core/src/core/contentGenerator.ts`
- `extern/orphan/gemini-cli/packages/cli/src/validateNonInterActiveAuth.ts`
- `extern/orphan/gemini-cli/packages/cli/src/nonInteractiveCli.ts`
- `extern/orphan/gemini-cli/packages/cli/src/utils/sessionUtils.ts`
- `extern/orphan/gemini-cli/packages/core/src/output/types.ts`
- `extern/orphan/gemini-cli/docs/cli/session-management.md`

Houmao files:

- `src/houmao/project/assets/starter_agents/tools/gemini/adapter.yaml`
- `src/houmao/agents/realm_controller/backends/gemini_headless.py`
- `src/houmao/agents/realm_controller/runtime.py`
- `openspec/specs/brain-launch-runtime/spec.md`

Live probe artifacts:

- `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn1.stderr`
- `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn1.stream.jsonl`
- `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn2-resume-uuid.stream.jsonl`
- `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/turn4-resume-latest-serial.stream.jsonl`
- `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/artifacts/env-auth-select.stream.jsonl`
- `/data1/huangzhe/code/houmao/tmp/gemini-headless-check/home/.gemini/tmp/workspace/chats/session-2026-04-02T04-22-8887b2c9.json`
