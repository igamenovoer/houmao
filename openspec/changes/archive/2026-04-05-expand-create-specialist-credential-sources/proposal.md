## Why

The packaged `houmao-create-specialist` skill currently models only explicit auth input, credential-bundle reuse, and one narrow `auto credentials` path. That is too limited for deployed hosts, where users may want to point the agent at specific env vars, a specific directory, or a tool-specific automatic lookup flow, and where fixture-only repository paths do not exist.

## What Changes

- Expand `houmao-create-specialist` so credential sourcing is modeled as four explicit modes: fully explicit auth input, user-directed env lookup, user-directed directory scan, and tool-specific auto discovery.
- Add separate tool-specific credential lookup reference pages for Claude, Codex, and Gemini instead of embedding all lookup details inside the main skill body.
- Require those reference pages to describe deployment-realistic credential locations and selectors using official tool documentation, `extern/orphan` upstream source, and direct executable inspection, without assuming `tests/fixtures/agents` or similar repository-only paths exist on the host.
- Require the skill to map discovered credentials only into auth inputs that `houmao-mgr project easy specialist create` can actually express, and to report unsupported current auth shapes instead of guessing.

## Capabilities

### New Capabilities
- `houmao-create-specialist-credential-sources`: Defines the credential-source modes, per-tool lookup references, deployment-safe discovery rules, and importability limits for the packaged `houmao-create-specialist` system skill.

### Modified Capabilities

## Impact

- `src/houmao/agents/assets/system_skills/houmao-create-specialist/SKILL.md`
- New tool-specific reference pages under `src/houmao/agents/assets/system_skills/houmao-create-specialist/`
- Skill-content regression coverage in `tests/unit/agents/test_system_skills.py`
- Related user-facing docs if they describe the skill’s credential lookup behavior
