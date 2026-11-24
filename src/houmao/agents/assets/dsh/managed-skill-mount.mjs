/** Scoped, immutable versioned skill discovery and owner-only native publication. */
import { randomUUID } from 'node:crypto';
import { closeSync, constants, fstatSync, fsyncSync, lstatSync, openSync, readFileSync, readdirSync, realpathSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const PROVIDER = 'houmao-versioned-skills';
const REVISION = /^[a-f0-9]{40}$/;
const MOUNT = /^[a-f0-9]{32}$/;
const SKILL = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const OPERATION = /^[A-Za-z0-9_.:-]{1,128}$/;
const QUALIFIED_VERSION = '0.2.2-rc.3';
const MAX_FILE_BYTES = 2 * 1024 * 1024;

function inspect(path, directory) {
  const info = lstatSync(path);
  if ((directory ? !info.isDirectory() : !info.isFile() || info.nlink !== 1)
    || info.uid !== process.getuid() || (info.mode & 0o077) || realpathSync(path) !== path) {
    throw new Error('Unverified managed skill projection');
  }
  return info;
}

function readPrivateMarker(path, pattern, minLength, maxLength = minLength) {
  inspect(path, false);
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const info = fstatSync(fd);
    if (!info.isFile() || info.size < minLength + 1 || info.size > maxLength + 1 || info.nlink !== 1
      || info.uid !== process.getuid() || (info.mode & 0o077)) {
      throw new Error('Invalid managed skill marker');
    }
    const text = readFileSync(fd, 'utf8');
    const content = text.slice(0, -1);
    if (text.length === info.size && text.endsWith('\n') && pattern.exec(content)?.[0] === content) {
      return content;
    }
    throw new Error('Invalid managed skill marker');
  } finally { closeSync(fd); }
}

function publishMarker(root, revision, operation) {
  const temp = join(root, `.publish-${randomUUID()}`);
  try {
    const file = openSync(temp, 'wx', 0o600);
    try {
      writeFileSync(file, `${revision}\n${operation}\n`);
      fsyncSync(file);
    } finally { closeSync(file); }
    renameSync(temp, join(root, 'published'));
    const directory = openSync(root, constants.O_RDONLY | constants.O_DIRECTORY | constants.O_NOFOLLOW);
    try { fsyncSync(directory); } finally { closeSync(directory); }
  } finally { rmSync(temp, { force: true }); }
}

function revisionDirectory(root, revision) {
  if (typeof revision !== 'string' || !REVISION.test(revision)) throw new Error('Invalid managed skill revision');
  inspect(join(root, 'revisions'), true);
  const directory = join(root, 'revisions', revision);
  inspect(directory, true);
  return directory;
}

function verifyTree(directory) {
  const stack = [directory];
  while (stack.length) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const path = join(current, entry.name);
      if (entry.isDirectory()) {
        inspect(path, true);
        stack.push(path);
      } else if (inspect(path, false).size > MAX_FILE_BYTES) {
        throw new Error('A managed skill file exceeds its size bound');
      }
    }
  }
}

