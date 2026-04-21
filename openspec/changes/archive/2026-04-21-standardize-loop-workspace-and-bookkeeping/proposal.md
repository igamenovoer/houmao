## Why

`houmao-agent-loop-pairwise-v2` has a strong control-plane and recovery model, but it still leaves workspace posture outside the authored run contract. Users need a newer pairwise skill that can either use a standardized Houmao workspace or honor a user-provided custom workspace without forcing both concerns into the same skill surface.

## What Changes

- Add a new packaged skill `houmao-agent-loop-pairwise-v3` as an extension of pairwise-v2.
- Give pairwise-v3 a first-class workspace contract with two modes:
  - `standard`, which uses Houmao's standardized workspace posture
  - `custom`, which records user-provided paths and rules directly in the loop plan
- Define standard in-repo workspace posture for pairwise-v3 as task-scoped under `houmao-ws/<task-name>/...` so one repository can host multiple concurrent teams without path or branch collisions.
- Keep `houmao-utils-workspace-mgr` as the standard workspace-preparation skill only. It does not gain a custom-workspace mode; users who do not want the standard Houmao workspace simply do not invoke it.
- Keep pairwise-v3 recovery boundaries aligned with pairwise-v2: runtime-owned recovery files remain Houmao-managed state, not user-authored bookkeeping.
- Update loop authoring docs and packaged system-skill installation/catalog expectations so pairwise-v3 is presented as the workspace-aware extension of pairwise-v2.

## Capabilities

### New Capabilities

- `houmao-agent-loop-pairwise-v3-skill`: packaged pairwise-v3 skill that extends v2 with authored workspace contracts, including standard and custom workspace modes and standardized task-scoped in-repo posture.

### Modified Capabilities

- `houmao-utils-workspace-mgr-skill`: keep the workspace manager standard-only while redefining standard in-repo workspaces as task-scoped under `houmao-ws/<task-name>/`.
- `houmao-system-skill-installation`: package and install `houmao-agent-loop-pairwise-v3` as a current Houmao-owned system skill alongside the existing pairwise variants.
- `docs-loop-authoring-guide`: explain when to use pairwise-v2 versus pairwise-v3 and document pairwise-v3 standard/custom workspace modes plus task-scoped in-repo posture.

## Impact

- New packaged skill assets under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v3/`.
- Packaged workspace-manager skill assets under `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/`, especially the in-repo flavor guidance and naming rules.
- Packaged system-skill catalog and install/docs surfaces that enumerate current loop skills.
- Loop authoring docs, templates, and references that currently stop at pairwise-v2 and do not describe a workspace-aware pairwise successor.
- No runtime engine replacement is required in this change; the main deliverable is a new packaged skill plus aligned workspace-manager and documentation contracts.
