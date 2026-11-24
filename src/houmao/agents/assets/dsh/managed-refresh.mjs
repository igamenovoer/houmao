/** Native common-resource evidence and bounded refresh inside one owned Web host. */
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

/** Owned local Linux processes share the OS monotonic clock across transports. */
const monotonicNow = () => Number(process.hrtime.bigint()) / 1000000;

/** Compare configuration privately, without exposing credential-derived fingerprints. */
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}

/** Equality of detached native configuration values stays inside the owning process. */
function equal(left, right) { return JSON.stringify(canonical(left)) === JSON.stringify(canonical(right)); }

/** Detect native expressions without evaluating caller-authored code during a read. */
function expression(value) {
  if (!value || typeof value !== 'object') return false;
  return Object.hasOwn(value, '__jsExpr') || Object.values(value).some(expression);
}

/** Retain only public skill discovery metadata, never instruction bodies. */
function summary(value) {
  return Object.fromEntries(['name', 'description', 'whenToUse', 'invocation', 'source', 'provider', 'path', 'resourceBase'].filter(key => value[key] !== undefined).map(key => [key, value[key]]));
}

/** Build a resource observation with an explicit native boundary and coverage. */
function resource(kind, component, freshness, boundary, inventory, reason, complete = true) {
  return {kind, component, freshness, boundary, inventory, reason, complete, supported: true, health: 'available', evidence: [reason]};
}

/** Flatten ordinary groups; unmodelled includes or expressions make coverage incomplete. */
function flattened(rows, output = [], parentDisabled = false) {
  let complete = true;
  for (const row of rows) {
    const common = row.id === 'skill-filesystem' || row.id === 'mcp-manager' || String(row.name).includes('dsh-skill-filesystem') || String(row.name).includes('dsh-mcp-manager');
    if (common && (expression(row.disabled) || expression(row.name) || expression(row.group))) complete = false;
    const disabled = parentDisabled || row.disabled === true;
    if (row.group === true || row.name === 'cordis:group') {
      if (!Array.isArray(row.config)) { complete = false; continue; }
      complete = flattened(row.config, output, disabled).complete && complete;
    } else {
      if (row.name === 'cordis:include' || row.name?.includes('plugin-include')) complete = false;
      output.push({...row, disabled});
    }
  }
  return {rows: output, complete};
}

