/** Test-only barriers around actual native preparation, steps and maintenance. */
import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';
import { randomUUID } from 'node:crypto';
export const name = 'houmao-native-web-qualification-gates';
export const inject = ['attachments', 'agents', 'connection'];
export function apply(ctx, config) {
  const file = name => `${config.directory}/${name}`;
  const guest = ctx.connection.createPeer({principal: {kind: 'qualification-guest'}, interactions: 'none'});
  const admit = ctx.connection.admit.bind(ctx.connection);
  ctx.connection.admit = request => {
    const original = admit(request);
    return 'peer' in original && request.headers['x-qualification-principal'] === 'guest' ? {peer: guest} : original;
  };
  const matches = (name, text) => existsSync(file(`${name}.request`)) && readFileSync(file(`${name}.request`), 'utf8') === text;
  const wait = async name => {
    writeFileSync(file(`${name}.entered`), 'entered');
    appendFileSync(file(`${name}.count`), 'entered\n');
    while (!existsSync(file(`${name}.release`))) await delay(10);
  };
  const prepare = ctx.attachments.admitPromptContent.bind(ctx.attachments);
  ctx.attachments.admitPromptContent = async content => {
    if (content.some(part => part.type === 'text' && matches('prepare', part.text))) await wait('prepare');
    return prepare(content);
  };
  ctx.on('agent/created', ({agent}) => {
    const maintain = agent.runMaintenance.bind(agent);
    agent.runMaintenance = job => maintain(async signal => {
      const value = await job(signal);
      if (existsSync(file('settlement.entered')) && !existsSync(file('settlement.release'))) await wait('settlement');
      return value;
    });
    const timer = setInterval(() => {
      if (existsSync(file('unknown.request')) && !existsSync(file('unknown.entered'))) {
        Object.defineProperty(agent.inbox, 'hasPending', {get: () => undefined, configurable: true});
        writeFileSync(file('unknown.entered'), 'entered');
      }
      if (existsSync(file('pending.request')) && !existsSync(file('pending.entered'))) {
        agent.inject({id: randomUUID(), role: 'user', source: {kind: 'user'}, content: [{type: 'text', text: readFileSync(file('pending.request'), 'utf8')}]});
        writeFileSync(file('pending.entered'), 'entered');
      }
      if (!existsSync(file('maintenance.request')) || existsSync(file('maintenance.entered'))) return;
      try { void maintain(() => wait('maintenance')); } catch {}
    }, 10);
    agent.ctx.effect(() => () => clearInterval(timer));
  });
  ctx.on('agent/inbox/inserted', ({message}) => {
    if (message.content?.some(part => part.type === 'text' && matches('settlement', part.text))) writeFileSync(file('settlement.entered'), 'entered');
  });
  ctx.on('agent/pre-step', async ({messages}, next) => {
    if (messages.some(message => message.content.some(part => part.type === 'text' && matches('step', part.text)))) await wait('step');
    return next();
  });
}
