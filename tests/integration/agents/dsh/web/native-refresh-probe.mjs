/** Controlled native-result/finally barriers; never shipped with the product. */
import { existsSync, writeFileSync } from 'node:fs';
import { setTimeout as delay } from 'node:timers/promises';
export const name = 'qualification-common-refresh';
export const inject = ['agents'];
export async function apply(ctx, config) {
  if (config.mode === 'observation-gate') ctx.on('agent/created', () => {
    const registry = ctx.get('skills');
    const snapshot = registry.snapshot.bind(registry);
    registry.snapshot = async options => {
      if (existsSync(`${config.directory}/observation.request`) && !existsSync(`${config.directory}/observation.release`)) {
        writeFileSync(`${config.directory}/observation.entered`, 'entered');
        while (!existsSync(`${config.directory}/observation.release`)) await delay(10);
      }
      return snapshot(options);
    };
  });
  const prior = ctx.get('hmr');
  if (prior) throw new Error('Controlled result shim expects the configuration-only fixture profile');
  ctx.provide('hmr', {
    async runExclusive(operation) {
      if (config.mode === 'lockbusy') while (!existsSync(`${config.directory}/reload.release`)) await delay(10);
      const pending = operation();
      writeFileSync(`${config.directory}/reload.entered`, 'entered');
      if (['gate', 'gate-child'].includes(config.mode)) while (!existsSync(`${config.directory}/reload.release`)) await delay(10);
      const result = await pending;
      if (config.mode === 'unready') {
        ctx.agents.list()[0].model.current = () => undefined;
        throw new Error('Synthetic invalid native readiness');
      }
      if (config.mode === 'failed') throw new Error('Synthetic native failure after actual profile apply');
      return {...result, pending: config.mode === 'pending' ? [{reason: 'host-module'}] : []};
    },
  });
  if (['child', 'gate-child'].includes(config.mode)) {
    let child;
    const timer = setInterval(async () => {
      if (child || !existsSync(`${config.directory}/child.request`)) return;
      clearInterval(timer);
      try {
        child = await ctx.agents.create({sessionId: 'qualification-child', meta: {cwd: config.directory}});
        writeFileSync(`${config.directory}/child.entered`, 'entered');
      } catch {
        writeFileSync(`${config.directory}/child.refused`, 'refused');
      }
    }, 10);
    ctx.effect(() => async () => { clearInterval(timer); await child?.dispose(); });
  }
}
