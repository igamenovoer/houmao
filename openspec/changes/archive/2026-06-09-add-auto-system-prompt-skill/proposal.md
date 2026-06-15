## Why

Some supported CLI tools, including Kimi's public CLI surface, do not expose a native per-launch system-prompt option. The current bootstrap-message fallback is visible as ordinary chat and does not reliably reload after context compaction, while memo injection does not help because the agent has no native reason to read `houmao-memo.md`.

## What Changes

- Add a Houmao-owned auto-skill lane under `src/houmao/agents/assets/auto_skills`.
- Package an auto-injected `houmao-auto-system-prompt` skill for managed agents whose tool lacks native system-prompt support but exposes skill metadata in the tool's native startup context.
- Add a read-only `houmao-mgr agents self system-prompt show --format text` command that returns the effective Houmao system prompt for the current managed agent.
- Extend launch policy so known non-native, skill-visible tools use the auto-skill system-prompt bootstrap instead of chat bootstrap messages.
- Project auto skills into managed homes independently from user skills, private skills, and installable Houmao system skills.
- Record auto-skill projection provenance without claiming the system prompt was applied merely because the skill was projected.
- Reject managed launches with a role/system prompt when a tool supports neither native system prompts nor reliable startup-visible skills, unless a future explicit override is added.

## Capabilities

### New Capabilities

- `managed-agent-auto-skills`: Covers Houmao-owned auto skills that are injected by managed launch for provider bootstrap behavior and are not user-installable system skills.

### Modified Capabilities

- `brain-launch-runtime`: Managed brain construction and runtime role injection select and project auto skills when needed.
- `versioned-launch-policy-registry`: Launch policy capability metadata distinguishes native system prompts, startup-visible skills, and unsupported fallback cases.
- `houmao-mgr-agents-scope-cli`: The current-agent CLI exposes the effective managed system prompt through a read-only self command.
- `houmao-system-skill-installation`: System-skill installation remains separate from auto-skill injection and user system-skill policy does not disable auto skills.

## Impact

- Affected runtime code includes brain construction, role-injection planning, Kimi skill discovery wiring, managed-agent manifests, and `houmao-mgr agents self` commands.
- Affected assets include a new packaged auto-skill root and the `houmao-auto-system-prompt` skill.
- Affected tests include unit coverage for projection, launch-policy selection, CLI prompt retrieval, collision handling, and Kimi skill-dir configuration.
- No external Python dependency is required.
