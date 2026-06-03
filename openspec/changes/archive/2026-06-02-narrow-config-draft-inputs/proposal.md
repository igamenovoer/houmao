## Why

The first config-draft change made YAML output much smaller than command templates, but the draft inputs still mirror too much of the full create/set command surface. Config drafts should be opinionated partial applications of Houmao's config models: a draft id binds many model fields to fixed values and exposes only a minimal set of holes, including credential, while users who need full model coverage should use the maintained project subcommands directly.

## What Changes

- Narrow each initial config draft so it accepts only the deliberately exposed minimal input fields for that draft id.
- Require credential as an explicit input where a generated draft references a credential-bearing specialist/profile path instead of deriving or exposing credential material implicitly.
- Treat draft ids as opinionated model binders: fixed values may be defaults or draft-specific non-default choices, and they are not supplied by the caller.
- Reject full-model optional override fields that are not part of the draft's minimal exposed input set.
- Keep generated YAML concise and concrete, with no command-template schema metadata and no broad optional override catalog.
- **BREAKING**: Existing `internals config-drafts generate` callers that pass optional override fields such as model, env, mailbox, skills, prompt overlay, memo seed, gateway, or credential material will receive unsupported-field blockers unless those fields are explicitly part of the narrowed draft contract.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-mgr-config-drafts`: Narrow config-draft inputs to opinionated, minimal holes; require credential as an explicit draft input; reject hidden full-model fields instead of copying them into generated YAML.

## Impact

- Affected CLI behavior: `houmao-mgr internals config-drafts list|generate` required/accepted intent keys and blocker messages.
- Affected implementation: `src/houmao/srv_ctrl/config_drafts/` draft registry, validation, and project agent draft generators.
- Affected tests: config-draft registry inventory, YAML shape tests, unsupported-field blockers, CLI list/generate behavior, and packaged skill text guidance.
- Affected system skills: `houmao-agent-definition` and related subskills should describe config drafts as minimal opinionated drafts and direct full customization back to maintained project subcommands.
