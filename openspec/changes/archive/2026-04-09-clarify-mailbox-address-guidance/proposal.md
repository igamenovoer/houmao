## Why

The mailbox protocol already defines ordinary managed-agent mailbox addresses as `<agentname>@houmao.localhost` and reserves `HOUMAO-*` mailbox local parts under `houmao.localhost` for Houmao-owned system principals. But mailbox account creation guidance, touring examples, and one late mailbox-binding path still expose older `HOUMAO-...@agents.localhost` patterns, so operators and packaged skills receive conflicting guidance at the moment mailbox identities are chosen.

We need one consistent mailbox account creation contract so omitted-address defaults, packaged skill guidance, and onboarding examples all point users toward the same ordinary address pattern while preserving the existing `HOUMAO-<agentname>` principal-id model.

## What Changes

- Align late filesystem mailbox binding defaults with the existing Houmao mailbox address policy so omitted addresses derive `<agentname>@houmao.localhost` while canonical principal ids remain `HOUMAO-<agentname>`.
- Teach `houmao-mailbox-mgr` that `HOUMAO-*` mailbox local parts are reserved under `houmao.localhost` and that `houmao.localhost` is the recommended domain when the user has not specified one.
- Teach `houmao-touring` mailbox-setup prompts to use `research@houmao.localhost` plus `HOUMAO-research` examples and to explain the reserved-prefix rule when asking mailbox questions.
- Update affected onboarding, CLI, and mailbox-reference examples so mailbox account creation guidance no longer teaches `HOUMAO-...@agents.localhost` as the ordinary managed-agent pattern.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime`: define the omitted-address default for late filesystem mailbox binding in terms of the ordinary Houmao mailbox address policy.
- `houmao-mailbox-mgr-skill`: require mailbox-admin guidance to explain the reserved `HOUMAO-*` local-part rule and the recommended `houmao.localhost` domain.
- `houmao-touring-skill`: require mailbox-setup prompts and examples to distinguish mailbox address from principal id and to explain the reserved-prefix rule.

## Impact

- Affected runtime path: late filesystem mailbox binding for existing managed agents, especially the omitted-address path used by `houmao-mgr agents mailbox register`.
- Affected packaged skills: `src/houmao/agents/assets/system_skills/houmao-mailbox-mgr/**` and `src/houmao/agents/assets/system_skills/houmao-touring/**`.
- Affected docs: mailbox account creation examples in getting-started, CLI, and mailbox-reference pages that still use `agents.localhost` or `HOUMAO-...` as the ordinary mailbox-address pattern.
- Existing explicit mailbox bindings remain valid; this change focuses on defaults, guidance, and consistency for ordinary managed-agent mailbox creation.
