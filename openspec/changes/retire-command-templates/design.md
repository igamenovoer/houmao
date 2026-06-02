## Context

`houmao-mgr internals command-templates` currently exposes a code-first registry that describes ordinary `houmao-mgr` commands, renders sparse JSON intent into argv, and can export YAML views of the registry. Core runtime code does not depend on that registry; the active consumers are packaged system-skill instructions, command-template specs, and command-template unit tests.

The model has proven to be the wrong abstraction. It asks agents to learn a second command language before running the real command, while also competing with `config-drafts` for template-like behavior. The intended product split is simpler:

- `config-drafts` generates YAML/config documents.
- Skills show executable workflows as explicit `bash` command blocks.
- The maintained CLI itself remains the source of truth for command behavior.

## Goals / Non-Goals

**Goals:**

- Remove the `internals command-templates` command group and all command-template registry/render/export code.
- Update packaged skills so no instruction requires `internals command-templates show|render|export`.
- Preserve `internals config-drafts` for YAML authoring and make skill guidance route YAML-template needs there.
- Replace command-template tests with assertions that the removed command group is absent and that packaged skills no longer reference it.
- Remove command-template requirements from related specs so future changes do not maintain the historical layer.

**Non-Goals:**

- Do not add a replacement executable-command renderer.
- Do not expand config-drafts into action-command rendering.
- Do not preserve compatibility for `internals command-templates`; this repository permits breaking changes during the current unstable development phase.
- Do not redesign the underlying project, credential, gateway, mailbox, or lifecycle command semantics.

## Decisions

1. Hard-remove the command-template CLI group.

   The implementation removes the group from `houmao-mgr internals` rather than keeping a deprecated command that prints migration guidance. This avoids teaching skills or tests that the historical surface is still valid.

2. Delete the registry package instead of retaining it as an internal library.

   The registry's purpose was to describe maintained commands in a second structured schema. Keeping it without the CLI would preserve the duplicated source of truth and invite future call sites to depend on it again.

3. Use direct `bash` command snippets in packaged skills.

   Skills that previously rendered sparse intent SHALL show the actual `houmao-mgr` command families they intend to run, with placeholders for user-provided values where needed. The command help, specs, and tests own valid option behavior.

4. Keep config-drafts narrow.

   `internals config-drafts` remains a YAML authoring helper only. It SHALL NOT grow target argv, action-command renderers, command conflict schemas, or omitted-field bookkeeping to fill the removed command-template gap.

5. Treat skill updates as part of the removal, not follow-up cleanup.

   Removing the subcommand while leaving packaged skills that call it would create broken agent workflows. The implementation updates the skills in the same change and adds content tests for the absence of command-template references.

## Risks / Trade-offs

- Agents lose renderer blockers for missing or conflicting action-command inputs. -> Mitigate by making skill snippets explicit and preserving guardrail prose that tells agents to stop when required inputs are missing or mutually exclusive.
- Direct command snippets can drift from CLI behavior. -> Mitigate with focused tests that inspect skill content for retired command-template references and with existing CLI tests that validate command behavior.
- Removing the registry deletes broad metadata coverage that tests used as inventory. -> Mitigate by relying on each command family's own unit/spec coverage rather than a duplicated registry inventory.
- Some specs mention command templates across many capabilities. -> Mitigate by removing or rewriting those requirements in the same OpenSpec change so archive does not resurrect old obligations.
