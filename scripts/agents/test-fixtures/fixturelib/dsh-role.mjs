/** Add the selected literal role to a direct DSH fixture. */

import { readFileSync } from 'node:fs';

export const name = 'houmao-fixture-role';
export const inject = ['systemPrompt'];

export function apply(ctx, config) {
  const text = readFileSync(config.roleFile, 'utf8');
  if (text) {
    ctx.systemPrompt.section({ name: 'houmao:fixture-role', order: 0, text, interpolate: false });
  }
}