/** Bind all RPCs to the one owner-provisioned scoped provider in this native host. */
export function createManagedSkillMount(ctx, config, callbacks) {
  if (config !== undefined && (!config || typeof config.mount_id !== 'string' || !MOUNT.test(config.mount_id)
    || typeof config.projection_root !== 'string' || !isAbsolute(config.projection_root))) {
    throw new Error('Invalid managed skill mount configuration');
  }
  const name = PROVIDER;
  const states = new WeakMap();
  const receipts = new Map();
  let active;
  let api;
  const native = packageName => {
    const resolve = createRequire(process.argv[1]).resolve;
    return import(pathToFileURL(resolve(`@deepseek-ai/${packageName}`)).href);
  };
  const load = () => api ??= Promise.all([native('dsh-skill-filesystem'), native('dsh-scope')]);
  const publicationIdentity = () => {
    const root = config.projection_root;
    inspect(root, true);
    if (readPrivateMarker(join(root, 'mount-id'), MOUNT, 32) !== config.mount_id) {
      throw new Error('Managed skill mount identity changed');
    }
    return readPrivateMarker(join(root, 'published'), /^[a-f0-9]{40}(?:\n[A-Za-z0-9_.:-]{1,128})?$/, 40, 169)
      .split('\n');
  };
  const marker = () => publicationIdentity()[0];
  const checkedState = agent => {
    const state = states.get(agent);
    if (!state?.qualified) callbacks.fail('unsupported_operation', 'Managed skill mount is unavailable');
    return state;
  };
  const withProvider = async (state, revision, use) => {
    const directory = revisionDirectory(config.projection_root, revision);
    const abort = new AbortController();
    const provider = new state.filesystem.FileSystemSkillProvider(
      state.ctx,
      { signal: abort.signal, invalidate() {} },
      { providerName: name, includeDefaultRoots: false, customSkillDirs: [directory], watch: false },
    );
    try { return await use(provider, directory); }
    finally { abort.abort(); await provider.dispose(); }
  };
  const candidates = (state, revision, options) => withProvider(state, revision, async provider => {
    const result = await provider.list(options);
    const entries = Array.isArray(result) ? result : result.candidates;
    return { entries, complete: Array.isArray(result) || result.complete };
  });
  const optionsFor = (agent, signal) => ({ cwd: callbacks.cwd, scope: agent, signal });

  /** Validate every visible skill and its immutable origin before publication. */
  const preflight = async (state, agent, revision, signal) => {
    const directory = revisionDirectory(config.projection_root, revision);
    verifyTree(directory);
    const names = new Set();
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      if (!entry.isDirectory() || !SKILL.test(entry.name)) {
        callbacks.fail('invalid_request', 'A versioned skill needs a named directory and SKILL.md');
      }
      inspect(join(directory, entry.name, 'SKILL.md'), false);
      names.add(entry.name);
    }
    const options = optionsFor(agent, signal);
    const discovered = await candidates(state, revision, options);
    if (!discovered.complete || discovered.entries.length !== names.size
      || new Set(discovered.entries.map(entry => entry.name)).size !== names.size
      || discovered.entries.some(entry => !names.has(entry.name))) {
      callbacks.fail('invalid_request', 'Managed skill definitions are invalid or unavailable');
    }
    const [scoped, global] = await Promise.all([
      ctx.get('skills').snapshot(options),
      ctx.get('skills').snapshot({ cwd: callbacks.cwd, signal }),
    ]);
    if (!scoped.complete || !global.complete) {
      callbacks.fail('unavailable', 'Existing native skill catalog is incomplete');
    }
    if ([...scoped.skills, ...global.skills].some(entry => entry.provider !== name && names.has(entry.name))) {
      callbacks.fail('conflict', 'Managed skill would shadow an existing native skill');
    }
    return discovered.entries;
  };

  /** Register once from the exact native Agent scope. */
  const register = async (agentCtx, agent, preset) => {
    if (!config || callbacks.nativeVersion !== QUALIFIED_VERSION || preset !== 'standard') return;
    const [filesystem, scope] = await load();
    const registry = ctx.get('skills');
    if (!registry || scope.scopeOf(agentCtx) !== agent
      || scope.scopeChainOf(agent).slice(1).some(ancestor => states.has(ancestor))) return;
    const state = { filesystem, ctx: agentCtx, revision: marker(), qualified: false, preset };
    await preflight(state, agent, state.revision, AbortSignal.timeout(10000));
    const providerPlugin = {
      name,
      inject: ['skills'],
      apply(scopedCtx) {
        if (scope.scopeOf(scopedCtx) !== agent) throw new Error('Managed skill provider scope changed');
        state.ctx = scopedCtx;
        scopedCtx.skills.registerProvider(control => {
          state.invalidate = control.invalidate;
          return {
            name,
            async list(options) {
              const revision = state.revision;
              const result = await candidates(state, revision, options);
              return {
                candidates: result.entries.map(entry => ({ ...entry, locator: { revision, original: entry } })),
                complete: result.complete,
              };
            },
            async get(entry, options) {
              const { revision, original } = entry.locator;
              return withProvider(state, revision, provider => provider.get(original, options));
            },
          };
        });
      },
    };
    state.fiber = agentCtx.plugin(providerPlugin);
    await state.fiber;
    if (typeof state.invalidate !== 'function') return;
    state.qualified = true;
    states.set(agent, state);
  };

  /** Attribute one result to current publication and later native settlement. */
  const publicReceipt = receipt => ({
    operation_id: receipt.operationId,
    outcome: receipt.outcome,
    published_commit: receipt.publishedCommit ?? null,
    effective_commit: receipt.effectiveCommit ?? null,
    native_settled: receipt.settled,
    native_ready: receipt.ready,
  });
  const ensureIdleBoundary = (operation, request, signal, peer) => {
    callbacks.authenticate(request, signal, peer);
    callbacks.requireIdentity(request.identity);
    if (peer !== operation.peer || request.operation_id !== operation.operationId
      || Date.now() >= operation.deadline) {
      callbacks.fail('stale_operation', 'Native skill maintenance authority changed');
    }
    if (callbacks.pendingInbox(operation.agent).hasPending || callbacks.pendingInteractions(operation.agent).length
      || ctx.agents.list().some(agent => agent !== operation.agent)) {
      callbacks.fail('busy', 'Native input, interaction, or a shared execution is active');
    }
  };
  const requireOperation = (agent, request, peer) => {
    if (!active || active.agent !== agent || active.peer !== peer
      || active.operationId !== request.operation_id || active.token !== request.maintenance_token) {
      callbacks.fail('stale_operation', 'Native skill maintenance authority is unavailable');
    }
    return active;
  };
  const awaitReady = async agent => {
    try {
      return await agent.runMaintenance(async () => {
        if (callbacks.pendingInbox(agent).hasPending || callbacks.pendingInteractions(agent).length
          || ctx.agents.list().some(other => other !== agent)) return false;
        return callbacks.ready(agent);
      });
    } catch { return false; }
  };
  const waitForNativeSerializer = async work => {
    const hmr = ctx.get('hmr');
    if (!hmr) return work();
    let claimed = false;
    let abandoned = false;
    const result = hmr.runExclusive(() => {
      if (abandoned) return undefined;
      claimed = true;
      return work();
    });
    await Promise.resolve();
    if (!claimed) {
      abandoned = true;
      void result.catch(() => {});
      callbacks.fail('busy', 'Native configuration serialization is occupied');
    }
    return result;
  };

  const open = async (agent, request, callerSignal, peer) => {
    const state = checkedState(agent);
    if (active) callbacks.fail('busy', 'A native skill publication already holds maintenance');
    const now = Date.now();
    if (typeof request.operation_id !== 'string' || !OPERATION.test(request.operation_id)
      || typeof request.candidate !== 'string' || !REVISION.test(request.candidate)
      || typeof request.expected !== 'string' || !REVISION.test(request.expected)
      || !Number.isSafeInteger(request.deadline_epoch_ms)
      || request.deadline_epoch_ms <= now || request.deadline_epoch_ms > now + 120000) {
      callbacks.fail('invalid_request', 'Native skill publication requires a bounded exact intent');
    }
    if (receipts.has(request.operation_id)) callbacks.fail('conflict', 'Native skill operation already exists');
    const bounded = AbortSignal.timeout(request.deadline_epoch_ms - now);
    const selected = Promise.withResolvers();
    const action = Promise.withResolvers();
    const publication = Promise.withResolvers();
    const released = Promise.withResolvers();
    const operation = {
      agent, peer, deadline: request.deadline_epoch_ms, operationId: request.operation_id,
      token: randomUUID(), candidate: request.candidate, expected: request.expected,
      outcome: 'pending', settled: false, ready: false, started: false,
      abort: () => { action.resolve(null); released.resolve(); },
      select: action.resolve, publication: publication.promise, release: released.resolve,
    };
    active = operation;
    receipts.set(operation.operationId, operation);
    if (receipts.size > 256) receipts.delete(receipts.keys().next().value);
    const stop = () => operation.abort();
    for (const signal of [bounded, callerSignal, peer.signal]) signal.addEventListener('abort', stop, { once: true });

    // Keep acquisition, marker publication, and final catalog proof inside one maintenance call.
    let entered = false;
    const work = async () => agent.runMaintenance(async maintenanceSignal => {
      entered = true;
      maintenanceSignal.addEventListener('abort', stop, { once: true });
      const signal = AbortSignal.any([bounded, callerSignal, peer.signal, maintenanceSignal]);
      try {
        ensureIdleBoundary(operation, request, signal, peer);
        if (marker() !== operation.expected || state.revision !== operation.expected) {
          callbacks.fail('conflict', 'Native skill publication base changed');
        }
        await preflight(state, agent, operation.candidate, signal);
        if (!await callbacks.checkSkillScope(agent, signal)) {
          callbacks.fail('unavailable', 'Native skill cache can affect an unverified live provider');
        }
        ensureIdleBoundary(operation, request, signal, peer);
        selected.resolve({ maintenance_token: operation.token });
        const invocation = await action.promise;
        if (invocation === null) {
          operation.outcome = 'unchanged';
          return;
        }
        try {
          const publicationSignal = AbortSignal.any([signal, invocation.signal]);
          const prepared = await preflight(state, agent, operation.candidate, publicationSignal);
          if (!await callbacks.checkSkillScope(agent, publicationSignal)) {
            callbacks.fail('unavailable', 'Native skill cache can affect an unverified live provider');
          }
          ensureIdleBoundary(operation, invocation.request, publicationSignal, peer);
          if (marker() !== operation.expected || state.revision !== operation.expected) {
            callbacks.fail('conflict', 'Native skill publication base changed');
          }
          publishMarker(config.projection_root, operation.candidate, operation.operationId);
          operation.publishedCommit = operation.candidate;
          state.revision = operation.candidate;
          state.invalidate();
          const reading = optionsFor(agent, AbortSignal.any([bounded, maintenanceSignal]));
          const current = await ctx.get('skills').snapshot(reading);
          const names = new Set(current.skills.filter(entry => entry.provider === name).map(entry => entry.name));
          if (!current.complete || names.size !== prepared.length || prepared.some(entry => !names.has(entry.name))) {
            callbacks.fail('unavailable', 'Native managed skill catalog could not be verified');
          }
          for (const entry of prepared) {
            const skill = await ctx.get('skills').get(entry.name, reading);
            const path = entry.locator.path;
            if (skill?.provider !== name || skill.path !== path
              || skill.resourceBase?.path !== entry.locator.directory) {
              callbacks.fail('unavailable', 'Native managed skill body or resource origin could not be verified');
            }
          }
          operation.effectiveCommit = operation.candidate;
          operation.outcome = 'activated';
        } catch {
          // Rename precedes directory fsync. A readable candidate marker is
          // publication evidence even when its durability call reported failure.
          try {
            const [revision, id] = publicationIdentity();
            if (revision === operation.candidate && id === operation.operationId) operation.publishedCommit = revision;
          } catch {}
          operation.outcome = operation.publishedCommit ? 'unknown' : 'unchanged';
        } finally { publication.resolve(publicReceipt(operation)); }
        await released.promise;
      } finally { maintenanceSignal.removeEventListener('abort', stop); }
    });
    const settled = (async () => {
      try { await waitForNativeSerializer(work); }
      catch (error) {
        if (operation.outcome === 'pending') operation.outcome = 'unchanged';
        selected.reject(entered || error?.managed ? error : Object.assign(new Error('Native work is active'), { code: 'busy', managed: true }));
      } finally {
        operation.settled = true;
        operation.ready = await awaitReady(agent);
        if (active === operation) active = undefined;
        for (const signal of [bounded, callerSignal, peer.signal]) signal.removeEventListener('abort', stop);
      }
      return publicReceipt(operation);
    })();
    operation.settlement = settled;
    return selected.promise;
  };

  return {
    register,
    providerName: name,
    managesFiber: (agent, fiber) => fiber.uid != null && states.get(agent)?.fiber.uid === fiber.uid,
    observeCandidates: async (agent, signal) => {
      const state = states.get(agent);
      if (!state?.qualified) return null;
      if (marker() !== state.revision) return { entries: [], complete: false };
      return candidates(state, state.revision, optionsFor(agent, signal));
    },
    assertIdle() {
      if (active) callbacks.fail('busy', 'Managed skill publication holds native maintenance');
    },
    guardCreated(agent) {
      if (active && active.agent !== agent) callbacks.fail('busy', 'Managed skill publication holds native resources');
    },
    describe(agent) {
      const state = states.get(agent);
      return state?.qualified ? { mount_id: config.mount_id, preset: state.preset, build: QUALIFIED_VERSION } : null;
    },
    open,
    publish(agent, request, signal, peer) {
      const operation = requireOperation(agent, request, peer);
      if (operation.started) callbacks.fail('conflict', 'Native skill publication was already dispatched');
      operation.started = true;
      operation.select({ request, signal });
      return operation.publication;
    },
    close(agent, request, peer) {
      const operation = requireOperation(agent, request, peer);
      operation.abort();
      return operation.settlement;
    },
    async status(agent, request) {
      const receipt = receipts.get(request.operation_id);
      if (!receipt || receipt.agent !== agent) return null;
      if (receipt.settled && !receipt.ready && !active) receipt.ready = await awaitReady(agent);
      return publicReceipt(receipt);
    },
  };
}
