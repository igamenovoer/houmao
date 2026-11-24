/** Confine approved MCP connections to the selected native Agent's scope. */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const NAME = /^[A-Za-z0-9_-]{1,32}$/;
const MAX_DECLARATIONS = 16;

export function managedMcpAdapter(ctx, config, fail) {
  let api;
  const native = name => import(pathToFileURL(
    createRequire(process.argv[1]).resolve(`@deepseek-ai/${name}`),
  ).href);
  const load = () => api ??= Promise.all([native('dsh-mcp-client'), native('dsh-scope')]);

  const requireScope = (state, agent) => {
    if (state.scope.scopeOf(state.ctx) !== agent || !ctx.get('tools')) {
      fail('unsupported_operation', 'Managed MCP requires the exact native Agent scope');
    }
  };

  const ready = (state, agent, revision) => {
    requireScope(state, agent);
    if (state.effective !== revision) return false;
    const names = ctx.get('tools').schemas(agent).map(tool => tool.name);
    for (const [name, child] of state.children) {
      if (state.scope.scopeOf(child.handle.ctx) !== agent) return false;
      const status = child.status.current();
      if (status.state !== 'connected'
        || names.filter(tool => tool.startsWith(`mcp__${name}__`)).length !== status.toolCount) return false;
    }
    return true;
  };

  return {
    async register(agentCtx, agent, preset, revision) {
      if (!config) return undefined;
      const [client, scope] = await load();
      if (scope.scopeOf(agentCtx) !== agent || typeof client.connectionStatusOf !== 'function'
        || !ctx.get('tools')) return undefined;
      return { ctx: agentCtx, client, scope, preset, revision, children: new Map(), declared: [], effective: null };
    },

    preflight(state, agent, directory, signal) {
      signal.throwIfAborted();
      requireScope(state, agent);
      const declared = new Map();
      const entries = [];
      const names = ctx.get('tools').schemas(agent).map(tool => tool.name);
      const globalServers = ctx.get('mcpManager')?.list().map(entry => entry.name) ?? [];
      const files = readdirSync(directory, { withFileTypes: true });
      if (files.length > MAX_DECLARATIONS) fail('invalid_request', 'Managed MCP declaration limit exceeded');
      for (const file of files) {
        const name = file.name.slice(0, -5);
        const path = join(directory, file.name);
        if (!file.isFile() || !file.name.endsWith('.json') || !NAME.test(name) || statSync(path).size > 4096) {
          fail('invalid_request', 'Invalid managed MCP declaration file');
        }
        let data;
        try { data = JSON.parse(readFileSync(path, 'utf8')); }
        catch { fail('invalid_request', 'Malformed managed MCP declaration'); }
        if (!data || typeof data !== 'object' || Array.isArray(data)
          || Object.keys(data).some(key => key !== 'connector' && key !== 'enabled')
          || typeof data.connector !== 'string' || !NAME.test(data.connector)
          || !Object.hasOwn(config.connectors, data.connector)
          || (Object.hasOwn(data, 'enabled') && typeof data.enabled !== 'boolean')) {
          fail('invalid_request', 'Managed MCP requires an owner-approved connector and optional enabled flag');
        }
        entries.push({ name, enabled: data.enabled !== false });
        if (data.enabled === false) continue;
        if (globalServers.includes(name) || (!state.children.has(name)
          && names.some(tool => tool.startsWith(`mcp__${name}__`)))) {
          fail('conflict', 'Managed MCP would shadow an existing native server');
        }
        const connector = config.connectors[data.connector];
        declared.set(name, { id: data.connector, native: {
          transport: 'streamable-http', serverName: name,
          url: connector.url, headers: connector.headers, expandTemplates: true,
          failOnStartupError: true, startupTimeoutMs: 5000, closeTimeoutMs: 2000,
        } });
      }
      return { declarations: entries, connections: declared };
    },

    async activate(state, agent, plan, revision, signal) {
      requireScope(state, agent);
      const declared = plan.connections;
      // Dispose changed entries before starting replacements with the same namespace.
      state.effective = null;
      state.declared = plan.declarations;
      const closing = [];
      for (const [name, child] of state.children) {
        if (declared.get(name)?.id !== child.id) {
          closing.push((async () => {
            await child.handle.dispose();
            const result = child.status.closure();
            if (!result.closeConfirmed || result.cleanupError) {
              fail('unavailable', 'Native managed MCP connection closure could not be verified');
            }
            state.children.delete(name);
          })());
        }
      }
      if ((await Promise.allSettled(closing)).some(result => result.status === 'rejected')) {
        fail('unavailable', 'Native managed MCP connection cleanup was incomplete');
      }
      signal.throwIfAborted();
      const starting = [];
      for (const [name, entry] of declared) {
        if (!state.children.has(name)) {
          starting.push((async () => {
            const handle = state.ctx.plugin(state.client, entry.native);
            try {
              await handle.await();
              const status = state.client.connectionStatusOf(handle);
              if (!status || state.scope.scopeOf(handle.ctx) !== agent) {
                fail('unsupported_operation', 'Native MCP connection escaped the selected scope');
              }
              state.children.set(name, { id: entry.id, handle, status });
            } catch {
              await handle.dispose();
              fail('unavailable', 'Native managed MCP connection could not be prepared');
            }
          })());
        }
      }
      if ((await Promise.allSettled(starting)).some(result => result.status === 'rejected')) {
        fail('unavailable', 'Native managed MCP activation was incomplete');
      }
      signal.throwIfAborted();
      state.effective = revision;
      if (!ready(state, agent, revision)) {
        state.effective = null;
        fail('unavailable', 'Native managed MCP tool generation could not be verified');
      }
    },

    ready,
    observe(state, agent, revision) {
      return {
        current: ready(state, agent, revision),
        declarations: state.declared,
        instances: [...state.children].map(([name, child]) => ({name, health: child.status.current().state})),
      };
    },
  };
}
