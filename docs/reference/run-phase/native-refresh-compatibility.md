# Native Refresh Compatibility

Houmao provides active native-home inspection and common-plugin observations for skills and MCP. DSH is the primary refresh implementation. Kimi Code, Codex, and Claude Code receive best-effort support according to the native behavior and owned control paths qualified below. Pi integration remains postponed.

The gateway [refresh contract](../gateway/operations/native-refresh.md) permits native automatic updates and broader native reload effects. It provides no common inventory or freshness guarantee for native-special-plugin packages. Refresh never starts a replacement agent process or conversation; restarting the agent uses explicit relaunch.

## Managed Secondary-Tool Support

The implementation currently reports skills and MCP as `unknown` for the maintained secondary-tool modes below. Home inspection can still return the selected active runtime's authoritative native home. Missing or stopped authority fails explicitly.

| Tool and Maintained Mode | Passive Skill Evidence | Passive MCP Evidence | Managed Refresh | Qualified Automatic Boundary |
| --- | --- | --- | --- | --- |
| Kimi Code, `kimi_headless` | Unknown. | Unknown. | `unsupported`, HTTP 501. | None established for current-home changes across exact continuation. |
| Kimi Code, `local_interactive` | Unknown. | Unknown. | `unsupported`, HTTP 501. | Native watchers and manual `/reload` are not observed through an owned semantic channel. |
| Codex, `codex_headless` | Unknown. | Unknown. | `unsupported`, HTTP 501. | None established for `codex exec` continuation. |
| Codex, `local_interactive` | Unknown. | Unknown. | `unsupported`, HTTP 501. | Native TUI updates have no qualified common-state observer. |
| Claude Code, `claude_headless` | Unknown. | Unknown. | `unsupported`, HTTP 501. | None established for fresh or resumed `claude -p` work. |
| Claude Code, `local_interactive` | Unknown. | Unknown. | `unsupported`, HTTP 501. | Native TUI updates have no qualified common-state observer. |

An unknown observation returns HTTP 200. It does not assert an empty inventory, stale material, or a failed native update. Operators may update or reload these agents directly; Houmao retains unknown freshness until a qualified observer can establish the result. A refresh refusal performs no worker launch, model turn, terminal command injection, or home regeneration.

The secondary headless backends start a native worker for ordinary prompt work. That architecture alone does not establish which current-home skill catalogs, bodies, MCP declarations, or tool implementations the selected build consumes. The implementation therefore does not return an automatic success merely because the next prompt starts a worker.

## Executed Native Capability Evidence

The credential-free preflight probes ran on 2026-11-17. They sent no model turns and used isolated native homes and synthetic local MCP peers. These results qualify the listed native control surfaces, rather than a maintained Houmao transport to an existing managed agent.

| Tool and Executed Build | Native Surface | Executed Skill Evidence | Executed MCP Evidence | Scope and Limits |
| --- | --- | --- | --- | --- |
| Kimi Code 2.6.0 | Native Web server `POST /api/v1/sessions/{session_id}:reload`. | Add, metadata update, and removal appear after reload with watchers disabled. | Add, changed command/tool marker, and removal appear after reload. | Same server PID and empty-session ID. The tested `disable_feedback_survey` configuration edit also applies. Skill bodies, nonempty conversation history, TUI command delivery, and headless next-invocation discovery remain unqualified. |
| Codex CLI 0.169.0 | Native app-server `skills/list` with `forceReload: true`; `config/mcpServer/reload` and `mcpServerStatus/list`. | Add, metadata update, and removal appear after forced catalog reload. | Server add, rename, removal, and changed implementation/tool marker take effect. | Same process and original loaded thread IDs. MCP reload affects every loaded thread in that process. General configuration reload and skill-body activation remain unqualified. |
| Claude Code 2.1.325 | Bidirectional SDK stream controls `reload_skills`, `mcp_reconnect`, and `mcp_status`. | Add, metadata update, and removal appear in normal user-settings mode. | Reconnect updates the implementation/tools of an already-known server. | Same process. Bare mode omits native user skills. `reload_plugins` did not reread edited home or startup-file MCP declarations in the tested profiles. Skill bodies, nonempty history, and general configuration reload remain unqualified. |

See the [preflight report](../../../context/plans/native-agent-home-refresh/preflight.md), [Kimi probe and 12 named checks](../../../scripts/qualification/native_refresh/kimi/README.md), and [Codex/Claude probe](../../../scripts/qualification/native_refresh/codex_claude/README.md) for reproducible commands and the source/executable identities. The existing probe results do not certify every subsequently installed version.

