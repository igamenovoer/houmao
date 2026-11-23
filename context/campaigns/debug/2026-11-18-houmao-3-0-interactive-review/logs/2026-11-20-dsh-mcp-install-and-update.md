# DSH MCP Dynamic Install and Update

Date: 2026-11-20. Status: `semantic-scholar-mcp` 0.4.0 installed and updated on the live uv-installed DSH Web agent through native refresh. Dynamic refresh initially returned `busy` because DSH retained multiple live Agents from browser sessions; a host relaunch with exact session preservation cleared them, after which install and update both returned `refreshed` with `method=native_reload` and `effects=confirmed`.

Context: [debug-intent.md](../debug-intent.md), [Iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md), [skill install and refresh log](2026-11-20-dsh-skill-install-and-refresh.md).

## Target

- Run: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9`
- Agent: `49f2ba49-e7be-4463-bdbf-a788f4ff9596`
- Backend: `dsh_web`, native session `session-c22df0f3-5c06-4362-bab0-897fc205c0c0`
- Gateway: `http://127.0.0.1:36205`, healthy, detached process, connected
- Browser origin after relaunch: `http://127.0.0.1:39119`
- Toolchain: uv-installed `houmao-mgr 3.0.0rc3` on Python 3.13.18

The relaunch used `--chat-session-mode exact --chat-session-id session-c22df0f3-5c06-4362-bab0-897fc205c0c0`, so the native session and conversation were preserved. The browser origin changed from `46039` to `39119`; the private sign-in URL file in the run directory was updated.

## Package and Command

