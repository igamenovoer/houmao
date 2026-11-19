/** Owner-authenticated DSH Web control with synchronous native admission. */
import { randomUUID } from 'node:crypto';
import { chmodSync, existsSync, readFileSync, renameSync, statSync, writeFileSync, appendFileSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { createCommonRefresh } from './managed-refresh.mjs';

export const name = 'houmao-managed-web';
export const inject = ['agents', 'sessions', 'agentPresets', 'llm', 'systemPrompt', 'sessionPersistence', 'sessionQuery', 'connection', 'webServer', 'typertGateway', 'attachments', 'permissionPresets'];
const VERSION = 1;
const IDENTITY_KEYS = ['agent_id', 'runtime_session_id', 'generation', 'host_incarnation', 'native_session_id', 'agent_incarnation'];

/** Validate private authority before registering any routes. */
function controlFrom(path) {
  if (typeof path !== 'string' || !isAbsolute(path)) throw new Error('Houmao Web controlFile must be absolute');
  const value = JSON.parse(readFileSync(path, 'utf8'));
  for (const key of ['agent_id', 'runtime_session_id', 'generation', 'working_directory', 'state_path', 'evidence_path', 'bootstrap_path', 'provider', 'model']) {
    if (typeof value[key] !== 'string' || !value[key]) throw new Error(`Houmao Web requires ${key}`);
  }
  if (value.version !== VERSION || value.mode !== 'web') throw new Error('Incompatible Houmao Web control');
  if (value.native_version !== undefined && (typeof value.native_version !== 'string' || !value.native_version)) {
    throw new Error('Houmao Web native_version must be a non-empty string when provided');
  }
  for (const key of ['working_directory', 'state_path', 'evidence_path', 'bootstrap_path']) {
    if (!isAbsolute(value[key])) throw new Error(`Houmao Web ${key} must be absolute`);
  }
  return value;
}

/** Resolve the running DSH package version without assuming one pinned build. */
function resolveNativeVersion(control) {
  if (typeof control.native_version === 'string' && control.native_version) return control.native_version;
  try {
    const nativeRequire = createRequire(process.argv[1]);
    return JSON.parse(readFileSync(nativeRequire.resolve('@deepseek-ai/dsh/package.json'), 'utf8')).version ?? null;
  } catch {
    return null;
  }
}

/** Replace a private metadata file without exposing partially written JSON. */
function writePrivate(path, value) {
  const temporary = `${path}.${randomUUID()}.tmp`;
  writeFileSync(temporary, `${JSON.stringify(value)}\n`, {mode: 0o600, flag: 'wx'});
  renameSync(temporary, path);
  chmodSync(path, 0o600);
}

/** Settle only original receipts whose exact durable native claims closed. */
export function reconcileNativeReceipts(session, receipts, expected) {
  const candidates = receipts.filter(receipt => receipt.status === 'claimed'
    && typeof receipt.operation_id === 'string' && typeof receipt.message_id === 'string'
    && receipt.identity?.agent_id === expected.agent_id
    && receipt.identity?.runtime_session_id === expected.runtime_session_id
    && receipt.identity?.native_session_id === session.id
    && typeof receipt.identity?.generation === 'string' && receipt.identity.generation.length > 0
    && typeof receipt.identity?.host_incarnation === 'string' && receipt.identity.host_incarnation.length > 0
    && typeof receipt.identity?.agent_incarnation === 'string' && receipt.identity.agent_incarnation.length > 0
    && Array.isArray(receipt.claims) && receipt.claims.length > 0
    && Array.isArray(receipt.turns) && receipt.turns.length > 0
    && receipt.claims.every(claim => Number.isSafeInteger(claim.turn) && claim.turn >= 0
      && Number.isSafeInteger(claim.native_sequence) && claim.native_sequence >= 0)
    && receipt.turns.every(turn => receipt.claims.some(claim => claim.turn === turn))
    && receipt.claims.every(claim => receipt.turns.includes(claim.turn)));
  if (!candidates.length) return [];
  const inbox = {'next-turn': [], 'next-step': []};
  const proofs = new Map(candidates.map(receipt => [receipt, new Set()]));
  const endings = new Map();
  let activeTurn = null;
  let removed = [];
  let previousSplice = false;
  for (let seq = 0; seq < session.seq; seq++) {
    const event = session.eventAt(seq);
    if (!event || event.seq !== seq) return [];
    if (event.type === 'turn/start') {
      if (activeTurn !== null || !Number.isSafeInteger(event.data.turn)) return [];
      activeTurn = event.data.turn;
    }
    if (event.type === 'agent/inbox/spliced') {
      const splice = event.data;
      const list = Object.hasOwn(inbox, splice.target) ? inbox[splice.target] : undefined;
      const count = splice.removedCount ?? 0;
      if (!list || !Number.isSafeInteger(splice.start) || splice.start < 0
        || !Number.isSafeInteger(count) || count < 0 || splice.start + count > list.length
        || !Array.isArray(splice.inserted)
        || splice.inserted.some(message => typeof message.id !== 'string')) return [];
      if (!previousSplice) removed = [];
      const inserted = splice.inserted.map(message => ({id: message.id, kind: message.source?.kind,
        operation: candidates.find(receipt => receipt.message_id === message.id
          && message.source?.kind === 'user'
          && message.source?.rpcId === `houmao:${receipt.operation_id}`)?.operation_id ?? null}));
      removed.push(...list.splice(splice.start, count, ...inserted));
      const ids = [...inbox['next-turn'], ...inbox['next-step']].map(message => message.id);
      if (new Set(ids).size !== ids.length) return [];
      for (const receipt of candidates) for (const claim of receipt.claims) {
        if (claim.native_sequence === seq && claim.turn === activeTurn
          && removed.some(message => message.id === receipt.message_id && message.operation === receipt.operation_id)) {
          proofs.get(receipt).add(claim);
        }
      }
    }
    previousSplice = event.type === 'agent/inbox/spliced';
    if (event.type === 'turn/end') {
      if (activeTurn !== event.data.turn || !['completed', 'aborted', 'interrupted', 'error', 'forked'].includes(event.data.reason?.kind)) return [];
      endings.set(activeTurn, event);
      activeTurn = null;
    }
  }
  const settled = [];
  for (const receipt of candidates) {
    if (proofs.get(receipt).size !== receipt.claims.length
      || receipt.claims.some(claim => !endings.has(claim.turn)
        || endings.get(claim.turn).seq <= claim.native_sequence)) continue;
    const terminal = receipt.turns.map(turn => endings.get(turn)).sort((left, right) => right.seq - left.seq)[0];
    receipt.status = 'terminal';
    receipt.result = terminal.data.reason.kind;
    receipt.end_sequence = terminal.seq;
    receipt.mixed_input ??= 'unknown';
    settled.push(receipt);
  }
  return settled;
}

/** Install one private-host control surface; never create an Agent on inspection. */
export function apply(ctx, config) {
  const control = controlFrom(config.controlFile);
  const hostIncarnation = randomUUID();
  const nonces = new WeakMap();
  const stored = existsSync(control.state_path) ? JSON.parse(readFileSync(control.state_path, 'utf8')) : {version: VERSION, receipts: [], history: [], sequence: 0};
  if (stored.version !== VERSION || !Array.isArray(stored.receipts) || !Array.isArray(stored.history)) throw new Error('Invalid Houmao Web receipt state');
  const receipts = new Map(stored.receipts.map(receipt => [receipt.operation_id, receipt]));
  const history = stored.history;
  let sequence = stored.sequence;
  let root;
  let handle;
  let creating = false;
  let targetSession;
  let abandoned = new Set();
  let lastTurn = null;
  const claimedInputs = new Map();
  const observedTurnStarts = new Set();
  if (control.roleFile) {
    const role = readFileSync(control.roleFile, 'utf8');
    if (role) ctx.systemPrompt.section({name: 'houmao:managed-role', order: 0, text: role, interpolate: false});
  }

  const identity = agent => ({protocol_version: VERSION, agent_id: control.agent_id, runtime_session_id: control.runtime_session_id, generation: control.generation, host_incarnation: hostIncarnation, native_session_id: agent?.id ?? null, agent_incarnation: agent ? nonces.get(agent) ?? null : null});
  const persist = () => writePrivate(control.state_path, {version: VERSION, receipts: [...receipts.values()], history, sequence});
  const record = (event, agent, fields = {}) => {
    const row = {sequence: sequence++, event, observed_at_utc: new Date().toISOString(), identity: identity(agent), ...fields};
    history.push(row);
    if (history.length > 1000) history.splice(0, history.length - 1000);
    appendFileSync(control.evidence_path, `${JSON.stringify(row)}\n`, {mode: 0o600});
    persist();
    return row;
  };
  const fail = (code, message) => { throw Object.assign(new Error(message), {code, managed: true}); };
  const live = () => root !== undefined && ctx.agents.get(root.id) === root && ctx.sessions.get(root.id) === root.session;
  const authenticate = (request, signal, peer) => {
    if (peer.principal.kind !== 'owner' || peer.signal.aborted) fail('forbidden', 'Live owner authorization required');
    if (signal.aborted) fail('cancelled', 'Caller no longer active');
    if (request?.protocol_version !== VERSION) fail('protocol_mismatch', 'Managed protocol version mismatch');
  };
  const requireIdentity = expected => {
    if (!live()) fail('unavailable', 'Bound native Agent is not live');
    const actual = identity(root);
    if (!expected || IDENTITY_KEYS.some(key => expected[key] !== actual[key])) fail('stale_identity', 'Native execution identity changed');
    return root;
  };
  const pendingInteractions = agent => {
    const pending = ctx.typertGateway.getPendingRemoteEvents();
    if (!Array.isArray(pending)) fail('unknown_state', 'Native interaction state unavailable');
    return [...new Set(pending.filter(item => String(item.agentId) === agent.id).map(item => item.event === 'approval/request' ? 'approval' : item.event === 'user-questions/request' ? 'question' : 'other'))];
  };
  const pendingInbox = agent => {
    const nextTurn = agent.inbox.nextTurn;
    const nextStep = agent.inbox.nextStep;
    if (!Array.isArray(nextTurn) || !Array.isArray(nextStep) || typeof agent.inbox.hasPending !== 'boolean' || agent.inbox.hasPending !== (nextTurn.length + nextStep.length > 0)) fail('unknown_state', 'Native pending-input state unavailable');
    return {nextTurn, nextStep, hasPending: nextTurn.length + nextStep.length > 0};
  };
  const snapshot = (agent, trueIdle = false) => {
    const available = live() && agent === root;
    const boundary = available ? ctx.agents.turnBoundaryOf(agent.session) : null;
    const waits = available ? pendingInteractions(agent) : [];
    const pending = available ? pendingInbox(agent) : null;
    const inbox = available ? [['next_turn', pending.nextTurn], ['next_step', pending.nextStep]].flatMap(([placement, messages]) => messages.map(message => {
      const receipt = [...receipts.values()].find(item => item.message_id === message.id);
      return {message_id: message.id, placement, operation_id: receipt?.operation_id ?? null, operator: receipt?.operator ?? null};
    })) : [];
    const unblocked = available && waits.length === 0 && !creating;
    const selected = available ? agent.model.current() : undefined;
    return {protocol_version: VERSION, identity: identity(agent), sequence: sequence - 1, observed_at_utc: new Date().toISOString(), cursor: available ? agent.session.seq - 1 : -1, available, active_turn: boundary?.openTurnStartSeq === null || !boundary ? null : {turn: boundary.lastTurn, start_sequence: boundary.openTurnStartSeq}, last_turn: lastTurn, pending_inbox: inbox, interaction_waits: waits, admission: {ready_only: unblocked && trueIdle && inbox.length === 0, if_no_pending: unblocked && inbox.length === 0, always: available && !creating, reason: !available ? 'unavailable' : creating ? 'lifecycle' : waits.length ? 'interaction_wait' : inbox.length ? 'pending_input' : !trueIdle ? 'active_work' : null}, model: selected ? {provider: selected.provider, model: selected.model, reasoning_effort: selected.reasoningEffort ?? null} : null};
  };
  const checkDeadline = (request, signal, peer) => {
    authenticate(request, signal, peer);
    if (!Number.isSafeInteger(request.deadline_epoch_ms) || Date.now() >= request.deadline_epoch_ms) fail('expired', 'Dispatch deadline elapsed');
  };
  const checkDispatchPermission = request => {
    if (request.dispatch_permission_path === undefined) return;
    let allowed = false;
    try {
      const path = request.dispatch_permission_path;
      if (typeof path !== 'string' || !isAbsolute(path)) throw new Error('Invalid permission path');
      const info = statSync(path);
      if (!info.isFile() || (info.mode & 0o077)) throw new Error('Permission must remain private');
      const permission = JSON.parse(readFileSync(path, 'utf8'));
      if (permission.active !== true || typeof permission.expires_at !== 'number' || !Number.isFinite(permission.expires_at) || Date.now() >= permission.expires_at * 1000) throw new Error('Inactive permission');
      if (!Number.isSafeInteger(permission.origin_pid) || permission.origin_pid <= 0 || typeof permission.origin_birth_token !== 'string') throw new Error('Missing caller identity');
      const raw = readFileSync(`/proc/${permission.origin_pid}/stat`, 'utf8');
      const fields = raw.slice(raw.lastIndexOf(')') + 1).trim().split(/\s+/);
      if (fields.length < 20 || ['Z', 'X', 'x'].includes(fields[0]) || !/^\d+$/.test(fields[19]) || permission.origin_birth_token !== `proc:${fields[19]}`) throw new Error('Caller identity changed');
      if (permission.registry_generation_id !== control.generation || typeof permission.manifest_path !== 'string' || !isAbsolute(permission.manifest_path)) throw new Error('Missing execution fence');
      const manifest = JSON.parse(readFileSync(permission.manifest_path, 'utf8'));
      const bound = manifest.backend_state?.web_identity;
      if (manifest.registry_generation_id !== control.generation || !bound || IDENTITY_KEYS.some(key => bound[key] !== request.identity[key])) throw new Error('Execution binding changed');
      allowed = true;
    } catch {}
    if (!allowed) fail('cancelled', 'Managed dispatch permission is no longer active');
  };
  const composition = async presetId => {
    const preset = await ctx.agentPresets.resolve(presetId);
    const nativeRequire = createRequire(process.argv[1]);
    const {installModelSelection} = await import(pathToFileURL(nativeRequire.resolve('@deepseek-ai/dsh-agent')).href);
    return {agentPreset: preset.id, setup: async agentCtx => { installModelSelection(agentCtx); await ctx.agentPresets.mount(agentCtx, preset.id); }};
  };
  const nativeVersion = resolveNativeVersion(control);
  const commonRefresh = createCommonRefresh(ctx, {
    cwd: control.working_directory, identity, live, authenticate, requireIdentity,
    pendingInteractions, pendingInbox, fail, nativeVersion,
    ready: async agent => {
      const value = snapshot(agent, true);
      if (!value.available || !value.model || value.interaction_waits.length) return false;
      await ctx.llm.resolveCallConfig(agent.model.current());
      return true;
    },
  });

  ctx.on('webserver/entry-url', (origin, entries) => {
    const signed = entries.find(entry => new URL(entry.url).searchParams.has('token'));
    if (!signed) throw new Error('Houmao Web native sign-in mechanism unavailable');
    writePrivate(control.bootstrap_path, {version: VERSION, origin: new URL(origin).origin, launch_token: new URL(signed.url).searchParams.get('token')});
  });
  // The qualified rc.3 package exposes the native sign-in service directly.
  // Newer source separates that provider and contributes entry-url events instead.
  ctx.inject(['connection', 'webServer'], webCtx => webCtx.effect(() => {
    const timer = setInterval(() => {
      if (webCtx.webServer.port === undefined || typeof webCtx.connection.authenticatedUrl !== 'function') return;
      const origin = webCtx.webServer.getOrigin();
      const signed = new URL(webCtx.connection.authenticatedUrl(origin));
      writePrivate(control.bootstrap_path, {version: VERSION, origin, launch_token: signed.searchParams.get('token')});
      clearInterval(timer);
    }, 10);
    return () => clearInterval(timer);
  }));
  ctx.on('agent/created', ({agent}) => {
    nonces.set(agent, randomUUID());
    if (agent.id !== targetSession) return;
    const inbox = pendingInbox(agent);
    const pending = [...inbox.nextTurn, ...inbox.nextStep];
    for (const message of pending) {
      if (!message.source?.rpcId?.startsWith('houmao:')) continue;
      const receipt = [...receipts.values()].find(item => item.message_id === message.id);
      if (!receipt || (!receipt.operator && !abandoned.has(receipt.operation_id))) fail('reconciliation_required', 'Pending managed input lacks abandonment proof');
    }
    for (const message of pending) {
      const receipt = [...receipts.values()].find(item => item.message_id === message.id);
      if (receipt && !receipt.operator && abandoned.has(receipt.operation_id)) {
        if (!agent.inbox.remove(message.id)) fail('reconciliation_required', 'Pending input changed');
        receipt.status = 'abandoned';
        record('reconciled', agent, {operation_id: receipt.operation_id, message_id: message.id});
      }
    }
    if (typeof control.permission_preset === 'string') {
      ctx.permissionPresets.set(agent.session, control.permission_preset);
      if (ctx.permissionPresets.current(agent.session) !== control.permission_preset) {
        fail('permission_mismatch', 'Native agent did not apply the requested permission preset');
      }
    }
    root = agent;
    lastTurn = null;
    for (let seq = agent.session.seq - 1; seq >= 0; seq--) {
      const event = agent.session.eventAt(seq);
      if (event?.type === 'turn/end') { lastTurn = {turn: event.data.turn, result: event.data.reason.kind, end_sequence: event.seq}; break; }
    }
    for (const receipt of reconcileNativeReceipts(agent.session, [...receipts.values()], control)) {
      record('receipt/settled', agent, {operation_id: receipt.operation_id, message_id: receipt.message_id,
        turn: receipt.turns.at(-1), native_sequence: receipt.end_sequence, result: receipt.result});
    }
    record('created', agent);
  });
  ctx.on('agent/inbox/inserted', ({agent, message}) => {
    if (agent !== root) return;
    const receipt = [...receipts.values()].find(item => item.message_id === message.id);
    if (receipt) { receipt.status = 'admitted'; receipt.admitted_sequence = agent.session.seq - 1; }
    record('inbox/inserted', agent, {message_id: message.id, operation_id: receipt?.operation_id ?? null, native_sequence: agent.session.seq - 1});
  });
  ctx.on('agent/inbox/claimed', ({agent, message, turn}) => {
    if (agent !== root) return;
    const receipt = [...receipts.values()].find(item => item.message_id === message.id);
    const inputs = claimedInputs.get(turn) ?? new Map();
    inputs.set(message.id, {operation_id: receipt?.operation_id ?? null, input_kind: ['user', 'user-question-reply'].includes(message.source?.kind) ? message.source.kind : 'other'});
    claimedInputs.set(turn, inputs);
    if (receipt) { receipt.status = 'claimed'; receipt.turns = [...new Set([...receipt.turns, turn])]; receipt.claims.push({turn, native_sequence: agent.session.seq - 1}); }
    record('inbox/claimed', agent, {message_id: message.id, operation_id: receipt?.operation_id ?? null, turn, native_sequence: agent.session.seq - 1});
  });
  ctx.on('session/event', (session, event) => {
    if (root?.session !== session || !['turn/start', 'turn/end'].includes(event.type)) return;
    if (event.type === 'turn/start') observedTurnStarts.add(event.data.turn);
    if (event.type === 'turn/end') {
      lastTurn = {turn: event.data.turn, result: event.data.reason.kind, end_sequence: event.seq};
      const inputs = claimedInputs.get(event.data.turn);
      for (const receipt of receipts.values()) if (receipt.identity.native_session_id === root.id && receipt.turns.includes(event.data.turn)) { receipt.status = 'terminal'; receipt.result = event.data.reason.kind; receipt.end_sequence = event.seq; receipt.mixed_input = inputs && [...inputs.values()].some(input => input.operation_id !== receipt.operation_id && input.input_kind !== 'other') ? true : inputs?.has(receipt.message_id) && observedTurnStarts.has(event.data.turn) ? false : 'unknown'; receipt.input_claims = inputs ? [...inputs.entries()].map(([message_id, input]) => ({message_id, ...input})) : []; }
      claimedInputs.delete(event.data.turn);
      observedTurnStarts.delete(event.data.turn);
    }
    record(event.type, root, {turn: event.data.turn, native_sequence: event.seq, ...(event.type === 'turn/end' ? {result: event.data.reason.kind} : {})});
  });
  ctx.on('agent/disposed', ({agent}) => { if (agent === root) record('disposed', agent); });

  const operations = {
    describe: async () => ({protocol_version: VERSION, identity: identity(root), capabilities: ['state', 'history', 'conversation', 'prompt', 'receipt', 'interrupt', 'start', 'reset', 'stop', 'set_model', 'common_state', 'refresh'], build: nativeVersion}),
    common_state: async request => commonRefresh.observe(requireIdentity(request.identity)),
    refresh: async (request, signal, peer) => commonRefresh.refresh(requireIdentity(request.identity), request, signal, peer),
    state: async request => {
      if (request.identity) requireIdentity(request.identity);
      if (!live()) return snapshot(root);
      try { return await root.runMaintenance(() => Promise.resolve(snapshot(root, true))); }
      catch { return snapshot(root); }
    },
    history: async request => {
      requireIdentity(request.identity);
      const after = request.after_sequence ?? -1;
      const limit = Math.min(request.limit ?? 100, 1000);
      if (!Number.isSafeInteger(after) || after < -1 || !Number.isSafeInteger(limit) || limit < 1) fail('invalid_request', 'Invalid history bounds');
      const current = identity(root);
      const scoped = history.filter(row => IDENTITY_KEYS.every(key => row.identity[key] === current[key]));
      const rows = scoped.filter(row => row.sequence > after);
      return {identity: current, sequence: sequence - 1, entries: rows.slice(0, limit), has_more: rows.length > limit, truncated: after >= 0 && scoped.length > 0 && after < scoped[0].sequence - 1};
    },
    conversation: async request => {
      const agent = requireIdentity(request.identity);
      const after = request.after_native_sequence ?? -1;
      const limit = request.limit ?? 100;
      if (!Number.isSafeInteger(after) || after < -1 || !Number.isSafeInteger(limit) || limit < 1 || limit > 1000) fail('invalid_request', 'Invalid native history bounds');
      const current = agent.session.seq - 1;
      if (after > current) fail('invalid_cursor', 'Native history cursor is beyond this conversation');
      const through = Math.min(current, after + limit);
      const entries = [];
      const content = message => (message?.content ?? []).flatMap(block => {
        if (['text', 'reasoning'].includes(block.type) && typeof block.text === 'string') return [{type: block.type, text: block.text}];
        if (block.type === 'tool-call') return [{type: block.type, id: block.id, name: block.name, arguments: block.arguments}];
        return [];
      });
      for (let seq = after + 1; seq <= through; seq++) {
        const event = agent.session.eventAt(seq);
        if (!event) fail('history_gap', 'Bound native event is unavailable');
        const data = event.data;
        const base = {native_sequence: event.seq, type: event.type, time: event.time, ...(typeof data.turn === 'number' ? {turn: data.turn} : {}), ...(typeof data.step === 'number' ? {step: data.step} : {})};
        if (event.type === 'assistant/message') entries.push({...base, message_id: data.message.id, content: content(data.message), interrupted: data.interrupted === true});
        else if (event.type === 'tool/call') entries.push({...base, call_id: data.callId, name: data.name, arguments: data.arguments});
        else if (event.type === 'tool/result') entries.push({...base, message_id: data.message.id, call_id: data.message.source.callId, name: data.message.source.name, is_error: data.message.isError === true, content: content(data.message)});
        else if (['turn/start', 'turn/end', 'step/start', 'step/end'].includes(event.type)) entries.push({...base, ...(data.reason ? {result: data.reason.kind} : {})});
        else if (event.type === 'model/selection') entries.push({...base, provider: data.provider, model: data.model, reasoning_effort: data.reasoningEffort ?? null});
        else if (event.type === 'user/message') entries.push({...base, message_id: data.id});
        else if (event.type === 'approval/policy') entries.push({...base, policy: data.policy});
        else if (event.type === 'sandbox/mode') entries.push({...base, mode: data.mode});
        else if (event.type === 'permission/preset') entries.push({...base, preset: data.preset});
      }
      return {identity: identity(agent), after_native_sequence: after, cursor: through, current_cursor: current, entries, has_more: through < current};
    },
    start: async (request, signal, peer) => {
      if (creating) fail('busy', 'Lifecycle operation already active');
      if (!['new', 'exact'].includes(request.mode)) fail('invalid_request', 'Explicit new or exact selection required');
      if (live()) fail('busy', 'Stop the bound Agent before starting another');
      if (request.mode === 'exact' && (typeof request.session_id !== 'string' || !request.session_id)) fail('invalid_request', 'Exact session identity required');
      if (request.mode === 'exact' && control.expected_native_session_id && request.session_id !== control.expected_native_session_id) fail('wrong_session', 'Explicit native session does not match the managed binding');
      const abandonedIds = request.abandoned_operation_ids ?? [];
      if (!Array.isArray(abandonedIds) || abandonedIds.some(id => !receipts.has(id) || receipts.get(id).operator)) fail('reconciliation_required', 'Abandonment requires known ordinary operation receipts');
      creating = true;
      abandoned = new Set(abandonedIds);
      targetSession = request.mode === 'exact' ? request.session_id : `session-${randomUUID()}`;
      try {
        if (ctx.agents.get(targetSession)) fail('unavailable', 'Native target already has another lifecycle owner');
        let presetId;
        if (request.mode === 'exact') {
          using observation = await ctx.sessionQuery.observeSession(targetSession);
          if (observation.header.cwd !== control.working_directory) fail('wrong_workspace', 'Native workspace does not match');
          if (observation.header.origin === 'subagent') fail('wrong_session', 'Managed Web requires an ordinary root session');
          presetId = observation.header.agentPreset;
        }
        const composed = await composition(presetId);
        authenticate(request, signal, peer);
        const options = {provider: control.provider, model: control.model};
        handle = request.mode === 'exact' ? await ctx.agents.resume({resumeSessionId: targetSession, signal, agentOptions: options, setup: composed.setup}) : await ctx.agents.create({sessionId: targetSession, signal, agentOptions: options, meta: {cwd: control.working_directory, agentPreset: composed.agentPreset}, setup: composed.setup});
        if (handle.agent !== root) fail('unavailable', 'Native publication did not establish the managed binding');
        if (root.session.header.cwd !== control.working_directory) { await handle.dispose(); fail('wrong_workspace', 'Native workspace does not match'); }
        return identity(root);
      } finally { creating = false; }
    },
    prompt: async (request, signal, peer) => {
      const agent = requireIdentity(request.identity);
      const policy = request.admission_policy ?? 'ready_only';
      if (!['ready_only', 'if_no_pending', 'always'].includes(policy) || (policy !== 'ready_only' && request.operator !== true)) fail('invalid_policy', 'Only explicit operator input may queue');
      if (typeof request.operation_id !== 'string' || !request.operation_id || typeof request.text !== 'string' || !request.text.trim()) fail('invalid_request', 'Identified nonempty prompt required');
      const existing = receipts.get(request.operation_id);
      if (existing) return {...existing, duplicate: true};
      const content = await ctx.attachments.admitPromptContent([{type: 'text', text: request.text}]);
      authenticate(request, signal, peer);
      requireIdentity(request.identity);
      if (receipts.has(request.operation_id)) return {...receipts.get(request.operation_id), duplicate: true};
      const admit = () => {
        checkDeadline(request, signal, peer);
        checkDispatchPermission(request);
        if (requireIdentity(request.identity) !== agent || creating) fail('stale_identity', 'Native execution changed');
        if (receipts.has(request.operation_id)) return receipts.get(request.operation_id);
        if (policy !== 'always' && pendingInteractions(agent).length) fail('interaction_wait', 'Native human interaction pending');
        if (policy !== 'always' && pendingInbox(agent).hasPending) fail('pending_input', 'Native inbox is not empty');
        const message = Object.freeze({id: randomUUID(), role: 'user', source: Object.freeze({kind: 'user', rpcId: `houmao:${request.operation_id}`}), content: Object.freeze(content)});
        const receipt = {operation_id: request.operation_id, message_id: message.id, identity: identity(agent), operator: request.operator === true, admission_policy: policy, status: 'prepared', turns: [], claims: [], created_at_utc: new Date().toISOString()};
        receipts.set(receipt.operation_id, receipt);
        persist();
        agent.followup(message);
        return {...receipt};
      };
      if (policy !== 'ready_only') return admit();
      let acquired = false;
      try { return await agent.runMaintenance(() => { acquired = true; return Promise.resolve(admit()); }); }
      catch (error) { if (error.managed || acquired) throw error; fail('not_ready', 'Native agent has active work'); }
    },
    receipt: async request => { requireIdentity(request.identity); return receipts.get(request.operation_id) ?? null; },
    set_model: async (request, signal, peer) => {
      const agent = requireIdentity(request.identity);
      if (typeof request.provider !== 'string' || !request.provider || typeof request.model !== 'string' || !request.model || (request.reasoning_effort !== undefined && request.reasoning_effort !== null && typeof request.reasoning_effort !== 'string')) fail('invalid_request', 'Explicit provider/model selection required');
      const models = await ctx.llm.listModels(request.provider);
      if (!models.some(model => model.id === request.model)) fail('model_unavailable', 'Requested model is not in the configured native catalog');
      const selection = {provider: request.provider, model: request.model, ...(request.reasoning_effort === undefined || request.reasoning_effort === null ? {} : {reasoningEffort: request.reasoning_effort})};
      await ctx.llm.resolveCallConfig(selection);
      authenticate(request, signal, peer);
      if (requireIdentity(request.identity) !== agent || creating) fail('stale_identity', 'Native execution changed during model resolution');
      agent.model.select(selection);
      return {identity: identity(agent), model: {provider: selection.provider, model: selection.model, reasoning_effort: selection.reasoningEffort ?? null}};
    },
    reset: async (request, signal, peer) => {
      const agent = requireIdentity(request.identity);
      if (creating || !handle || handle.agent !== agent) fail('unavailable', 'Native lifecycle ownership unavailable');
      if ((request.admission_policy ?? 'ready_only') !== 'ready_only') fail('invalid_policy', 'Reset requires ready-only admission');
      try {
        await agent.runMaintenance(() => {
          authenticate(request, signal, peer);
          requireIdentity(request.identity);
          if (pendingInteractions(agent).length) fail('interaction_wait', 'Native interaction is pending');
          if (pendingInbox(agent).hasPending) fail('pending_input', 'Native inbox is not empty');
          creating = true;
          agent.cancel({kind: 'disposed'}, {keepInbox: true});
          return Promise.resolve();
        });
      } catch (error) { if (error.managed) throw error; fail('not_ready', 'Native agent has active work'); }
      try {
        await handle.dispose();
        authenticate(request, signal, peer);
        targetSession = `session-${randomUUID()}`;
        abandoned = new Set();
        const composed = await composition();
        authenticate(request, signal, peer);
        handle = await ctx.agents.create({sessionId: targetSession, signal, agentOptions: {provider: control.provider, model: control.model}, meta: {cwd: control.working_directory, agentPreset: composed.agentPreset}, setup: composed.setup});
        if (handle.agent !== root) fail('unavailable', 'Reset did not publish the expected Agent');
        lastTurn = null;
        return identity(root);
      } finally { creating = false; }
    },
    interrupt: async request => {
      const agent = requireIdentity(request.identity);
      const boundary = ctx.agents.turnBoundaryOf(agent.session);
      if (request.operation_id) {
        const receipt = receipts.get(request.operation_id);
        if (!receipt || receipt.identity.agent_incarnation !== identity(agent).agent_incarnation) fail('stale_operation', 'Operation does not own this execution');
        if (agent.inbox.remove(receipt.message_id)) { receipt.status = 'abandoned'; persist(); return {interrupted: false, removed: true}; }
        if (!receipt.turns.includes(boundary.lastTurn)) fail('stale_turn', 'Operation is not associated with the current turn');
      }
      if (boundary.openTurnStartSeq === null || boundary.openTurnStartSeq !== request.turn_start_seq) fail('stale_turn', 'Native active turn changed');
      agent.cancel({kind: 'user'}, {keepInbox: true});
      return {interrupted: true, removed: false};
    },
    stop: async request => { const agent = requireIdentity(request.identity); if (!handle || handle.agent !== agent) fail('unavailable', 'Lifecycle ownership unavailable'); await handle.dispose(); return {stopped: true}; },
  };
  const dispatch = async (endpoint, request, signal, peer) => {
    try {
      authenticate(request, signal, peer);
      const method = endpoint.startsWith('managed/v1/') ? endpoint.slice('managed/v1/'.length) : '';
      if (!Object.hasOwn(operations, method)) fail('unsupported_operation', 'Managed operation unavailable');
      return {ok: true, value: await operations[method](request, signal, peer)};
    } catch (error) { if (!error.managed) appendFileSync(`${control.state_path}.diagnostics`, `${String(error.stack)}\n`, {mode: 0o600}); return {ok: false, error: {code: error.managed ? error.code : 'native_failure', message: error.managed ? error.message : 'Native managed operation failed', details: {}}}; }
  };
  ctx.effect(() => ctx.webServer.register({kind: 'prefix', path: '/houmao', auth: 'required', async handler(req, res) {
    const admission = ctx.connection.admit(req);
    if ('rejection' in admission) { res.writeHead(admission.rejection); res.end(); return; }
    const abort = new AbortController();
    res.on('close', () => { if (!res.writableEnded) abort.abort(); });
    const endpoint = new URL(req.url, 'http://managed.invalid').pathname.slice('/houmao/'.length);
    if (req.method !== 'POST' || req.headers['content-type']?.split(';', 1)[0] !== 'application/json') { res.writeHead(415); res.end(); return; }
    let size = 0;
    const chunks = [];
    for await (const chunk of req) { size += chunk.length; if (size > 131072) { res.writeHead(413); res.end(); return; } chunks.push(chunk); }
    let envelope;
    try { envelope = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
    catch { res.writeHead(400); res.end(); return; }
    if (envelope.type !== 'client-request' || typeof envelope.rpcId !== 'string' || envelope.method !== endpoint || typeof envelope.payload !== 'object' || envelope.payload === null) { res.writeHead(400); res.end(); return; }
    const result = await dispatch(endpoint, envelope.payload, abort.signal, admission.peer);
    if (abort.signal.aborted) return;
    res.writeHead(200, {'content-type': 'application/json', 'cache-control': 'no-store'});
    res.end(JSON.stringify({type: 'server-response', rpcId: envelope.rpcId, result}));
  }}));
  record('loaded', undefined);
}