## Maintained Control Investigation

### Kimi Code

The local reference is `extern/orphan/kimi-code` at commit `67325c1b25e46b2fc66043bceab059221b719fa9`. Its package metadata reports 2.2.0, while the executed installed server reports 2.6.0. The source is useful mechanism evidence and does not replace installed-build qualification.

The source TUI `/reload` handler (`extern/orphan/kimi-code/apps/kimi-code/src/tui/commands/reload.ts`) calls `harness.reloadSession()` for an active session and reloads runtime/TUI configuration. `/reload-tui` only reloads TUI configuration. The native server reload action (`extern/orphan/kimi-code/packages/kap-server/src/routes/sessions.ts`) rejects running turns and compaction before reloading native configuration and plugins, refreshing catalogs, and reopening the session inside the same harness process. Broad native effects are permitted by the Houmao contract.

Houmao's [Kimi headless runner](../../../src/houmao/agents/realm_controller/backends/kimi_headless.py) launches `kimi -p` and passes the managed home skill directory. The native print runner (`extern/orphan/kimi-code/apps/kimi-code/src/cli/v2/run-v2-print.ts`) supplies explicit skill directories to a fresh native bootstrap. This suggests a next-invocation discovery path. The selected installed build still needs an executed exact-continuation test for skill metadata/body and MCP add/update/remove before Houmao can advertise that automatic boundary.

Maintained Kimi TUI and prompt-mode sessions do not expose the native server endpoint used by the probe. Starting a separate server with the same home would control different native resource objects. A managed TUI reload needs qualified command delivery, busy refusal, completion evidence, and preserved process/conversation identity through the existing session.

### Codex

The local reference is `extern/orphan/codex` at commit `091008729d5572712ac08964a9602eb71cf31428`; the executed native build is CLI 0.169.0. The app-server catalog processor (`extern/orphan/codex/codex-rs/app-server/src/request_processors/catalog_processor.rs`) clears native skill/plugin caches for forced skill listing. The MCP reload implementation (`extern/orphan/codex/codex-rs/app-server/src/mcp_refresh.rs`) iterates loaded threads. Its source tests distinguish MCP inputs from unrelated model configuration.

The maintained [Codex headless runner](../../../src/houmao/agents/realm_controller/backends/codex_headless.py) runs `codex exec --json`, and the TUI uses terminal control. Neither owns the probed app-server RPC stream. Houmao retains an old `codex_app_server` module, but [launch planning](../../../src/houmao/agents/realm_controller/launch_plan.py) and [runtime construction](../../../src/houmao/agents/realm_controller/runtime.py) explicitly reject that unmaintained backend. Refresh does not reactivate it or create another app-server process to operate on an existing agent.

A future owned app-server adapter would need admission for every affected loaded thread, rather than only the addressed gateway. Qualification of `codex exec` current-home discovery remains separate from these native app-server results.

### Claude Code

No complete first-party Claude implementation checkout is available under `extern/orphan/`. The selected installed 2.1.325 binary and matching SDK control responses provide the native evidence. The probe initializes `--print --input-format stream-json --output-format stream-json --verbose`, sends uniquely identified control requests, and checks matching responses plus returned resource evidence.

The maintained [Claude headless runner](../../../src/houmao/agents/realm_controller/backends/claude_headless.py) uses stream JSON for output. Its [child process runner](../../../src/houmao/agents/realm_controller/backends/headless_runner.py) sets `stdin=subprocess.DEVNULL`, so it does not retain the bidirectional SDK input channel used by the probe. The maintained TUI also has no owned SDK stream. A second native process cannot refresh the first process's resource objects, and model prompt text cannot substitute for an SDK control request.

Known-server reconnect does not establish arbitrary MCP declaration reread. The probed `mcp_set_servers` operation accepts replacement declarations; using it internally would require qualified native parsing and precedence through an owned stream. Houmao currently has neither that qualification nor that stream. The public refresh request continues to reject replacement configuration.

## Qualification Boundaries

Positive secondary support requires an executed test against the selected maintained mode, version, native home, and exact conversation. The test must distinguish catalog metadata from later skill-body loading, and declaration application from MCP connection/tool health. It must also distinguish changed declarations from externally upgraded server implementations whose runtime revision cannot be observed.

Existing native preflight results remain positive evidence for the controls they exercised. The managed `unknown`/`unsupported` results describe Houmao's present observation and transport coverage; they do not claim that these agent bodies lack native reload facilities. DSH acceptance does not depend on filling these secondary gaps.
