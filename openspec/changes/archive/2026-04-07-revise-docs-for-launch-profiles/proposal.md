## Why

The `add-agent-launch-profiles` change has shipped catalog support, two CLI surfaces (`project easy profile ...` and `project agents launch-profiles ...`), `agents launch --launch-profile`, and the canonical `project agents recipes ...` surface with `presets` retained as a compatibility alias. Operator-facing documentation has not caught up: `docs/reference/cli/houmao-mgr.md` still lists only the old `project easy specialist|instance` and `project agents roles|presets|tools` subtrees, `docs/getting-started/easy-specialists.md` does not mention easy profiles at all, and the build-phase reference still describes a launch-override precedence pipeline that has no notion of a launch-profile layer. Several reference and getting-started pages also still describe the low-level source object as "preset" rather than "recipe", which is now inconsistent with help text and the actual CLI behavior.

The result is that the new launch-profile surface is effectively undocumented and the existing docs actively mislead readers about the precedence model and the easy-versus-explicit lane split.

## What Changes

- Add a new conceptual page `docs/getting-started/launch-profiles.md` that explains the shared launch-profile semantic model, the easy-versus-explicit lane split, the five-layer precedence chain, and prompt overlays. This is the page the rest of the docs will link to instead of restating the concept inline.
- Heavy rewrite of `docs/reference/cli/houmao-mgr.md` for the `project easy` and `project agents` subtrees: extend the command-shape ASCII tree, add the missing `recipes`, `launch-profiles`, and `easy profile` subcommand families with option summaries, and document `agents launch --launch-profile` plus its mutual exclusion with `--agents`.
- Heavy rewrite of `docs/getting-started/easy-specialists.md` to cover the three-step easy lane (specialist → easy profile → instance) instead of the current two-step (specialist → instance). Retitle the comparison section to compare specialist, easy profile, and explicit recipe + launch-profile.
- Refresh `docs/getting-started/overview.md`: update the opening line, the build-phase mermaid pipeline, and the project ASCII tree to reflect the recipe-and-launch-profile model.
- Refresh `docs/reference/build-phase/launch-overrides.md`: extend the precedence pipeline mermaid diagram and the `merge_launch_intent` description to include the launch-profile layer between recipe defaults and direct CLI overrides.
- Refresh `docs/reference/run-phase/launch-plan.md`: document the new launch-profile provenance fields the manifest carries through into runtime metadata.
- Refresh `docs/reference/cli.md`: add a short paragraph and pointer for the launch-profile surfaces under the `project` view enumeration.
- Mechanical vocabulary sweep across light-touch reference pages (`docs/index.md`, `docs/reference/system-files/agents-and-runtime.md`, `docs/reference/realm_controller.md`, `docs/reference/houmao_server_pair.md`, `docs/reference/agents/operations/project-aware-operations.md`, `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md`, `docs/reference/build-phase/launch-policy.md`, `docs/reference/mailbox/contracts/project-mailbox-skills.md`) to use `recipe` for user-facing source authoring while keeping `preset` only when naming the on-disk projection path `.houmao/agents/presets/` or the legacy compatibility-alias CLI.
- Add the new launch-profiles guide to `docs/index.md` and `mkdocs.yml` navigation so it is discoverable.
- Complete and correct the partial in-tree edits already present on `README.md`, `docs/getting-started/agent-definitions.md`, `docs/getting-started/quickstart.md`, and `docs/reference/cli/system-skills.md`.

All diagrams in new and rewritten doc content SHALL use mermaid fenced code blocks rather than ASCII art.

## Capabilities

### New Capabilities
- `docs-launch-profiles-guide`: documentation requirements for the new conceptual launch-profiles guide page that explains the shared semantic model, both authoring lanes, the precedence chain, and prompt overlays.

### Modified Capabilities
- `docs-getting-started`: agent-definition and quickstart pages need to describe the recipe-and-launch-profile project tree, the new authoring paths, and the link to the launch-profiles guide.
- `docs-easy-specialist-guide`: easy-specialists page needs to add an Easy Profiles section, update its diagram for the three-step lane, and document `--profile`, the `--profile`/`--specialist` mutual exclusion, and easy-profile-aware instance inspection.
- `docs-cli-reference`: `houmao-mgr.md` needs to document `project easy profile`, `project agents recipes`, `project agents launch-profiles`, and `agents launch --launch-profile`, including the command-shape tree and option summaries.
- `docs-build-phase-reference`: `launch-overrides.md` needs to add the launch-profile layer to its precedence pipeline and use `recipe` as the canonical name for the source-layer overrides instead of `preset`.
- `docs-run-phase-reference`: `launch-plan.md` needs to record that the manifest carries launch-profile provenance (lane plus profile name) into runtime metadata for inspection and replay.
- `docs-site-structure`: `docs/index.md` and the mkdocs nav need to list the new launch-profiles guide alongside the existing getting-started pages.

## Impact

- Affected files (heavy rewrite): `docs/reference/cli/houmao-mgr.md`, `docs/getting-started/easy-specialists.md`.
- Affected files (medium refresh): `docs/getting-started/overview.md`, `docs/reference/build-phase/launch-overrides.md`, `docs/reference/run-phase/launch-plan.md`, `docs/reference/cli.md`.
- Affected files (vocabulary sweep): `docs/index.md`, `docs/reference/system-files/agents-and-runtime.md`, `docs/reference/realm_controller.md`, `docs/reference/houmao_server_pair.md`, `docs/reference/agents/operations/project-aware-operations.md`, `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md`, `docs/reference/build-phase/launch-policy.md`, `docs/reference/mailbox/contracts/project-mailbox-skills.md`.
- New file: `docs/getting-started/launch-profiles.md`.
- Affected nav: `mkdocs.yml`.
- Already-pending in-tree edits to be completed and reconciled: `README.md`, `docs/getting-started/agent-definitions.md`, `docs/getting-started/quickstart.md`, `docs/reference/cli/system-skills.md`.
- No code changes. No CLI changes. No spec deltas outside the `docs-*` capabilities.
- TUI-parsing developer docs that mention "preset" in the parser-detector sense are NOT in scope.
