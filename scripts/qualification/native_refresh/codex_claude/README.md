# Codex and Claude Native Refresh Qualification

This utility tests installed native control protocols before implementing Houmao refresh adapters. It sends no user prompt or model turn. Each run creates private temporary operating-system and native homes, excludes ambient authentication and tmux variables, starts a harmless local stdio MCP fixture, and removes its temporary homes after stopping only its own children. Select both executable paths explicitly.

```bash
pixi run python scripts/qualification/native_refresh/codex_claude/probe.py \
  --codex-executable /home/huangzhe/.bun/bin/codex \
  --claude-executable /home/huangzhe/.bun/bin/claude \
  --report tmp/native-refresh/codex-claude/qualification.json
```

Replace the executable paths for another installation. The command writes a JSON report and exits nonzero if an expected control operation fails. A tool's `status: passed` means its listed probe cases completed; it does not certify complete skills, MCP, and configuration refresh or a supported Houmao transport. The JSON records limitations alongside positive evidence. Absolute temporary-home paths in that report identify homes that have already been removed.

## Executed Evidence

The probe passed on 2026-11-17 with installed `codex-cli 0.169.0` and `Claude Code 2.1.325`, on Linux aarch64. The local Codex source reference was commit `091008729d5572712ac08964a9602eb71cf31428`. No Claude source checkout exists under `extern/orphan/`; its selected installed binary and returned SDK control responses supply the executed evidence. These source and executable identities are separate; the checkout commit does not attest to the installed build.

| Tool and Resource | Executed Operation | Observed Result | Limit |
| --- | --- | --- | --- |
| Codex skill catalog | `skills/list` with `cwds` and `forceReload: true` | Added, changed-description, and removed user skills appear correctly in the same process. | Metadata rescan does not establish model-visible body activation. |
| Codex MCP declarations and server implementation | Edit `CODEX_HOME/config.toml`, call `config/mcpServer/reload`, then `mcpServerStatus/list` | Server addition, rename, removal, and tool marker `probe_v1` to `probe_v2` take effect. | The operation affects every loaded thread in the process. |
| Codex thread scope | Start two idle threads without turns, change the MCP fixture marker, then reload | Both original thread IDs return the new MCP tool marker in the same native process. | Single-agent safety requires ownership and safe admission for every affected thread. |
| Codex other configuration | Inspect native source's `mcp_config_reload_only_applies_mcp_inputs` test | The source deliberately leaves unrelated model changes unapplied by MCP reload. | This row is source evidence; the utility does not execute that Rust test or certify general configuration refresh. |
| Claude skill catalog | SDK `reload_skills` in ordinary user-settings mode | Added, changed-description, and removed user skills appear correctly in the same process. | `--bare` omits native user-skill discovery; skill body use and conversation history are untested. |
| Claude known MCP server | SDK `mcp_reconnect` with `serverName`, then `mcp_status` | The local server reconnects and reports `probe_v2` after its marker changes. | Reconnection uses the known server declaration. |
| Claude home MCP declarations | Rename a server in `CLAUDE_CONFIG_DIR/.claude.json`, call SDK `reload_plugins`, allow one second for native observation, then inspect `mcp_status` | The installed version retains the old server name; `mcp_declaration_reread` is false. | Plugin reload is insufficient for arbitrary user MCP declaration refresh in this profile. |
| Claude general configuration | No qualified general file-reread operation established | Remains unqualified. | Do not infer success from skill reload or MCP reconnect. |

Earlier disposable probes also tested an edited startup `--mcp-config` file. SDK `reload_plugins` retained the original MCP declaration there too. `mcp_set_servers` accepted an explicit new declaration, but that operation supplies replacement configuration rather than rereading the native home. The durable utility deliberately excludes it from the refresh recipe.

## Native Recipes and Houmao Availability

Codex app-server initialization requires `initialize` with client information before the refresh RPCs. Its `skills/list` result supplies catalog evidence; MCP confirmation requires inspecting the native status/tool list after reload. The local reference defines these methods in `extern/orphan/codex/codex-rs/app-server-protocol/src/protocol/common.rs`, the rescan flag in `schema/typescript/v2/SkillsListParams.ts`, and process-wide MCP behavior in `app-server/src/mcp_refresh.rs`. The latter iterates all loaded threads and applies only the MCP-related configuration inputs. A successful RPC alone is insufficient to establish every server's health or every resource's activation.

Claude accepts SDK controls through `--print --input-format stream-json --output-format stream-json --verbose`. Send a `control_request` with a unique `request_id` and a request subtype such as `initialize`, `reload_skills`, `mcp_reconnect`, or `mcp_status`. Require the matching successful `control_response` and inspect the returned catalog or connected tool marker. The tested process has no persisted conversation and sends no model turns, so this qualification does not establish conversation preservation, active-turn safety, or skill-body replacement in existing model history.

Houmao's retained `backends/codex_app_server.py` contains an old stdio transport, but `launch_plan.py` and `runtime.py` explicitly reject that backend as unmaintained. Maintained `codex_headless` and `local_interactive` do not own this RPC channel. Refresh must not revive the deprecated backend or start another app-server process to control an existing agent.

The maintained Claude headless runner starts native children with `stdin=subprocess.DEVNULL`; its stream JSON is an output format, not an owned input control channel. Claude TUI control also lacks an owned SDK stream. The native SDK capability therefore does not authorize Houmao to paste commands as model text, manufacture a second CLI process, or claim live reload support through its current maintained transport.

Headless next-invocation discovery is a separate qualification. This utility does not execute `codex exec`, a Houmao-managed prompt, or resumed Claude model work. Qualify those flows through `scripts/agents/test-fixtures/fixture.py` with an explicitly selected case and model before advertising automatic full-home discovery.
