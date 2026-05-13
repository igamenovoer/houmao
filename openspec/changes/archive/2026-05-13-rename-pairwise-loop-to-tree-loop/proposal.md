## Why

The loop skill family currently uses "pairwise loop" for tree-shaped local-close execution, but that name hides the actual topology rule and now conflicts with the broader `houmao-agent-loop-pro` topology model. Using "tree loop" as the canonical name makes the distinction from "generic loop" clearer while preserving `pairwise loop` as an alias for existing users and package names.

## What Changes

- Make `tree loop` the canonical user-facing name for tree/forest-shaped local-close loop execution.
- Preserve `pairwise loop`, `pairwise-tree`, `pairwise-only`, and existing `houmao-agent-loop-pairwise*` skill names as compatibility aliases.
- Make `generic loop` the canonical user-facing name for directed graph loop execution; keep `generic graph` and `generic-graph` as compatibility aliases where existing artifacts may use them.
- In `houmao-agent-loop-pro`, prefer machine topology values `tree-loop` and `generic-loop` for newly generated artifacts while accepting legacy values `pairwise-tree` and `generic-graph`.
- Rename explanatory references to the elemental two-agent pattern from `pairwise edge-loop` toward `local-close edge loop`, while keeping old pattern filenames and alias wording for compatibility.
- Update loop-related system skills and touring/advanced-usage guidance so skill-invoked agents ask and explain in terms of `tree loop` versus `generic loop`.
- No breaking package, CLI, skill-directory, or invocation-name changes.

## Capabilities

### New Capabilities
- `houmao-loop-terminology`: Canonical loop terminology and alias compatibility rules across Houmao system skills.

### Modified Capabilities
- `houmao-agent-loop-pairwise-skill`: Stable pairwise-named skill presents tree loop terminology while preserving explicit skill-name activation.
- `houmao-agent-loop-pairwise-v2-skill`: Versioned enriched pairwise-named skill presents tree loop terminology while preserving pairwise aliases.
- `houmao-agent-loop-pairwise-v3-skill`: Workspace-aware pairwise-named skill presents tree loop terminology while preserving pairwise aliases.
- `houmao-agent-loop-pairwise-v4-skill`: Template-driven workspace-aware pairwise-named skill presents tree loop terminology while preserving pairwise aliases.
- `houmao-agent-loop-pairwise-v5-skill`: Generated-execplan skill uses tree loop naming in user-facing guidance while preserving `houmao-agent-loop-pairwise-v5` as the skill name.
- `houmao-agent-loop-generic-skill`: Generic loop skill presents `generic loop` as canonical and treats older graph wording as alias wording.
- `houmao-adv-usage-pattern-skill`: Elemental pairwise edge pattern is described as local-close edge loop behavior while preserving compatibility references.
- `houmao-touring-skill`: Guided touring presents tree loop and generic loop as the main loop families while preserving pairwise skill aliases.

## Impact

- Affects Markdown and YAML under `src/houmao/agents/assets/system_skills/`.
- Affects OpenSpec requirements for the loop-related system-skill capabilities listed above.
- Does not rename packaged skill directories, frontmatter `name` values, CLI commands, generated runtime paths, or installed skill handles.
- Does not change Houmao runtime behavior, mailbox behavior, gateway behavior, workspace management, or generated execplan mechanics beyond preferred terminology and accepted topology-mode aliases.
