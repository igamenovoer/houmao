## Why

The current `houmao-mgr project credential ...` CLI hides the real source model: project-local auth is already stored as tool-local bundles under `.houmao/agents/tools/<tool>/auth/<name>/`. Now that the repo-local project overlay exists, the project CLI should use the same nouns operators see on disk and in the agent-definition docs.

## What Changes

- **BREAKING** Replace `houmao-mgr project credential ...` with `houmao-mgr project agent-tools ...`.
- Add a tool-oriented subtree shaped like `houmao-mgr project agent-tools <tool> auth {list,add,get,set,remove}` for Houmao-supported tools.
- Change auth-bundle command semantics so `add` creates, `set` updates, `get` inspects, `list` enumerates, and `remove` deletes.
- Keep the on-disk storage model unchanged at `.houmao/agents/tools/<tool>/auth/<name>/`; do not introduce a separate credential registry.
- Update getting-started and CLI docs to describe local auth bundles through the same `agent-tools ... auth ...` vocabulary used by the source tree.

## Capabilities

### New Capabilities
- `houmao-mgr-project-agent-tools`: Manage project-local tool auth bundles through a CLI that mirrors `.houmao/agents/tools/<tool>/auth/<name>/`.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: The native `houmao-mgr project` subtree changes from `credential` to `agent-tools`.
- `docs-getting-started`: Getting-started docs and agent-definition guidance change from `project credential` wording to `project agent-tools <tool> auth ...`.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/project.py`, project CLI tests, and help text.
- Affected docs: `README.md`, `docs/getting-started/agent-definitions.md`, `docs/getting-started/quickstart.md`, `docs/reference/cli.md`, `docs/reference/cli/houmao-mgr.md`, and system-files reference pages that mention project-local auth management.
- Affected operator surface: breaking CLI rename inside the unmerged feature branch, but no on-disk auth-bundle migration.