The server is [`semantic-scholar-mcp`](https://pypi.org/project/semantic-scholar-mcp/) 0.4.0. Its documented command is:

```bash
uvx semantic-scholar-mcp
```

That command currently fails because the package declares `mcp[cli]>=1.12.3` without an upper bound; uv resolves mcp 2.x, where `FastMCP` was renamed:

```text
ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer ...
```

The working command pins mcp v1:

```bash
uvx --with 'mcp<2' semantic-scholar-mcp
```

The server exposes 24 tools under the `mcp__semantic-scholar__*` namespace and does not require an API key for the free tier.

## Live Configuration

The DSH Web build in this run has no MCP settings page under Settings or Plugins, so the supported external-update path was the profile user patch plus Houmao refresh. A later direct-DSH test used the Settings remote instead; see **Native DSH Settings Path (Tavily)** below.

File: `$H/profiles/web/cordis.patch.yml`, where `$H` is the run's native home.

```yaml
- id: mcp-manager
  config:
    servers:
      semantic-scholar:
        transport: stdio
        command: /home/huangzhe/.local/bin/uvx
        args: ["--with", "mcp<2", "semantic-scholar-mcp"]
        enabled: true
```

The absolute `uvx` path avoids depending on the DSH host's PATH. The manager config is mounted as the `mcp-manager` row from the DSH Web app composition.

## First Refresh Attempt: Busy

`refresh --check` correctly reported the pending declaration:

```text
freshness: pending
declarations -> pending, inventory ["semantic-scholar"]
tools        -> pending, inventory []
```

`refresh --timeout-seconds 120` returned:

```text
outcome = busy
method = native_reload
effects = absent
```

The managed refresh code refuses when native admission sees more than the selected Agent. `session/list` showed four sessions, all with `agentAvailable: true`:

- `session-c22df0f3-5c06-4362-bab0-897fc205c0c0` (managed)
- `session-c00dd3f8-b042-4af5-af5b-9cf878336fb8` (blank browser session)
- `session-79c87a78-1281-49ca-93c3-942573c2a007` (blank browser session)
- `session-bf286872-b14c-4cbb-b352-6011099190f2` (`hi` browser session)

Archiving the browser sessions through `workspace/archiveSession` with `stopActivity: true` succeeded but did not dispose their Agents; `agentAvailable` remained true for the archived sessions. Every Web tab, including a blank New Session, creates a live Agent that blocks native refresh.

## Clean Host and Successful Install

The MCP entry was removed, the agent was relaunched with exact session preservation, and the entry was re-added. The relaunch returned `success: true` with detail `Relaunched the owned native Web Host`; the gateway stayed healthy and the native session id was unchanged.

With only the managed Agent live, refresh succeeded:

```text
refresh --check: freshness=pending
refresh:         outcome=refreshed, method=native_reload, effects=confirmed
```

The resulting MCP observation was complete and current:

```text
declarations -> current, inventory ["semantic-scholar"]
tools        -> current, inventory ["semantic-scholar"]
```

The agent was prompted:

```text
Use the semantic-scholar MCP server to search Semantic Scholar for "transformer architectures".
Return only the top 3 paper titles and their years.
```

It called:

```json
{"name":"mcp__semantic-scholar__search_papers","arguments":{"query":"transformer architectures","limit":3,"fields":["title","year"]}}
```

The tool returned real results, and the agent answered with the top 3 titles and years. The MCP server process was:

```text
607485  uvx --with mcp<2 semantic-scholar-mcp
607498  .../bin/semantic-scholar-mcp
```

## Dynamic Update

The live config was updated to pin the package version:

```yaml
args: ["--with", "mcp<2", "semantic-scholar-mcp==0.4.0"]
```

`refresh --check` returned `pending` for both declarations and tools. `refresh` then returned:

```text
outcome = refreshed
method = native_reload
effects = confirmed
diagnostics = []
```

The manager rebuilt the instance; the process changed to:

```text
612306  uvx --with mcp<2 semantic-scholar-mcp==0.4.0
612318  .../bin/semantic-scholar-mcp
```

The next agent prompt searched for `graph neural networks` and returned the top 2 titles and years through the same `mcp__semantic-scholar__search_papers` tool. A final `refresh --check` returned `freshness: current`, `coverage_complete: true`, with `semantic-scholar` current in both declarations and tools.

## Native DSH Settings Path (Tavily)

A second MCP server was added without Houmao refresh, using DSH's own authenticated Settings remote. The Web UI still had no MCP form, but the Settings API was live.

- `credentials/set` stored `TAVILY_API_KEY` in DSH's credential provider. The value came from `~/.tavily/config.json` and is not recorded.
- `settings/mutate` on namespace `mcp-manager`, revision 1 to 2, added `servers.tavily` with `npx -y tavily-mcp@latest` and `TAVILY_API_KEY=${credential:TAVILY_API_KEY}`.
- The manager reconciled live without a host restart. The new process was `npm exec tavily-mcp@latest` / `node .../tavily-mcp` (PIDs `651461`, `651534`, and `651535`, started 12:32:00).
- The agent's tool catalog gained `mcp__tavily__tavily_search`, `_extract`, `_map`, `_crawl`, and `_research`.
- A prompt called `mcp__tavily__tavily_search` with `{"query":"Houmao 3.0 release","max_results":3}` and returned three results.

This path did not run any Houmao refresh and therefore did not hit the multi-Agent `busy` admission. DSH's Settings remote is the native dynamic-add path; the profile patch plus Houmao refresh is an alternative application path, not a requirement.

## Toolbox UI Install and Migration

`dsh-toolbox-ui` 1.13.2 was installed from npm with a pinned version into the run's web profile. The package added itself to `profiles/web/package.json` bundles and `node_modules`; the profile files were backed up under `/tmp/dsh-toolbox-backup` first. pnpm was not on PATH, so a temporary `/tmp/pnpm-bin/pnpm` shim forwarded to `npx -y pnpm@10`.

```bash
D=tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9
H="$D/workdir/.houmao/runtime/homes/dsh-brain-20261120-030332Z-fae160"
PATH=/tmp/pnpm-bin:$PATH DSH_HOME="$PWD/$H" \
  tmp/dsh/npm-runtime/node_modules/.bin/dsh plugin --profile web add dsh-toolbox-ui@1.13.2
```

The Toolbox entry appeared in the sidebar and as a floating button, with MCP, Skills, Tools, and Context tabs. The host was relaunched with `--chat-session-mode exact` and the managed native session id, so the session was preserved. The browser origin became `http://127.0.0.1:40673`, and `sign-in-url.txt` was regenerated from `browser-connection.json`.

The MCP tab initially showed `0 servers` because the plugin manages its own `@deepseek-ai/dsh-mcp-client` entries, while the existing servers were in the built-in `mcp-manager`. Its import dialog reads Claude Code, Codex, or pasted `mcpServers` JSON, not the built-in manager.

Migration steps:

- The built-in `mcp-manager` entries were disabled through the DSH Settings API, which stopped their processes.
- Both servers were imported through the Toolbox **Import MCP** flow with **Merge (update by name)**. The pasted JSON used this shape, with the Tavily key kept out of the log:

  ```json
  {
    "mcpServers": {
      "tavily": {
        "command": "/home/huangzhe/.local/bin/npx",
        "args": ["-y", "tavily-mcp@latest"],
        "env": {"TAVILY_API_KEY": "<from ~/.tavily/config.json; not recorded>"}
      },
      "semantic-scholar": {
        "command": "/home/huangzhe/.local/bin/uvx",
        "args": ["--with", "mcp<2", "semantic-scholar-mcp==0.4.0"]
      }
    }
  }
  ```

- The profile patch now contains `mcp-tavily` and `mcp-semantic-scholar` client rows; the built-in manager entries remain configured with `enabled: false`.
- `cordis.patch.yml` is mode `0600`. The plugin masks the Tavily key in its UI; the key now lives in the plugin-managed entry instead of the DSH credential provider.

Verification:

- Toolbox showed `2 servers · 2 enabled`: `tavily` with 5 tools and `semantic-scholar` with 33 tools.
- The agent still called `mcp__tavily__tavily_search` and `mcp__semantic-scholar__search_papers` successfully after the migration.
- The GUI **Disable** action changed the list to `2 servers · 1 enabled`, showed `Disabled` in the details pane, disconnected Semantic Scholar, and stopped its process. **Enable** returned it to `2 servers · 2 enabled`, showed `Connected`, started a new `semantic-scholar-mcp` process pair (PIDs `799610`/`799624` at 12:58:02), and the next agent prompt called `mcp__semantic-scholar__search_papers` successfully.

Side effect: the relaunch activated the existing `agent-preset-registry` patch entry with `selectedDefault: cordis`, so new sessions default to **Creator mode** instead of **Standard mode**. The managed session remains on its original preset.

## Findings

- Plain `uvx semantic-scholar-mcp` fails against mcp 2.x; the package needs an upper bound or the caller must add `--with 'mcp<2'`. This is an upstream packaging issue.
- The DSH Web build exposes no MCP settings page. The profile user patch plus Houmao refresh is the working external-update path.
- Community MCP UI plugins commonly manage `@deepseek-ai/dsh-mcp-client` rows rather than the built-in `mcp-manager`. `dsh-toolbox-ui` does not display servers configured only in `mcp-manager`; migrating them changes where the Tavily key is stored.
- `dsh-toolbox-ui` works after migration: it lists both servers and their tool counts and its enable/disable actions control the live clients. The built-in `mcp-manager` entries must stay disabled to avoid duplicate tool registration.
- The relaunch activated the existing `agent-preset-registry` entry with `selectedDefault: cordis`, changing the new-session default to Creator mode. Restore `standard` if that was not intended.
- Native refresh is refused as `busy` whenever DSH has more than one live Agent. Browser sessions, blank New Session tabs, and archived sessions all remain `agentAvailable: true`; archiving does not dispose them. This makes refresh unusable after the Web UI has ever opened another session.
- On a clean host, refresh performs a real native reload, mounts the new MCP server, and reports current declarations and tools.
- Updating the MCP config rebuilds only that instance. The process PID changed, the conversation was preserved, and the agent could use the updated server on the next prompt.
- The MCP `implementation` component remains `unknown` by design; the protocol does not expose the remote server implementation revision. Declarations and tools were current.
- The exact-session relaunch preserved the native conversation but changed the browser origin. The old Web link became invalid.

## Next Steps

- File a product issue for refresh admission: inactive, blank, or archived DSH sessions should not block a native refresh intended for one managed Agent.
- Consider an upstream report for `semantic-scholar-mcp`'s unbounded `mcp` dependency.
- Test MCP disable, removal, and restart through refresh on a clean host.
- Decide whether the MCP entry belongs in durable launch-profile material or remains a runtime profile-patch update for this campaign.

## Reproduction Commands

```bash
export HOUMAO_GLOBAL_REGISTRY_DIR=$PWD/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9/registry
export HOUMAO_GLOBAL_RUNTIME_DIR=$PWD/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9/workdir/.houmao/runtime
export HOUMAO_PROJECT_OVERLAY_DIR=$PWD/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9/workdir/.houmao

houmao-mgr --print-json agents single --agent-id 49f2ba49-e7be-4463-bdbf-a788f4ff9596 refresh --check
houmao-mgr --print-json agents single --agent-id 49f2ba49-e7be-4463-bdbf-a788f4ff9596 refresh --timeout-seconds 120
```
