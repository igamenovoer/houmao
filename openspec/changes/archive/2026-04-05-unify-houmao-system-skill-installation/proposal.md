## Why

Houmao currently installs its runtime-owned `houmao-*` skills through mailbox-specific logic that is separate from project starter assets and separate from any operator-facing installation workflow. That makes managed-agent launch and joined-session adoption depend on ad hoc code paths, and it leaves external agents without a supported way to install the current Houmao-owned skills into their own tool homes before using `houmao-mgr`.

## What Changes

- Package the current Houmao-owned `houmao-*` skills under one maintained source asset root in `src/.../assets` without introducing new skills in this change.
- Add one packaged skill catalog with an explicit schema that defines the current Houmao-owned skill inventory, named skill sets, and set-based auto-install selections.
- Add one shared installer contract that can project selected current Houmao-owned skills into a target Claude, Codex, or Gemini home while preserving each tool's visible skill layout.
- Add a `houmao-mgr` command family for listing, installing, and inspecting the current Houmao-owned system-skill set and named sets in arbitrary agent homes.
- Route managed brain construction and joined-session adoption through the same installer so Houmao-managed agents and externally managed agents use one installation path.
- Replace mailbox-only hardcoded default installation behavior with named auto-install sets built from the current Houmao-owned skills and keep explicit opt-out semantics for join-time installation.
- Record Houmao-owned install state in the target home so repeated installs are idempotent and Houmao can distinguish its own projected skill trees from unrelated user-authored skill content.
- Validate the packaged skill catalog against an explicit JSON Schema during loading so malformed packaged config fails closed.

## Capabilities

### New Capabilities
- `houmao-system-skill-installation`: Package the current Houmao-owned `houmao-*` skills as maintained assets and define the catalog and installation contract for projecting selected skills into arbitrary tool homes.
- `houmao-mgr-system-skills-cli`: Provide the operator-facing `houmao-mgr` command family for listing, installing, and inspecting the current Houmao-owned system-skill set and named skill sets.

### Modified Capabilities
- `agent-mailbox-system-skills`: Change mailbox skill projection to use the shared packaged Houmao system-skill installer and set-based auto-install selection instead of mailbox-specific installation code paths.
- `houmao-mgr-agents-join`: Change joined-session adoption so default Houmao-owned skill installation uses the shared installer contract and set-based auto-install semantics.
- `houmao-srv-ctrl-native-cli`: Extend the supported `houmao-mgr` top-level command tree to include the new system-skill command family.

## Impact

- Affected code includes packaged asset loading, mailbox skill projection helpers, brain build and join-time installation paths, and the `houmao-mgr` CLI tree.
- Affected docs include CLI reference, mailbox/runtime skill guidance, and any operator guidance that currently describes mailbox-only Houmao skill installation.
- Affected tests include managed brain build coverage, join-time installation coverage, tool-home projection assertions, and the new CLI command surface.
