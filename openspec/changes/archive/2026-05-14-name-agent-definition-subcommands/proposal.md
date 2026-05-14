## Why

`houmao-agent-definition` now routes several distinct authoring lanes, but the entry page names them as descriptive branches instead of stable skill subcommands. Users and invoking agents need concise handles they can name explicitly, and the default meaning of "profile" should match the easy-profile path that users usually intend.

## What Changes

- Add explicit user-facing subcommand names to `houmao-agent-definition/SKILL.md` for every branch.
- Make `profiles` mean specialist-backed easy profiles by default, even when the user says "launch profile" without raw/recipe-backed context.
- Rename the low-level recipe-backed launch-profile lane to the skill subcommand `raw-profiles`, while documenting that it still uses the underlying `houmao-mgr project agents launch-profiles ...` CLI.
- Rename the ready-profile lane to `create-agent-fast-forward`, describing it as a composed specialist-to-easy-profile authoring shortcut that does not launch a live agent.
- Update compatibility and documentation text that currently says ready profile, ready-profile generation, or launch profile where the new subcommand terminology is needed.
- Review old generic `actions/*` pages under `houmao-agent-definition` and either route them through the new subcommand names or clearly mark them as legacy low-level-only references.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-manage-agent-definition-skill`: Require explicit skill subcommands, default profile routing to easy profiles, `raw-profiles` for low-level recipe-backed profiles, and `create-agent-fast-forward` for the composed one-pass easy authoring workflow.
- `houmao-agent-ready-profile-workflow`: Rename the user-facing ready-profile workflow to `create-agent-fast-forward` while preserving its create/select specialist, create/update easy profile, print launch command, and do-not-launch behavior.
- `houmao-create-specialist-credential-sources`: Update credential-routing terminology so credential discovery applies to specialist creation and the specialist-create step inside `create-agent-fast-forward`.
- `houmao-create-specialist-skill`: Update compatibility wrapper terminology for the renamed fast-forward path.
- `houmao-mgr-system-skills-cli`: Update system-skill list/status expectations so descriptions name the new subcommands where relevant.
- `houmao-system-skill-installation`: Update packaged skill catalog expectations so the canonical skill advertises subcommand-based routing.
- `docs-cli-reference`: Update CLI reference skill prose to use `profiles`, `raw-profiles`, and `create-agent-fast-forward` terminology.
- `docs-readme-system-skills`: Update README system-skill prose expectations for the new terminology.
- `docs-system-skills-overview-guide`: Update the system-skills overview routing guidance for default easy-profile behavior and raw-profile escape hatch.
- `readme-structure`: Update the README skill table expectations for the renamed one-pass profile preparation path.

## Impact

- Affected skill files: `src/houmao/agents/assets/system_skills/houmao-agent-definition/**`, `houmao-specialist-mgr`, and neighboring skills that reference profile or ready-profile routing.
- Affected documentation: README system-skill table, getting-started system-skill overview, and CLI reference pages.
- Affected specs: OpenSpec requirements for the unified agent-definition skill, fast-forward easy-profile workflow, credential-source routing, system-skill catalog/listing docs, and README/docs descriptions.
- No CLI command rename is required; this change is about skill invocation terminology and routing guidance over existing maintained `houmao-mgr` surfaces.
