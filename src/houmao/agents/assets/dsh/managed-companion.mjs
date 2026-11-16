/** Native DSH role projection and payload-free managed admission evidence. */

import { createHash, randomUUID } from 'node:crypto';
import { closeSync, fsyncSync, openSync, readFileSync, writeSync } from 'node:fs';
import { isAbsolute } from 'node:path';

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
  return control;
}

/** Register an additive literal role and observe one exclusively owned ACP root. */
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
  const evidence = openSync(control.evidence_path, 'ax', 0o600);
  const incarnation = randomUUID();
  const agents = new WeakMap();
  const descendants = new Map();
  let root;
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
      throw new Error('Houmao ACP companion supports one native root per process');
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
  });
  ctx.on('agent/inbox/inserted', ({ agent, message }) => {
    if (agent === root && message.source.kind === 'user') {
      record('admitted', agent, { message_id: message.id });
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
