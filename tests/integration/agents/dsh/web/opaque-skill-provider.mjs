/** An intentionally unqualified native provider, including cached empty state. */
export const name = 'qualification-opaque-skill-provider';
export const inject = ['skills'];
export function apply(ctx, config) {
  ctx.skills.registerProvider(() => ({
    name: 'qualification-opaque',
    async list() {
      return {complete: true, candidates: config.empty ? [] : [{
        name: 'opaque', description: 'Unqualified source', source: 'runtime',
        provider: 'qualification-opaque', rank: 1,
        invocation: {modelInvocable: true, userInvocable: true}, locator: null,
      }]};
    },
    async get(candidate) { return {...candidate, content: 'Private body must not be queried'}; },
  }));
}
