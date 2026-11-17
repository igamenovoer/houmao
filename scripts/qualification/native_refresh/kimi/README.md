# Kimi Native Refresh Qualification

This development utility tests the installed Kimi native server's reload operation before a Houmao adapter claims support. It uses an explicit self-hosted fixture, a synthetic API key, an unreachable loopback model endpoint, and an isolated native home. The probe submits no model prompts, invokes no tools, and uses no tmux server. Default cleanup removes the temporary home after stopping only its own server process.

Run from the repository root:

```sh
pixi run python scripts/qualification/native_refresh/kimi/probe.py \
  --executable /home/huangzhe/.local/bin/kimi \
  --report tmp/native-refresh/kimi/report.json
```

Select the intended installed binary explicitly. `--fixture-script` and `--source-checkout` accept alternative local reference paths. `--scratch-parent` controls where private temporary state is created. `--keep-scratch` retains that state for debugging; native startup logs stay there and are not copied into the public report. The utility does not depend on existing scratch state, credentials, or package installation.

The launcher calls the supported fixture utility with these selections before starting the native server:

```text
fixture.py prepare --client kimi --case self-hosted
  --model native-refresh-probe --context-window 8192
  --base-url http://127.0.0.1:1/v1 --env-file <private synthetic env file>
  --surface raw --mode headless --run-root <private scratch root>
  --executable <explicit selected binary>
```

It starts `kimi web --no-open --host 127.0.0.1 --port <private free port> --dangerous-bypass-auth --log-level silent`. Authentication bypass applies only to this ephemeral loopback test instance. The child environment contains the selected fixture values and a separate operating-system home, with no ambient provider credentials. Native watchers are disabled through `KIMI_CODE_WATCH=false` and `[watch] enabled=false`, so explicit reload can be distinguished from automatic discovery.

## Executed Evidence

The 2026-11-17 run passed all 12 named checks against installed Kimi **2.6.0**, executable SHA-256 `c85652e2dc2a9f64ee78ba4f174dd7546048201fe61cda780dd4ae4d617089d2`. The local source reference is commit `67325c1b25e46b2fc66043bceab059221b719fa9`, whose CLI package declares **2.2.0**. Source and installed package versions differ; the installed observations below come from executed requests.

| Resource | External Edit | Observation After Native Reload |
| --- | --- | --- |
| Skills | Add a skill and edit another skill's description. | The existing catalog stays stale before reload; both changes appear after reload. |
| Skills | Remove the original skill. | The removed skill disappears and the added skill remains. |
| MCP | Add a stdio server exposing `probe_one`. | The server connects and the native tool catalog contains `mcp__refresh-probe__probe_one`. |
| MCP | Change that server's command arguments to expose `probe_two`. | The tool catalog changes to `mcp__refresh-probe__probe_two`. |
| MCP | Remove the server declaration. | Its tool disappears. |
| Configuration | Set `disable_feedback_survey` from `false` to `true` in `config.toml`. | The resolved value stays stale before reload and becomes `true` after reload. |
| Identity | Repeat the above operations on one empty native session. | The server process stays alive with the same PID, and the session retains the same ID. |

The native reload recipe is:

1. Complete external edits to the selected native home.
2. Address the already-running native server that owns the selected session.
3. Send `POST /api/v1/sessions/{session_id}:reload` with `{}`.
4. Confirm the native response, resource catalogs, and preserved process/session identity.

The probe records only synthetic resource names and safe version, hash, identity, and check results. `mcp_server.py` supplies the deterministic MCP peer; its initialization and tool-list responses require no network or provider access.

## Existing Houmao Control Limitations

This result qualifies the native server REST surface. Houmao's existing Kimi backends launch headless workers or a local interactive TUI; they do not supply a bound native server endpoint for the same running TUI. Starting another native server with the same home does not refresh the resource objects owned by the original TUI and would not satisfy the refresh contract.

The local source's [reload handler](../../../../extern/orphan/kimi-code/apps/kimi-code/src/tui/commands/reload.ts) calls `harness.reloadSession()` for an active session, then reloads runtime and TUI configuration. Its `/reload-tui` handler only applies TUI configuration. The [native server reload route](../../../../extern/orphan/kimi-code/packages/kap-server/src/routes/sessions.ts) checks running turns and compaction before reloading configuration/plugins/catalogs and closing/resuming the session inside the same harness process. These are source observations, not installed TUI transport qualification.

No TUI command delivery/completion matcher, active-turn refusal, headless next-invocation discovery, automatic watchers, skill-body consumption, or nonempty conversation history was exercised. Only the named configuration field was tested. A maintained Houmao profile must keep unsupported coverage explicit until its actual control path and version are qualified. Native process restart remains outside refresh and belongs to explicit relaunch.
