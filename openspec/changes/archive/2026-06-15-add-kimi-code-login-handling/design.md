## Context

`houmao-credential-mgr` currently supports Kimi credential CRUD and import through `--api-key`, `--config-toml`, `--credential-json`, and `--code-home`, but the packaged skill tells agents that Kimi has no maintained Houmao login helper. That statement is accurate for the `houmao-mgr project credentials kimi login` surface, which does not exist, but it leaves agents without a safe workflow when the user wants to use Kimi Code's own login command and then import the resulting Kimi Code home into Houmao.

The local installed Kimi Code CLI and source checkout are both version `0.14.3`. The CLI exposes `kimi login` as an OAuth device-code flow with no flags. The source uses `KIMI_CODE_HOME` as the data root, writes managed OAuth tokens under `<KIMI_CODE_HOME>/credentials/`, and provisions `config.toml` through the same auth facade used by the TUI. The default production token path resolves to `credentials/kimi-code.json`, which is the file Houmao already imports from `--code-home`.

## Goals / Non-Goals

**Goals:**

- Add Kimi-specific login-handling guidance for agents who need to obtain a fresh Kimi Code OAuth credential and import it into Houmao storage.
- Keep the workflow operator-visible by running `kimi login` inside tmux and carrying proxy variables into the tmux session.
- Use an isolated temporary `KIMI_CODE_HOME` so the agent does not mutate the operator's default Kimi Code home.
- Import successful default Kimi Code OAuth output through existing `credentials kimi add|set --code-home <dir>` surfaces.
- Preserve the current distinction between a Kimi login-handling subskill and a maintained Houmao Kimi credential login helper.

**Non-Goals:**

- Add `houmao-mgr project credentials kimi login` or `houmao-mgr internals native-agent credentials kimi login`.
- Add new credential bundle file formats.
- Teach Houmao to import every possible Kimi scoped OAuth credential filename in this change.
- Automate user browser authorization, API-key entry, or arbitrary Kimi TUI `/login` interactions headlessly.

## Decisions

1. Add a Kimi-specific subskill instead of extending the maintained helper list.

   The new guidance should live as a local page, for example `subskills/kimi-code-login-handling.md`, and the top-level skill should route Kimi login requests there. The page can explicitly say that it is a lower-level Kimi Code login/import workflow. This avoids claiming that `credentials kimi login` exists while still helping users complete a real Kimi Code OAuth login.

   Alternative considered: add Kimi to `actions/login.md` as another maintained helper. That would blur the command contract because Claude, Codex, and Gemini login are owned by Houmao helper commands, while Kimi would require the agent to create a Kimi home and call `kimi login` directly.

2. Run `kimi login` inside tmux with an isolated `KIMI_CODE_HOME`.

   Kimi login prints the verification URL and user code to stderr, attempts a browser open, and waits for the browser-side authorization to complete. A tmux session gives the operator and agent an attachable surface for that URL/code, and an isolated `KIMI_CODE_HOME` keeps the flow from touching `~/.kimi-code`.

   Alternative considered: instruct agents to run `kimi login` directly. That is simpler, but it has the same interaction problem the previous credential-login change addressed for other providers.

3. Preserve proxy variables through tmux, not through Kimi auth env inheritance.

   The Kimi login session should pass set `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and lowercase variants with tmux `-e` arguments. This mirrors the credential login helper guidance and avoids printing proxy values. Kimi-specific auth variables such as `KIMI_CODE_BASE_URL` and `KIMI_CODE_OAUTH_HOST` are credential-routing inputs, not ordinary proxy inputs, and should only be included when the user explicitly asks for a non-default Kimi Code environment.

   Alternative considered: inherit the full shell environment. That can accidentally couple the login to unrelated or stale Kimi model env values.

4. Import default Kimi Code OAuth output with `--code-home`.

   After a successful default login, the subskill should verify that `<temp-home>/credentials/kimi-code.json` exists and then import the whole temp home with `credentials kimi add --code-home <temp-home>` or `credentials kimi set --code-home <temp-home>`. If `config.toml` exists, the subskill should preserve it through the same import so the managed Kimi provider and default model travel together.

   Alternative considered: import only `--credential-json`. That can work for token-only state, but it may drop the provisioned managed provider configuration that Kimi writes after OAuth login.

5. State the scoped-OAuth limitation explicitly.

   Kimi can derive scoped token names for non-default `KIMI_CODE_OAUTH_HOST` or `KIMI_CODE_BASE_URL`. Current Houmao import uses `credentials/kimi-code.json`, so the first subskill should guide the default production OAuth path and avoid promising support for every scoped environment. If scoped environments become required, a later change can add CLI import support for those credential filenames.

## Risks / Trade-offs

- Kimi login may fail to reach the OAuth host behind a proxy -> the subskill carries current proxy env vars into tmux and tells agents not to print their values.
- Tmux may be unavailable -> the subskill should ask before falling back to a direct foreground run or another terminal-sharing path.
- A failed Kimi login leaves a temp home with partial state -> the subskill should preserve and report the temp home path for recovery instead of deleting it.
- Scoped Kimi OAuth environments may not import through current `--code-home` behavior -> the subskill should limit its default claim to `credentials/kimi-code.json` and call out non-default endpoint support as outside this change.

## Migration Plan

This is a packaged-skill artifact change. Update the skill Markdown and tests that assert Kimi credential-manager guidance. Rollback is a revert of the skill-text and test changes because no stored credentials, CLI commands, or bundle formats change.
