# Proposal

## Why

The default system prompt header rendered into `<houmao_system_prompt>` packs unindented XML blocks and dense specification prose without visual spacing, making its operating rules slow for operators and models to parse. In `<houmao_runtime_guidance>`, generic wording about bundled guidance also fails to tell agents to consult installed `houmao-*` skills (particularly entrypoint skills) first before running `houmao-mgr` commands.

## What Changes

- Reformat `<houmao_system_prompt>` rendering in `src/houmao/agents/managed_prompt_header.py` to separate container and sibling XML blocks with blank lines while preserving `HOUMAO_SYSTEM_PROMPT_LAYOUT_VERSION = 1`, all existing XML tag names, and all `--managed-header-section` policy identifiers.
- Rewrite the six `<managed_header>` subsections (`identity`, `memo-cue`, `houmao-runtime-guidance`, `automation-notice`, `task-reminder`, and `mail-ack`) with consistent `Key: value` fields, separated read/write or branch bullets, and direct plain-English imperatives that preserve every existing behavioral rule.
- Update `<houmao_runtime_guidance>` to use an ordered sequence for Houmao-related actions: look for installed `houmao-*` skills (especially entrypoint skills) for guidance first, execute through `houmao-mgr` and supported Houmao manifests or service APIs second, and avoid ad hoc probing of `tmux` state or internal files.
- Increment `MANAGED_PROMPT_HEADER_VERSION` from `1` to `2` in persisted `managed_prompt_header` build metadata so manifests record the revised header prose provenance.
- Update unit tests and managed-header documentation (`docs/reference/run-phase/managed-prompt-header.md` and `docs/getting-started/launch-profiles.md`) to match the revised prompt text, formatting, skill-first guidance order, and header version.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `managed-launch-prompt-header`: Require readable blank-line block separation, structured plain-English section prose, `MANAGED_PROMPT_HEADER_VERSION = 2` metadata provenance, and explicit skill-first guidance (`houmao-*` skills, particularly entrypoint skills, before `houmao-mgr`) in `<houmao_runtime_guidance>`.
- `docs-managed-launch-prompt-header-reference`: Update reference documentation requirements to reflect `MANAGED_PROMPT_HEADER_VERSION = 2`, the revised structured prompt example, and the `houmao-*` entrypoint-skill-first runtime guidance rule.

## Impact

- **Runtime prompt composition**: `src/houmao/agents/managed_prompt_header.py` (`MANAGED_PROMPT_HEADER_VERSION`, `_render_prompt_section`, `render_managed_prompt_header`, and all six section builders).
- **Compatibility**: Preserves `<houmao_system_prompt version="1">`, all XML section tags, CLI flags (`--managed-header`, `--no-managed-header`, `--managed-header-section`), and stored launch-profile schemas; only rendered prompt whitespace/prose and `inputs.managed_prompt_header.version` change.
- **Tests and documentation**: `tests/unit/agents/test_managed_prompt_header.py`, `tests/unit/srv_ctrl/commands/test_agents_core.py`, `tests/unit/docs/test_managed_memory_docs.py`, `docs/reference/run-phase/managed-prompt-header.md`, `docs/getting-started/launch-profiles.md`, and `docs/getting-started/managed-memory-dirs.md`.
