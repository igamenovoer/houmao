## 1. Manifest and Domain Model

- [ ] 1.1 Replace the v1 flat `catalog.toml` and JSON Schema with the versioned pack, public-skill, protected-mount, and protected-routine manifest schema.
- [ ] 1.2 Add strict typed models for pack audiences, public roles, public skills, protected routines, dependencies, default lanes, and actor-qualified invocation designators.
- [ ] 1.3 Implement manifest parsing and validation for unique ids, source containment, per-pack role cardinality, route-name uniqueness, and forbidden auto-skill membership.
- [ ] 1.4 Implement audience-specific protected dependency closure and reject ineligible or missing transitive dependencies before composition.
- [ ] 1.5 Add route helpers that map one protected logical id to admin and agent invocation designators without exposing it as an install selector.
- [ ] 1.6 Add a read-only v1 catalog loader and known-content digest inventory used only to classify legacy flat installations.
- [ ] 1.7 Add focused unit tests and invalid fixtures for all manifest, actor-route, dependency, and legacy-catalog model rules.

## 2. Pack Composition and Ownership State

- [ ] 2.1 Implement an audience-aware composer that combines one public entrypoint source, the selected protected route file, shared resources, and only the eligible protected subskill closure.
- [ ] 2.2 Make the composer install no protected content beneath `houmao-admin-welcome` and reject protected top-level output.
- [ ] 2.3 Add recursive staged-tree validation for frontmatter, `SKILL.md` presence, actor guards, public commands, direct-subskill route summaries, command layout, and source containment.
- [ ] 2.4 Define the versioned pack receipt model and tool-scoped receipt/materialization locations under the target home.
- [ ] 2.5 Implement receipt serialization, atomic persistence, forward-version rejection, and read-only status handling for absent or corrupt receipts.
- [ ] 2.6 Implement transaction preflight for all selected public paths, including receipt-owned replacement, untracked collision rejection, and unrelated-skill preservation.
- [ ] 2.7 Implement same-filesystem staging, bounded backups, all-member commit, receipt commit, and rollback for multi-public pack transactions.
- [ ] 2.8 Implement copy projection for complete composed public trees and keep it as the external and managed default.
- [ ] 2.9 Implement explicit symlink projection through receipt-owned complete materializations rather than uncomposed public source directories.
- [ ] 2.10 Implement pack status classification for absent, complete, incomplete, drifted, and conflicting state with public-role and protected-mount evidence.
- [ ] 2.11 Implement safe upgrade classification for package-linked, digest-matched, modified, unknown, and partial legacy flat projections.
- [ ] 2.12 Implement pack uninstall and exact managed-home sync using only receipt-owned public paths and materializations.
- [ ] 2.13 Add filesystem tests for composition, public path shape, atomic admin-pack handling, rollback, receipts, symlink materialization, drift, collisions, legacy migration, and unrelated-path preservation.

## 3. Public Admin and Agent Skills

- [ ] 3.1 Create the self-contained public `houmao-admin-welcome` skill with `help`, `show-options`, `choose-path`, `show-command-map`, `next-step`, and `start-guided-tour` commands.
- [ ] 3.2 Move maintained touring concepts and state-aware guidance into welcome-local references and implement the five curated guided paths.
- [ ] 3.3 Add the welcome read-only gate, narrow implicit-trigger metadata, prohibited mutation list, and context-preserving admin-entrypoint handoff templates.
- [ ] 3.4 Create public `houmao-admin-entrypoint` with the human-operator actor declaration, explicit-target rules, required/optional question gate, and admin protected-route map.
- [ ] 3.5 Implement admin-entrypoint delegation of empty and welcome-oriented commands to the standalone welcome without duplicating welcome resources.
- [ ] 3.6 Implement the explicit joined-session adoption route that ends the admin frame and hands later work to the agent entrypoint only after successful identity verification.
- [ ] 3.7 Create public `houmao-agent-entrypoint` with managed-agent actor declaration, `houmao-mgr --print-json agents self identity` verification, fail-closed behavior, and agent protected-route map.
- [ ] 3.8 Add verified self-target defaults, explicit peer-target handling, admin-route rejection, and concise agent help without an agent welcome.
- [ ] 3.9 Add content tests for public names, roles, command maps, welcome mutation boundaries, actor declarations, identity command spelling, delegation, and standalone handoff behavior.

## 4. Protected Shared Routine Refactor

- [ ] 4.1 Create the canonical `protected/houmao-shared-routines` source bundle with checked-in admin and agent route files, shared commands, shared references, and nested subskill ownership.
- [ ] 4.2 Encode the complete admin-only, agent-only, and shared audience matrix in the manifest and both protected route files with one “When to Route Here” summary per included direct subskill.
- [ ] 4.3 Move the eighteen maintained low-level skill packages into canonical protected subskills while preserving stable logical ids and private resources.
- [ ] 4.4 Remove the flat `houmao-touring` source and migrate its maintained behavior to `houmao-admin-welcome` without a compatibility directory.
- [ ] 4.5 Remove `houmao-specialist-mgr`, move any remaining unique references into protected `houmao-agent-definition`, and retain specialist/profile behavior only in the canonical routine.
- [ ] 4.6 Convert parent-owned `actions/*.md` and procedure-only `subskills/*.md` pages to `commands/` or `references/` according to resource ownership.
- [ ] 4.7 Convert every retained nested capability into a true subskill with its own `SKILL.md`, private resources, lean router, and parent route summary.
- [ ] 4.8 Add actor-frame validation and explicit admin versus self branches to agent-instance, agent-inspect, agent-messaging, and agent-gateway routines.
- [ ] 4.9 Add actor-frame validation and explicit admin versus self branches to email-comms, mailbox-manager, memory-manager, and workspace-manager routines.
- [ ] 4.10 Add actor-frame validation and eligible actor behavior to advanced usage, pro loop, lite loop, AG-UI interop, and graphing routines.
- [ ] 4.11 Add admin-only guards to project, credential, agent-definition, and operator-messaging routines and an agent-only guard to notified email processing.
- [ ] 4.12 Replace direct peer-skill references throughout protected content with public entrypoint prompts or entrypoint-qualified internal route traces.
- [ ] 4.13 Add recursive content tests for every protected logical id, command map, route summary, actor guard, audience composition, and absence of public compatibility wrappers.

