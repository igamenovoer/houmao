/** Native DSH role projection and payload-free managed admission evidence. */

import { createHash, randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { closeSync, fsyncSync, openSync, readFileSync, renameSync, unlinkSync, writeSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';

export const name = 'houmao-managed-companion';
export const inject = ['agents', 'systemPrompt', 'sessionPersistence'];

/** Refuse malformed private controls before registering native lifecycle hooks. */
function readControl(filename) {
  if (typeof filename !== 'string' || !isAbsolute(filename)) {
    throw new Error('Houmao DSH companion requires an absolute controlFile');
  }
  const control = JSON.parse(readFileSync(filename, 'utf8'));
  if (control?.version !== 1
      || typeof control.attempt_id !== 'string' || !control.attempt_id
      || typeof control.runtime_session_id !== 'string' || !control.runtime_session_id
      || typeof control.generation !== 'string' || !control.generation
      || !(control.expected_native_session_id === null
        || typeof control.expected_native_session_id === 'string')
      || typeof control.evidence_path !== 'string' || !isAbsolute(control.evidence_path)
      || !Array.isArray(control.abandoned_message_ids)
      || control.abandoned_message_ids.some(id => typeof id !== 'string' || !id)) {
    throw new Error('Houmao DSH companion received invalid version-1 control');
  }
  if (control.one_shot !== undefined
      && (['manifest_path', 'guard_path', 'python_executable', 'session_path'].some(key =>
        typeof control.one_shot?.[key] !== 'string' || !isAbsolute(control.one_shot[key]))
        || control.process_id !== process.pid || typeof control.process_birth_token !== 'string')) {
    throw new Error('Houmao DSH companion received invalid one-shot ownership');
  }
  return control;
}

/** Atomically publish one payload-free, user-private binding or handoff record. */
function writeBinding(path, value) {
  const temporary = `${path}.${randomUUID()}.tmp`;
  try {
    const descriptor = openSync(temporary, 'wx', 0o600);
    try {
      writeSync(descriptor, `${JSON.stringify(value)}\n`);
      fsyncSync(descriptor);
    } finally {
      closeSync(descriptor);
    }
    renameSync(temporary, path);
  } finally {
    try { unlinkSync(temporary); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
}

/** Verify the exact owner and reread revocation in the native synchronous call stack. */
function requireOneShotPermission(control) {
  const fence = control.one_shot;
  const result = spawnSync(fence.python_executable, [
    '-m', 'houmao.agents.realm_controller.backends.dsh_headless_entry',
    '--verify-dispatch', fence.guard_path, fence.manifest_path, control.generation, control.attempt_id,
  ], { stdio: 'ignore', timeout: 5000 });
  if (result.status !== 0) throw new Error('Houmao DSH native input permission is unavailable');
  const permission = JSON.parse(readFileSync(fence.guard_path, 'utf8'));
  if (permission.active !== true || permission.expires_at <= Date.now() / 1000
      || permission.attempt_id !== control.attempt_id
      || permission.registry_generation_id !== control.generation
      || permission.manifest_path !== fence.manifest_path) {
    throw new Error('Houmao DSH native input permission was revoked');
  }
}

/** Register an additive literal role and observe one exclusively owned native root. */
export function apply(ctx, config) {
  const control = readControl(config.controlFile);
  let role = '';
  if (config.roleFile !== undefined && config.roleFile !== null) {
    if (typeof config.roleFile !== 'string' || !isAbsolute(config.roleFile)) {
      throw new Error('Houmao DSH companion requires an absolute roleFile');
    }
    role = readFileSync(config.roleFile, 'utf8');
  }
  if (role !== '') {
    ctx.systemPrompt.section({
      name: 'houmao:managed-role', order: 0, text: role, interpolate: false,
    });
  }
  if (control.service !== undefined) {
    applyService(ctx, control, role);
    return;
  }
  const evidence = openSync(control.evidence_path, 'ax', 0o600);
  const incarnation = randomUUID();
  const agents = new WeakMap();
  const descendants = new Map();
  let root;
  let inputId;
  let binding;
  let sequence = 0;
  let closed = false;

  /** Write durable metadata only; input and role bytes never enter this channel. */
  const record = (event, agent, fields = {}) => {
    const row = {
      version: 1, event, sequence: sequence++, attempt_id: control.attempt_id,
      runtime_session_id: control.runtime_session_id, generation: control.generation,
      process_id: process.pid, host_incarnation: incarnation,
      native_session_id: agent?.session.id ?? null,
      agent_incarnation: agent === undefined ? null : agents.get(agent),
      ...fields,
    };
    writeSync(evidence, `${JSON.stringify(row)}\n`);
    fsyncSync(evidence);
  };
  ctx.on('dispose', () => {
    if (!closed) {
      closed = true;
      closeSync(evidence);
    }
  });
  record('loaded', undefined, {
    role_sha256: createHash('sha256').update(role).digest('hex'), role_bytes: Buffer.byteLength(role),
  });

  ctx.on('agent/created', ({ agent, source }) => {
    agents.set(agent, randomUUID());
    if (agent.session.header.origin === 'subagent') {
      const parent = agent.session.header.parentSession;
      if (root !== undefined && (parent === root.session.id || descendants.has(parent))) {
        descendants.set(agent.session.id, parent);
        record('descendant/created', root, {
          child_session_id: agent.session.id, parent_session_id: parent, local: true,
        });
      }
      return;
    }
    if (root !== undefined && root !== agent) {
      throw new Error('Houmao DSH companion supports one native root per process');
    }
    if (control.expected_native_session_id !== null
        && agent.session.id !== control.expected_native_session_id) {
      throw new Error('Houmao DSH native session binding does not match');
    }
    root = agent;
    const abandoned = new Set(control.abandoned_message_ids);
    const pending = [...agent.inbox.nextTurn, ...agent.inbox.nextStep];
    if (pending.some(message => !abandoned.has(message.id))) {
      record('unreconciled', agent, { pending_count: pending.length });
      throw new Error('Houmao DSH resume refused: unidentified pending input');
    }
    for (const message of pending) {
      if (!agent.inbox.remove(message.id)) {
        throw new Error('Houmao DSH resume refused: pending input changed during reconciliation');
      }
      record('reconciled', agent, { message_id: message.id });
    }
    record('created', agent, { source });
    if (control.one_shot !== undefined) {
      binding = Object.fromEntries([
        'version', 'attempt_id', 'runtime_session_id', 'generation', 'working_directory',
        'process_id', 'process_birth_token', 'evidence_path', 'persistence_root', 'source_revision',
      ].map(key => [key, control[key]]));
      binding.native_session_id = agent.session.id;
      const artifactRoot = control.evidence_path.slice(0, control.evidence_path.lastIndexOf('/'));
      writeBinding(`${artifactRoot}/dsh-native-binding.json`, binding);
      const followup = agent.followup.bind(agent);
      agent.followup = message => {
        if (message.source.kind === 'user') {
          if (inputId !== undefined) throw new Error('Houmao DSH attempt allows one user input');
          requireOneShotPermission(control);
          inputId = message.id;
        }
        // Followup synchronously appends the inbox splice before it emits inserted.
        return followup(message);
      };
    }
  });
  ctx.on('agent/inbox/inserted', ({ agent, message }) => {
    if (agent === root && message.source.kind === 'user') {
      if (control.one_shot !== undefined && inputId !== message.id) {
        throw new Error('Houmao DSH input did not cross the native permission boundary');
      }
      record('admitted', agent, { message_id: message.id });
      if (control.one_shot !== undefined) {
        const artifactRoot = control.evidence_path.slice(0, control.evidence_path.lastIndexOf('/'));
        writeBinding(control.one_shot.session_path, binding);
        writeBinding(`${artifactRoot}/dsh-native-handoff.json`, binding);
      }
    }
  });
  ctx.on('agent/inbox/claimed', ({ agent, message, turn }) => {
    if (agent === root) record('claimed', agent, { message_id: message.id, turn });
  });
  ctx.on('session/event', (session, event) => {
    if (root?.session !== session) {
      if (root !== undefined && descendants.has(session.id)
          && (event.type === 'turn/start' || event.type === 'turn/end')) {
        record(`descendant/${event.type}`, root, {
          child_session_id: session.id, parent_session_id: descendants.get(session.id),
          turn: event.data.turn, native_sequence: event.seq,
        });
      }
      return;
    }
    if (event.type === 'turn/start' || event.type === 'turn/end') {
      record(event.type, root, {
        turn: event.data.turn, native_sequence: event.seq,
        ...(event.type === 'turn/end' ? { reason: {kind: event.data.reason.kind} } : {}),
      });
    }
  });
  ctx.on('subagent/start', (info) => {
    if (root === undefined
        || !(info.parentSessionId === root.session.id || descendants.has(info.parentSessionId))) return;
    if (!descendants.has(info.id)) {
      descendants.set(info.id, info.parentSessionId);
      record('descendant/created', root, {
        child_session_id: info.id, parent_session_id: info.parentSessionId, local: info.local,
      });
    }
  });
  ctx.on('agent/disposed', ({ agent }) => {
    if (agent === root) record('disposed', agent);
  });
}

/** Arm each ACP prompt independently while keeping one native body alive. */
function applyService(ctx, control, role) {
  const service = control.service;
  if (['manifest_path', 'arm_path', 'python_executable', 'turn_root'].some(key =>
    typeof service?.[key] !== 'string' || !isAbsolute(service[key]))) {
    throw new Error('Houmao DSH service ownership is unavailable');
  }
  const host = randomUUID();
  const agent = randomUUID();
  let root;
  let active;

  const record = (operation, event, fields = {}) => {
    writeSync(operation.stream, `${JSON.stringify({
      ...operation.binding, event, sequence: operation.sequence++, ...fields,
    })}\n`);
    fsyncSync(operation.stream);
  };

  ctx.on('dispose', () => { if (active !== undefined) closeSync(active.stream); });
  ctx.on('agent/created', ({ agent: created }) => {
    if (created.session.header.origin === 'subagent') {
      const parent = created.session.header.parentSession;
      if (active !== undefined && (parent === root.session.id || active.children.has(parent))) {
        if (!active.children.has(created.session.id)) {
          active.children.set(created.session.id, parent);
          record(active, 'descendant/created', {
            child_session_id: created.session.id, parent_session_id: parent, local: true,
          });
        }
      }
      return;
    }
    if (root !== undefined
        || (control.expected_native_session_id !== null
            && control.expected_native_session_id !== created.session.id)
        || created.inbox.nextTurn.length !== 0 || created.inbox.nextStep.length !== 0) {
      throw new Error('Houmao DSH service could not bind an idle exact native session');
    }
    root = created;
    writeBinding(control.evidence_path, {
      version: 1, service_incarnation: control.attempt_id, generation: control.generation,
      runtime_session_id: control.runtime_session_id, native_session_id: root.session.id,
      process_id: process.pid, host_incarnation: host, agent_incarnation: agent,
      role_sha256: createHash('sha256').update(role).digest('hex'),
    });
    const followup = root.followup.bind(root);
    root.followup = message => {
      if (message.source.kind === 'user') {
        const arm = JSON.parse(readFileSync(service.arm_path, 'utf8'));
        if (typeof arm.request_id !== 'string' || !arm.request_id
            || arm.request_id === '.' || arm.request_id === '..' || arm.request_id.includes('/')
            || arm.request_id === active?.binding.attempt_id
            || arm.generation !== control.generation || arm.service_incarnation !== control.attempt_id
            || arm.native_session_id !== root.session.id || arm.process_id !== process.pid) {
          throw new Error('Houmao DSH service prompt is unarmed or no longer current');
        }
        const verified = spawnSync(service.python_executable, [
          '-m', 'houmao.agents.realm_controller.backends.dsh_acp_service',
          '--verify-native-arm', service.arm_path, service.manifest_path, control.generation,
          control.attempt_id, arm.request_id, root.session.id, String(process.pid),
        ], { stdio: 'ignore', timeout: 5000 });
        const current = JSON.parse(readFileSync(service.arm_path, 'utf8'));
        const directory = join(service.turn_root, arm.request_id);
        const guard = JSON.parse(readFileSync(join(directory, '.dispatch-permission.json'), 'utf8'));
        if (verified.status !== 0 || current.nonce !== arm.nonce || current.expires_at <= Date.now() / 1000
            || guard.active !== true || guard.expires_at <= Date.now() / 1000
            || guard.attempt_id !== arm.request_id || guard.registry_generation_id !== control.generation
            || guard.manifest_path !== service.manifest_path) {
          throw new Error('Houmao DSH service prompt permission was revoked');
        }
        const binding = {
          version: 1, attempt_id: arm.request_id, service_incarnation: control.attempt_id,
          runtime_session_id: control.runtime_session_id, generation: control.generation,
          native_session_id: root.session.id, process_id: process.pid,
          process_birth_token: arm.process_birth_token, host_incarnation: host,
          agent_incarnation: agent, working_directory: control.working_directory,
          persistence_root: control.persistence_root, source_revision: control.source_revision,
        };
        const stream = openSync(join(directory, 'dsh-native-evidence.jsonl'), 'ax', 0o600);
        if (active !== undefined) closeSync(active.stream);
        active = { directory, binding, stream, input: message.id, sequence: 0,
          children: new Map(), flush: Promise.resolve() };
        writeBinding(join(directory, 'dsh-native-binding.json'), binding);
      }
      return followup(message);
    };
  });
  ctx.on('agent/inbox/inserted', ({ agent: subject, message }) => {
    if (subject !== root || message.source.kind !== 'user' || active === undefined) return;
    if (active.input !== message.id) throw new Error('Unbound DSH service inbox mutation');
    record(active, 'admitted', { message_id: message.id });
    writeBinding(join(active.directory, 'dsh-native-handoff.json'), active.binding);
  });
  ctx.on('agent/inbox/claimed', ({ agent: subject, message, turn }) => {
    if (subject === root && active !== undefined) record(active, 'claimed', { message_id: message.id, turn });
  });
  ctx.on('session/event', (session, event) => {
    const operation = active;
    if (operation === undefined || (event.type !== 'turn/start' && event.type !== 'turn/end')) return;
    const fields = { turn: event.data.turn, native_sequence: event.seq };
    if (session !== root.session) {
      const parent = operation.children.get(session.id);
      if (parent !== undefined) record(operation, `descendant/${event.type}`, {
        ...fields, child_session_id: session.id, parent_session_id: parent,
      });
      return;
    }
    if (event.type === 'turn/start') {
      record(operation, event.type, fields);
      return;
    }
    const reason = event.data.reason.kind;
    record(operation, event.type, { ...fields, reason: { kind: reason } });
    operation.flush = operation.flush.then(async () => {
      const sessions = ctx.get('sessions');
      if (sessions === undefined) throw new Error('DSH session flush is unavailable');
      await sessions.flush(session);
      writeBinding(join(operation.directory, 'dsh-native-flush.json'), {
        ...operation.binding, ...fields, reason, status: 'flushed',
      });
    }).catch(() => {
      writeBinding(join(operation.directory, 'dsh-native-flush.json'), {
        ...operation.binding, ...fields, reason, status: 'failed',
      });
    });
  });
  ctx.on('subagent/start', info => {
    if (active === undefined || !(info.parentSessionId === root.session.id || active.children.has(info.parentSessionId))) return;
    if (!active.children.has(info.id)) {
      active.children.set(info.id, info.parentSessionId);
      record(active, 'descendant/created', { child_session_id: info.id, parent_session_id: info.parentSessionId, local: info.local });
    }
  });
}