/** Create native observation/control without starting a body or changing configuration. */
export function createCommonRefresh(ctx, callbacks) {
  let imports;
  let operation;
  const connected = new Map();
  const liveFibers = new Set();
  const nativeRequire = createRequire(process.argv[1]);
  const resolveVersion = () => {
    if (typeof callbacks.nativeVersion === 'string' && callbacks.nativeVersion) return callbacks.nativeVersion;
    try {
      return JSON.parse(readFileSync(nativeRequire.resolve('@deepseek-ai/dsh/package.json'), 'utf8')).version ?? null;
    } catch {
      return null;
    }
  };
  const native = name => import(pathToFileURL(nativeRequire.resolve(`@deepseek-ai/${name}`)).href);
  const api = () => imports ??= Promise.all([native('dsh-app-boot'), native('cordis-plugin-include'), native('dsh-skill-filesystem'), native('dsh-scope'), native('cordis'), native('dsh-skill-office'), native('dsh-tool-skill')]);
  ctx.on('internal/plugin', fiber => { if (fiber.uid === null) liveFibers.delete(fiber); else liveFibers.add(fiber); }, {global: true});

  // Native Agent creation awaits this serial hook before initialization can
  // release queued work. Reject only the competing activation, not watchers.
  ctx.on('agent/created', ({agent}) => {
    if (operation && !operation.settled && agent !== operation.agent) callbacks.fail('busy', 'Native refresh owns shared resource admission');
  }, {global: true});

  // A connected event follows native negotiation/tool registration for the current
  // manager instance. Capture its selected declaration, not just a timestamp.
  ctx.on('mcp-manager/status', async (name, status) => {
    const [, , , , cordis] = await api();
    const manager = ctx.get('mcpManager');
    if (status.state !== 'connected' || !manager?.config?.servers) { connected.delete(name); return; }
    const declaration = manager.config.servers.get()[name];
    if (declaration) connected.set(name, {manager: manager[cordis.symbols.original] ?? manager, declaration: structuredClone(declaration), status});
  }, {global: true});

  /** Read the effective on-disk profile using native patch semantics, without apply. */
  const source = async () => {
    const [boot, include] = await api();
    const profile = ctx.get('profileContext');
    if (!profile) throw new Error('profile_unavailable');
    const patch = boot.readProfilePatches('dsh', profile);
    const filename = join(profile.dir, 'cordis.yml');
    const yaml = nativeRequire('js-yaml');
    const base = existsSync(filename) ? yaml.load(readFileSync(filename, 'utf8'), {schema: include.entryListSchema}) : [];
    if (!Array.isArray(base)) throw new Error('profile_unavailable');
    const rows = include.applyEntryPatches(base, structuredClone(patch), () => {});
    return {...flattened(rows), patch, profile};
  };

  /** Inspect all filesystem providers visible to this exact agent without invalidating them. */
  const skills = async (agent, desired, deadline) => {
    const registry = ctx.get('skills');
    if (!registry) return [resource('skills', 'catalog', 'unknown', 'next_step', [], 'native_registry_unavailable', false)];
    const [, , filesystem, scopes, cordis, office, skillTool] = await api();
    const callback = entry => entry.fiber?.runtime?.callback?.[cordis.symbols.original] ?? entry.fiber?.runtime?.callback;
    const chain = scopes.scopeChainOf(agent).reverse();
    const loaded = [...ctx.loader.entries()];
    const entries = [...(ctx.registry.get(filesystem)?.fibers ?? [])].filter(fiber => fiber.uid !== null && fiber.effectiveConfig !== undefined).map(fiber => loaded.find(entry => entry.fiber?.uid === fiber.uid) ?? {fiber, options: {name: '@deepseek-ai/dsh-skill-filesystem', config: fiber.config}});
    const visible = entries.filter(entry => { const scope = scopes.scopeOf(entry.fiber.ctx); return scope === undefined || chain.includes(scope); });
    const current = await registry.snapshot({cwd: callbacks.cwd, scope: agent, signal: deadline});
    const names = new Set();
    const expected = new Map();
    let complete = current.complete && (desired?.complete ?? true);
    // Unknown consumers can also register an empty cached provider. Include
    // their declared skill dependency in coverage even with no winning names.
    const known = [filesystem.apply, office.apply, skillTool.apply];
    for (const fiber of new Set([...liveFibers, ...loaded.flatMap(entry => entry.fiber ? [entry.fiber] : [])])) {
      if (fiber.uid === null || !Object.hasOwn(fiber.inject ?? {}, 'skills')) continue;
      const scope = scopes.scopeOf(fiber.ctx);
      if (scope !== undefined && !chain.includes(scope)) continue;
      if (callbacks.skillMount?.managesFiber(agent, fiber)) continue;
      const callback = fiber.runtime?.callback?.[cordis.symbols.original] ?? fiber.runtime?.callback;
      if (!known.includes(callback)) complete = false;
    }
    let configPending = false;
    const missing = desired?.rows.filter(row => !row.disabled && String(row.name).includes('dsh-skill-filesystem') && !visible.some(entry => entry.options.id === row.id)) ?? [];
    const providers = [...visible.map(entry => {
      const global = scopes.scopeOf(entry.fiber.ctx) === undefined;
      const replacement = entry.options.id && global ? desired?.rows.find(row => row.id === entry.options.id) : undefined;
      return {entry, replacement, removed: desired !== undefined && entry.options.id && global && !replacement};
    }), ...missing.map(replacement => ({entry: undefined, replacement, removed: false}))];
    for (const [order, {entry, replacement, removed}] of providers.entries()) {
      const scope = entry ? scopes.scopeOf(entry.fiber.ctx) : undefined;
      const level = scope === undefined ? 0 : chain.indexOf(scope) + 1;
      let raw = replacement?.config ?? entry?.options.config ?? {};
      // A standing preset keeps its mounted configuration. Read the public
      // resolved value without evaluating author expressions in an observer.
      if (entry && (!desired || scope !== undefined) && expression(raw)) raw = entry.fiber.effectiveConfig;
      if (expression(raw)) { complete = false; continue; }
      const config = filesystem.Config(raw);
      const abort = new AbortController();
      const provider = new filesystem.FileSystemSkillProvider(entry?.fiber.ctx ?? ctx, {signal: abort.signal, invalidate() {}}, {...config, watch: false});
      names.add(provider.name);
      try {
        if (removed || replacement?.disabled) { configPending = true; continue; }
        if (replacement && (!entry || replacement.name !== entry.options.name || !equal(replacement.config ?? {}, entry.options.config ?? {}))) configPending = true;
        const observation = await provider.list({cwd: callbacks.cwd, signal: deadline});
        const candidates = Array.isArray(observation) ? observation : observation.candidates;
        if (!Array.isArray(observation) && !observation.complete) complete = false;
        for (const candidate of candidates) {
          const old = expected.get(candidate.name);
          if (!old || level > old.level || (level === old.level && (candidate.rank < old.rank || (candidate.rank === old.rank && order < old.order)))) {
            expected.set(candidate.name, {...summary(candidate), rank: candidate.rank, level, order});
          }
        }
      } finally { abort.abort(); await provider.dispose(); }
    }
    // The installed Office provider is another qualified disk-backed reader.
    // Capture its pure provider registration outside the live registry so reads
    // compare current assets without invalidating the runtime's cached catalog.
    const officeEntries = [...ctx.loader.entries()].filter(entry => callback(entry) === office.apply && (scopes.scopeOf(entry.fiber.ctx) === undefined || chain.includes(scopes.scopeOf(entry.fiber.ctx))));
    if (desired?.rows.some(row => !row.disabled && String(row.name).includes('dsh-skill-office') && !officeEntries.some(entry => entry.options.id === row.id))) complete = false;
    for (const entry of officeEntries) {
      const global = scopes.scopeOf(entry.fiber.ctx) === undefined;
      const replacement = global ? desired?.rows.find(row => row.id === entry.options.id) : undefined;
      let raw = replacement?.config ?? entry.options.config ?? {};
      if ((!desired || !global) && expression(raw)) raw = entry.fiber.effectiveConfig;
      // The selected rc.3 profile expression depends only on fixed profile
      // identity and process environment. Other expressions remain unknown.
      if (raw.pythonEnvironment?.__jsExpr === "ctx.get('profileContext')?.name === 'desktop' && process.env.DSH_PRIMARY_RUNTIME ? 'workspace-dependencies' : 'user'") raw = {...raw, pythonEnvironment: entry.fiber.effectiveConfig.pythonEnvironment};
      if (expression(raw)) { complete = false; continue; }
      let factory;
      office.apply({skills: {registerProvider(value) { factory = value; }}, logger: {warn() {}}}, office.Config(raw));
      if (!factory) { complete = false; continue; }
      const provider = factory({signal: deadline, invalidate() {}});
      names.add(provider.name);
      if ((desired && global && !replacement) || replacement?.disabled) { configPending = true; continue; }
      if (replacement && (replacement.name !== entry.options.name || !equal(replacement.config ?? {}, entry.options.config ?? {}))) configPending = true;
      const observation = await provider.list({cwd: callbacks.cwd, signal: deadline});
      if (!observation.complete) complete = false;
      for (const candidate of observation.candidates) {
        if (expected.has(candidate.name)) complete = false;
        else expected.set(candidate.name, summary(candidate));
      }
    }
    const managed = await callbacks.skillMount?.observeCandidates(agent, deadline);
    if (managed) {
      names.add(callbacks.skillMount.providerName);
      complete &&= managed.complete;
      for (const candidate of managed.entries) {
        if (expected.has(candidate.name)) complete = false;
        expected.set(candidate.name, summary(candidate));
      }
    }
    // An opaque provider's cached contributions do not prove current inputs.
    // Retain its inventory while explicitly withholding complete coverage.
    for (const value of current.skills) {
      if (!names.has(value.provider)) {
        complete = false;
        if (expected.has(value.name)) complete = false;
        else expected.set(value.name, summary(value));
      }
    }
    const expectedRows = [...expected.values()].map(summary).sort((a, b) => a.name.localeCompare(b.name));
    const actualRows = current.skills.map(summary).sort((a, b) => a.name.localeCompare(b.name));
    const same = equal(expectedRows, actualRows);
    const freshness = !same || configPending ? 'pending' : complete ? 'current' : 'unknown';
    const inventory = actualRows.map(({name, provider, source, path}) => ({name, provider, source, ...(path ? {path} : {})}));
    return [resource('skills', 'catalog', freshness, 'next_step', inventory, freshness === 'current' ? 'source_and_native_catalog_match' : freshness === 'pending' ? 'catalog_or_provider_configuration_differs' : 'incomplete_provider_coverage', complete), resource('skills', 'body', configPending ? 'pending' : complete ? 'current' : 'unknown', 'next_load', inventory, 'qualified_native_bodies_read_on_load', complete)];
  };

  /** Compare declarations and bound connection/tool evidence without reconnecting. */
  const mcp = async (agent, desired) => {
    const [, , , , cordis] = await api();
    const manager = ctx.get('mcpManager');
    const tools = ctx.get('tools');
    if (!manager || !tools) return [resource('mcp', 'declarations', 'unknown', 'now', [], 'native_manager_unavailable', false)];
    const row = desired.rows.find(value => value.id === 'mcp-manager' || String(value.name).includes('dsh-mcp-manager'));
    if (!row || expression(row)) return [resource('mcp', 'declarations', 'unknown', 'now', [], 'effective_manager_configuration_unavailable', false)];
    const selected = row.disabled ? {} : manager.constructor.Config(row.config ?? {}).servers.get();
    const actual = manager.config.servers.get();
    const states = manager.list();
    const commonTools = tools.schemas(agent).map(tool => tool.name).filter(name => name.startsWith('mcp__'));
    const declarations = Object.keys(selected).map(name => ({name, enabled: selected[name].enabled !== false}));
    const declarationFreshness = equal(selected, actual) ? 'current' : 'pending';
    let toolsFreshness = declarationFreshness;
    let complete = desired.complete;
    const inventory = [];
    for (const state of states) {
      const declaration = selected[state.name];
      const names = commonTools.filter(name => name.startsWith(`mcp__${state.name}__`));
      inventory.push({name: state.name, configured: state.configured, health: state.status.state, tools: names});
      if (!declaration) {
        if (state.configured) { complete = false; toolsFreshness = 'unknown'; }
        else if (names.length) toolsFreshness = 'pending';
        continue;
      }
      if (!declaration.enabled) { if (names.length) toolsFreshness = 'pending'; continue; }
      const proof = connected.get(state.name);
      if (!proof || proof.manager !== (manager[cordis.symbols.original] ?? manager) || !equal(proof.declaration, declaration) || !equal(proof.status, state.status)) {
        if (toolsFreshness !== 'pending') toolsFreshness = state.status.state === 'connecting' || state.status.state === 'reconnecting' ? 'pending' : 'unknown';
      } else if (state.status.toolCount !== names.length) toolsFreshness = 'pending';
    }
    for (const [name, declaration] of Object.entries(selected)) {
      if (declaration.enabled && !states.some(state => state.name === name)) toolsFreshness = 'pending';
    }
    const managed = callbacks.mcpMount?.observeMcp(agent);
    if (managed) {
      declarations.push(...managed.declarations);
      for (const {name, health} of managed.instances) {
        inventory.push({name, configured: true, health,
          tools: commonTools.filter(tool => tool.startsWith(`mcp__${name}__`))});
      }
      if (!managed.current && toolsFreshness === 'current') toolsFreshness = 'unknown';
    }
    const implementation = declarations.some(value => value.enabled) ? 'unknown' : 'current';
    const health = inventory.some(value => ['failed', 'waiting-credentials'].includes(value.health)) ? 'degraded' : inventory.some(value => ['connecting', 'reconnecting'].includes(value.health)) ? 'connecting' : 'available';
    return [resource('mcp', 'declarations', declarationFreshness, 'now', declarations, 'effective_native_declaration_comparison', complete), {...resource('mcp', 'tools', toolsFreshness, 'next_step', inventory, toolsFreshness === 'current' ? 'native_connection_generation_and_tools_confirmed' : 'connection_generation_or_tools_unverified', complete), health}, {...resource('mcp', 'implementation', implementation, 'now', [], implementation === 'current' ? 'no_enabled_external_implementation' : 'server_implementation_revision_not_exposed'), required: false}];
  };

  /** Observe current source/runtime evidence without forcing native refresh. */
  const observe = async (agent, timeoutSeconds = 10) => {
    const captured = callbacks.identity(agent);
    const signal = AbortSignal.timeout(Math.max(1, Math.min(300000, Math.ceil(timeoutSeconds * 1000))));
    let resources;
    try {
      const before = await source();
      resources = [...await skills(agent, before, signal), ...await mcp(agent, before)];
      const after = await source();
      if (!equal(before.rows, after.rows) || !equal(captured, callbacks.identity(agent))) {
        resources = resources.map(value => ({...value, freshness: 'unknown', complete: false, reason: 'observation_superseded'}));
      }
    } catch {
      resources = ['skills', 'mcp'].map(kind => resource(kind, kind === 'skills' ? 'catalog' : 'declarations', 'unknown', 'now', [], 'native_observation_unavailable', false));
    }
    const required = resources.filter(value => value.required !== false);
    if (resources.length) resources[0].evidence = [...resources[0].evidence, 'refresh_configuration_and_resources_only', 'hot_code_hmr_not_supported'];
    const complete = required.every(value => value.complete);
    const freshness = required.some(value => value.freshness === 'pending') ? 'pending' : complete && required.every(value => value.freshness === 'current') ? 'current' : 'unknown';
    return {schema_version: 1, protocol_version: 1, identity: captured, observed_at_utc: new Date().toISOString(), native_version: resolveVersion(), profile: 'web', coverage_complete: complete, freshness, resources, native_reload: true, native_settled: !operation || operation.settled, native_ready: callbacks.live() && (!operation || operation.ready), effects: operation?.effects ?? 'absent'};
  };

  /** Refuse a new managed mutation after the original operation deadline. */
  const checkDeadline = request => {
    if (!Number.isFinite(request.deadline_monotonic_ms)) callbacks.fail('invalid_request', 'Native refresh requires an absolute deadline');
    if (monotonicNow() >= request.deadline_monotonic_ms) callbacks.fail('expired', 'Native refresh deadline elapsed');
  };

  /** Claim the original deadline together with native identity and readiness. */
  const admit = (agent, expected, callerSignal, peer) => {
    callbacks.authenticate(expected, callerSignal, peer);
    callbacks.requireIdentity(expected.identity);
    checkDeadline(expected);
    if (callbacks.pendingInteractions(agent).length || callbacks.pendingInbox(agent).hasPending) callbacks.fail('busy', 'Native input or interaction is pending');
    const agents = ctx.agents.list();
    if (agents.some(value => value !== agent)) callbacks.fail('busy', 'Other native execution shares refresh resources');
  };

  /** Lifecycle/control edits belong to explicit relaunch, never resource refresh. */
  const lifecycleChanged = async desired => {
    const [, , , scopes] = await api();
    for (const entry of ctx.loader.entries()) {
      if (!entry.fiber || scopes.scopeOf(entry.fiber.ctx) !== undefined) continue;
      const name = String(entry.options.name);
      if (entry.options.id !== 'houmao-managed-web' && !/dsh-(agent|agent-loop|session|session-persistence|connection|web-server)(?:\/|$)/.test(name)) continue;
      const replacement = desired.rows.find(row => row.id === entry.options.id);
      if (!replacement || replacement.disabled || replacement.name !== entry.options.name || !equal(replacement.config ?? {}, entry.options.config ?? {})) return true;
    }
    return false;
  };

  /** Refresh resources once; native maintenance remains held across timeout/failure. */
  const refresh = async (agent, request, callerSignal, peer) => {
    const budget = request.timeout_seconds ?? 30;
    if (!Number.isFinite(budget) || budget <= 0 || budget > 300) callbacks.fail('invalid_request', 'Refresh timeout must be between zero and 300 seconds');
    checkDeadline(request);
    request = {...request, deadline_monotonic_ms: Math.min(request.deadline_monotonic_ms, monotonicNow() + budget * 1000)};
    const remaining = () => Math.max(0.001, (request.deadline_monotonic_ms - monotonicNow()) / 1000);
    if (operation && (!operation.settled || !operation.ready)) return {outcome: operation.settled ? 'failed' : 'busy', effects: operation.effects, native_settled: operation.settled, native_ready: false, observation: await observe(agent)};
    const before = await observe(agent, remaining());
    checkDeadline(request);
    if (before.freshness === 'current') return {outcome: 'already_current', method: 'noop', effects: 'absent', native_settled: true, native_ready: true, observation: before};
    let entered = false;
    let completeResponse;
    const response = new Promise(resolve => { completeResponse = resolve; });
    let boot;
    try { [boot] = await api(); }
    catch { return {outcome: 'unsupported', method: 'none', effects: 'absent', native_settled: true, native_ready: true, observation: before}; }
    const state = {agent, settled: false, ready: false, effects: 'absent'};
    operation = state;
    try {
      const work = agent.runMaintenance(async maintenanceSignal => {
        entered = true;
        try { admit(agent, request, callerSignal, peer); }
        catch (error) {
          state.ready = true;
          return {outcome: error.code === 'stale_identity' ? 'unavailable' : 'busy', effects: 'absent', native_ready: true, observation: before};
        }
        try {
          const desired = await source();
          callbacks.requireIdentity(request.identity);
          if (await lifecycleChanged(desired)) {
            state.ready = true;
            return {outcome: 'restart_required', method: 'none', effects: 'absent', native_ready: true, observation: before, diagnostics: [{reason: 'native_lifecycle_configuration_changed'}]};
          }
          callbacks.authenticate(request, callerSignal, peer);
          callbacks.requireIdentity(request.identity);
          if (callbacks.pendingInteractions(agent).length || callbacks.pendingInbox(agent).hasPending || ctx.agents.list().some(value => value !== agent)) {
            state.ready = true;
            return {outcome: 'busy', method: 'none', effects: 'absent', native_ready: true, observation: before};
          }
          const reconcile = async () => {
            const hmr = ctx.get('hmr');
            const apply = async () => {
              admit(agent, request, callerSignal, peer);
              state.effects = 'unknown';
              return {warnings: await boot.reconcileProfilePatches(ctx.root, desired.patch, 'dsh'), pending: []};
            };
            // Share native serialization without asking its code-replacement
            // planner to stop lifecycle providers that own the live Agent.
            if (!hmr) return apply();
            let claimed = false;
            let abandoned = false;
            const work = hmr.runExclusive(() => {
              if (abandoned) throw new Error('abandoned_native_refresh_claim');
              claimed = true;
              return apply();
            });
            // The qualified serializer enters through an already-settled
            // Promise when idle. Never leave a mutation waiting behind HMR.
            await Promise.resolve();
            if (!claimed) {
              abandoned = true;
              void work.catch(() => {});
              return {busy: true};
            }
            return work;
          };
          const nativeResult = await reconcile();
          if (nativeResult.busy) {
            state.ready = true;
            return {outcome: 'busy', method: 'none', effects: 'absent', native_ready: true, observation: before};
          }
          // Reload every visible filesystem provider, not the agent or its session.
          const [, , filesystem, scopes, , office] = await api();
          const chain = scopes.scopeChainOf(agent);
          const fibers = [...(ctx.registry.get(filesystem)?.fibers ?? []), ...(ctx.registry.get(office)?.fibers ?? [])];
          for (const fiber of fibers) {
            if (fiber.uid === null || fiber.effectiveConfig === undefined) continue;
            const scope = scopes.scopeOf(fiber.ctx);
            if (scope !== undefined && !chain.includes(scope)) continue;
            checkDeadline(request);
            callbacks.requireIdentity(request.identity);
            await fiber.restart();
          }
          await ctx.loader.await();
          // A declaration may be unchanged after its server package was edited.
          // Explicit refresh renews known MCP instances; passive queries never do.
          const manager = ctx.get('mcpManager');
          for (const view of manager?.list() ?? []) {
            if (view.configured && view.status.state !== 'disabled') {
              checkDeadline(request);
              callbacks.requireIdentity(request.identity);
              await manager.restart(view.name);
            }
          }
          let observation = await observe(agent, remaining());
          while (observation.resources.some(value => value.kind === 'mcp' && value.component === 'tools' && value.freshness === 'pending') && monotonicNow() < request.deadline_monotonic_ms) {
            await new Promise(resolve => setTimeout(resolve, 20));
            observation = await observe(agent, remaining());
          }
          callbacks.requireIdentity(request.identity);
          state.ready = callbacks.live() && await callbacks.ready(agent);
          if (!state.ready) throw new Error('native_readiness_unavailable');
          state.effects = 'confirmed';
          const diagnostics = [...(nativeResult.pending ?? []).map(value => ({reason: value.reason ?? 'native_module_pending'})), ...(nativeResult.warnings ?? []).map(() => ({reason: 'native_activation_warning'})), ...(nativeResult.restartReason ? [{reason: nativeResult.restartReason}] : [])];
          return {outcome: observation.freshness === 'current' ? 'refreshed' : 'partial', method: 'native_reload', effects: 'confirmed', native_ready: state.ready, observation, diagnostics};
        } catch (error) {
          if (state.effects === 'absent' && error.managed) {
            state.ready = true;
            return {outcome: 'busy', method: 'none', effects: 'absent', native_ready: true, observation: before};
          }
          state.effects = state.effects === 'absent' ? 'absent' : 'partial';
          try { callbacks.requireIdentity(request.identity); state.ready = await callbacks.ready(agent); } catch { state.ready = false; }
          const observation = await observe(agent, remaining());
          const result = {outcome: state.ready && observation.freshness === 'current' ? 'refreshed' : 'failed', method: 'native_reload', effects: state.effects, native_outcome: 'failed', native_settled: false, native_ready: state.ready, observation, diagnostics: [{reason: error.code === 'expired' ? 'native_refresh_deadline_elapsed' : 'native_activation_failed'}]};
          if (state.ready) return result;
          completeResponse(result);
          // Native runMaintenance wakes inbox work in finally. Keep that guard
          // until explicit disposal instead of releasing potentially broken work.
          await new Promise(resolve => {
            const disposed = () => { if (maintenanceSignal.reason?.kind === 'disposed') resolve(); };
            maintenanceSignal.addEventListener('abort', disposed);
            disposed();
          });
        }
      });
      void work.then(result => {
        state.settled = true;
        if (state.ready) operation = undefined;
        if (result) completeResponse({...result, native_settled: true, observation: {...result.observation, native_settled: true, native_ready: state.ready, effects: state.effects}});
      }).catch(() => {
        state.settled = true;
        if (!entered) { operation = undefined; completeResponse({outcome: 'busy', effects: 'absent', native_settled: true, native_ready: true, observation: before}); }
        else completeResponse({outcome: 'failed', effects: state.effects, native_settled: true, native_ready: false, observation: before});
      });
    } catch (error) {
      if (!entered) { operation = undefined; return {outcome: 'busy', effects: 'absent', native_settled: true, native_ready: true, observation: before}; }
      throw error;
    }
    let timer;
    try {
      return await Promise.race([response, new Promise(resolve => { timer = setTimeout(() => resolve({outcome: 'outcome_unknown', method: 'native_reload', effects: state.effects, native_settled: state.settled, native_ready: state.ready, observation: before}), Math.max(0, request.deadline_monotonic_ms - monotonicNow())); })]);
    } finally { clearTimeout(timer); }
  };

  /** Confirm that invalidation will not apply unrelated changes from live providers. */
  const checkSkillScope = async (agent, signal) => {
    const [catalog] = await skills(agent, undefined, signal);
    return catalog.complete && catalog.freshness === 'current';
  };

  return {observe, refresh, checkSkillScope};
}