## 5. Policy, Runtime, and Mailbox Integration

- [ ] 5.1 Replace stored `sets` and `skills` system-skill policy selectors with `packs` while retaining valid default, inherit, extend, replace, and none mode semantics.
- [ ] 5.2 Update recipe, launch-profile, configuration, and provenance serialization plus validation to use pack ids and reject protected logical ids.
- [ ] 5.3 Change external-home omitted selection to the admin pack and managed launch, rebuild, relaunch, and join omitted selection to the agent pack.
- [ ] 5.4 Update brain construction and reused-home sync to install complete receipt-owned agent packs with copy projection.
- [ ] 5.5 Update joined-session adoption failure and opt-out handling so later runtime prompts assume protected mailbox routes only when the agent pack is installed.
- [ ] 5.6 Route notifier-driven email rounds and ordinary runtime mailbox prompts through `houmao-agent-entrypoint` with required gateway context.
- [ ] 5.7 Keep `houmao-auto-system-prompt` in `assets/auto_skills`, preserve its collision rules, and exclude it from pack receipts and selectors.
- [ ] 5.8 Update managed runtime and policy tests for defaults, overrides, disablement, reused-home sync, mailbox prompt routing, auto-skill separation, and secret-free provenance.

## 6. Pack-Oriented CLI

- [ ] 6.1 Replace system-skills list rendering with pack, public-role, default-lane, and protected-eligibility output in plain and structured forms.
- [ ] 6.2 Replace set and skill install options with repeatable `--pack admin|agent`, retain supported tool/home/mode resolution, and add obsolete-selector diagnostics.
- [ ] 6.3 Update install result models and output to report selected packs, public paths, receipt path, projection mode, and nested protected inspection detail.
- [ ] 6.4 Replace stateless status output with receipt-aware pack integrity, legacy evidence, drift, and conflict reporting.
- [ ] 6.5 Add the transactional `system-skills upgrade` command with selected-pack refresh and conservative legacy migration.
- [ ] 6.6 Replace global name-based uninstall with selected receipt-owned pack uninstall and preserved-conflict reporting.
- [ ] 6.7 Update command help, root `--print-json` payloads, errors, and supported Claude, Codex, Copilot, Kimi, and universal target behavior without adding Gemini.
- [ ] 6.8 Add compact CLI smoke tests for list, default and explicit install, status, upgrade, uninstall, structured output, unsupported packs, removed selectors, and conflicts.

## 7. Documentation and Migration Guidance

- [ ] 7.1 Rewrite the README Quick Start to install the admin pack and begin with `$houmao-admin-welcome start-guided-tour`.
- [ ] 7.2 Replace README flat skill tables, old set names, direct protected invocations, and touring references with the three-role public surface and actor distinction.
- [ ] 7.3 Rewrite `docs/getting-started/system-skills-overview.md` around actor packs, public roles, welcome paths, the complete protected route matrix, and managed versus external defaults.
- [ ] 7.4 Rewrite `docs/reference/cli/system-skills.md` for pack lifecycle, receipts, status classes, upgrade, safe legacy handling, tool homes, projection modes, and structured output.
- [ ] 7.5 Update mailbox, agent-definition, lifecycle, memory, workspace, loop, AG-UI, graphing, and project docs to use public entrypoint invocations and internal route notation consistently.
- [ ] 7.6 Add a breaking migration section mapping old public skill prompts and set selectors to the admin or agent pack and preserving conflict-resolution instructions.
- [ ] 7.7 Audit all repository docs, examples, runtime prompt fixtures, and tests for `houmao-touring`, `houmao-specialist-mgr`, `core`, `extensions`, `all`, and top-level low-level skill paths.

## 8. Verification and Packaging

- [ ] 8.1 Update package-data configuration so the new manifest, schema, public assets, protected assets, route files, commands, references, and nested subskills ship in wheels and sdists.
- [ ] 8.2 Run OpenSpec strict validation and fix every delta-operation, scenario, and artifact consistency issue.
- [ ] 8.3 Run focused unit and integration tests for manifest models, actor routing, composition, receipts, migration, CLI, managed homes, mailbox prompts, and content validation.
- [ ] 8.4 Run `pixi run format`, inspect the resulting changes, and run `pixi run lint`.
- [ ] 8.5 Run `pixi run typecheck` and resolve every strict typing failure in the refactored models and lifecycle code.
- [ ] 8.6 Run `pixi run test` and the relevant runtime-focused suite, mapping any removed flat-skill assertions to retained pack-aware coverage.
- [ ] 8.7 Run `pixi run build-dist` and `pixi run check-dist`, then inspect built artifacts to confirm all public and protected skill resources are present.
