# Tasks

## 1. Static Metadata and Instruction Format

- [x] 1.1 Move invocation notation into YAML `metadata` throughout the active packaged instruction tree and add its declaration to every current entrypoint. Move the six release values to `metadata.houmao_version` and update manifest, doctor, and release validation in the same change. Verify with synthetic parser and doctor cases, `pixi run check-system-skill-versions`, and the available Agent Skills validator on each standalone root.
- [x] 1.2 Bring the changed instruction pages and their related route and reference pages into Imsight form. Review numbered workflows, planning fallbacks, command links, route sentences, and `DO NOT` guardrails while preserving operation semantics and entrypoint activation. Update installation and doctor documentation for the new metadata format and normal upgrade path.

## 2. Shared Access and File Workflows

- [x] 2.1 Add the parent-scoped `houmao-agent-access` tree and its command pages. Review examples for the detached owner, live administrator roster, and verified cross-account peer lanes against `agents single ... access --help` and the authorization reference. Verify the declared entrypoint and resource paths exist.
- [x] 2.2 Add the parent-scoped `houmao-agent-files` tree with owned discovery, inspection, draft, publication, and reconciliation resources. Review the owner-enabled DSH Web mount, precise permissions, author and publisher attribution, and original-operation-ID status lookup against `agents single ... files --help` and the file edits reference. Verify the declared entrypoint and resource paths exist.
- [x] 2.3 Wire both children into the manifest, schema, two actor routes, shared router, and read-only help. Drive child layout and doctor checks from the declared inventory. Verify six discoverable standalone roots, the complete eighteen-child shared tree, and the expected `system-skills list` and doctor results. Update README and system-skills overview examples with the new routes and public versus parent-scoped placement.

## 3. Existing Command Guidance

- [x] 3.1 Update `agent-gateway` for private deployment configuration, signed-request handoff, and `web-entry`. Correct mail attachment authority in the email routine while preserving its receipts, binding checks, and supported fallbacks. Review examples against the current gateway CLI, authorization policy, and mail operation contracts.
- [x] 3.2 Update the two saved project profile workflows and the one-shot instance launch workflow with the four tmux choices and their precedence. Add `native-resources()` and the handoff to `agent-files`. Verify the flag and scope examples against source CLI help and the launch and native refresh references, including the separate native dossier lane.
- [x] 3.3 Revise inspection and messaging to use explicit agent identity, saved records, and managed observations. Review a same-name, two-server example and confirm the raw pane fallback requires the recorded socket and exact target. Verify examples treat transport port options as modifiers and preserve ordinary mail and prompt paths without an attached gateway.
- [x] 3.4 Align the manifest, route tables, help, and `system-skills list` with the published commands. Include the existing definition and instance operations, canonical messaging `mail` and its `mail-handoff` alias, and the project-manager handoff for profiles. Verify structured catalog output and review command table parity.

## 4. Skill Unit Test Reduction

- [x] 4.1 Consolidate shipped asset assertions around entrypoint, directory, and declared resource existence. Remove instruction-text and semantic fixture assertions from `test_system_skills.py` and the skill-specific documentation tests. Remove the unused pre-compaction inventory and semantic fixture after verifying consumer references. Verify that changing instruction wording alone does not alter the asset test cases.
- [x] 4.2 Trim authored skill-text assertions in brain builder, mailbox support, join, config draft, and managed memory tests. Keep installed path assertions and tests of executable CLI, parser, staging, digest, ownership, collision, rollback, and generated prompt behavior. Decouple the development skill test from the live runtime frontmatter as needed. Run the affected unit modules.

## 5. Integrated Verification

- [x] 5.1 Validate the complete change with lint, strict type checking, the full unit suite, the strict docs build, the distribution build, and `openspec validate revise-system-skills --strict`. Check source and installed pack inventories and release metadata in the built wheel and sdist.

## Workflow Follow-Up

- When syncing the change, update the main static collection and managed skill test coverage purposes to describe the manifest-owned inventory and structure-only asset tests.
