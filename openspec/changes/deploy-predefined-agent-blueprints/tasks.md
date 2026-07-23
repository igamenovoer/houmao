## 1. Blueprint Package Domain

- [ ] 1.1 Add typed blueprint manifest, input, output, skill-binding, source-reference, and diagnostic models in a dedicated `houmao` module.
- [ ] 1.2 Implement `blueprint.toml` parsing and validation for the v1 schema, supported input types, supported tool families, declared members, duplicate names, and maintained package limits.
- [ ] 1.3 Implement confined package traversal and deterministic tree hashing that reject symlinks, traversal, special files, unsafe names, and undeclared binary templates.
- [ ] 1.4 Implement strict placeholder discovery, typed input validation, deterministic rendering, and unresolved-placeholder rejection without an executable template engine.
- [ ] 1.5 Implement built-in and explicit local source resolution plus plan-owned source snapshotting with one shared validation path.
- [ ] 1.6 Add focused unit tests for valid packages, manifest errors, typed inputs, placeholder formatting, repeatable digests, traversal, symlinks, reserved skill names, and non-executable content.

## 2. Built-in Blueprint Assets

- [ ] 2.1 Add a package-data root for agent blueprints that is separate from system skills and native-agent starter assets.
- [ ] 2.2 Author the `repository-reviewer` built-in with a specialist prompt, profile overlay, memo seed, typed objective and completion inputs, and one complete task-specific private skill.
- [ ] 2.3 Update distribution configuration so source distributions and wheels contain every built-in blueprint member.
- [ ] 2.4 Add tests that enumerate, load, validate, render, and package-check the built-in collection through the production source loader.

## 3. Project Catalog and Managed Content

- [ ] 3.1 Add deployment catalog dataclasses and schema tables for provenance, normalized-input content, owned specialist/profile relationships, output ownership, and last-applied digests.
- [ ] 3.2 Add the stable deployment inspection view and repository methods for create, load, list, update, integrity inspection, reference checks, and removal.
- [ ] 3.3 Add the overlay-owned `content/agent-deployments/<deployment-id>/` root and safe helpers for normalized inputs and complete private-skill trees.
- [ ] 3.4 Increment the catalog schema and add an explicit `project migrate` step from the immediately preceding schema while preserving existing project objects.
- [ ] 3.5 Extend catalog integrity checks and compatibility projection handling for deployment-owned content without treating deployment directory layout as canonical semantics.
- [ ] 3.6 Add catalog and migration tests for fresh schemas, explicit prior-schema migration, foreign-key ownership, read views, lexical-path mutation safety, and unsupported-schema diagnostics.

## 4. Blueprint Discovery and Planning

- [ ] 4.1 Implement blueprint list and inspect services that expose validated manifest data and digests without project-definition mutation.
- [ ] 4.2 Define the versioned deployment plan schema, opaque plan ids, selected-overlay binding, expected preconditions, and structured blocker and warning records.
- [ ] 4.3 Implement creation planning from blueprint source, normalized inputs file, deployment name, tool, credential, workdir, and maintained optional profile settings.
- [ ] 4.4 Implement deterministic specialist, profile, registered-skill, private-skill, and managed-path naming from a sanitized deployment name.
- [ ] 4.5 Stage source snapshots, rendered output trees, and `plan.json` beneath the selected overlay jobs root without creating durable definitions or deployment records.
- [ ] 4.6 Add planner tests for overlay bootstrap, tool and credential validation, output summaries, deterministic names, collisions, source changes, generated skill validation, and absence of definition side effects.

## 5. Atomic Deployment Apply

- [ ] 5.1 Add transaction-aware internal specialist, skill, and profile persistence primitives that can share one catalog transaction without recursively invoking Click handlers.
- [ ] 5.2 Implement apply preflight for plan location, schema, overlay identity, every recorded digest, credential identity, catalog version, target preconditions, and lexical output paths.
- [ ] 5.3 Implement deployment creation apply with staged managed content, catalog ownership records, specialist/profile relationships, registered and private skills, prompt overlay, memo seed, and compatibility projection.
- [ ] 5.4 Implement filesystem rollback bookkeeping and database rollback so failure at any apply phase leaves no observable partial deployment.
- [ ] 5.5 Add success and failure-injection integration tests covering complete materialization, static skills at rest, profile-backed launch preparation, modified plans, cross-project plans, stale preconditions, projection failure, and rollback.

## 6. Deployment Inspection, Update, Doctor, and Removal

- [ ] 6.1 Implement deployment list and get services with essential blueprint provenance, owned objects, content digests, timestamps, health summary, and exact profile launch handoff.
- [ ] 6.2 Implement doctor classification for healthy state, source drift, output drift, missing objects, invalid generated skills, broken profile relationships, unrelated references, and live-agent references.
- [ ] 6.3 Implement explicit update planning and atomic update apply with blueprint-id continuity and last-applied object and content preconditions.
- [ ] 6.4 Implement reference-protected removal that deletes only deployment-owned catalog objects and lexical managed artifacts while preserving credentials and unrelated content.
- [ ] 6.5 Add integration tests for source drift, operator-edited output, clean update, blocked update, clean removal, live-agent blocking, unrelated references, and symlink-target preservation.

## 7. `houmao-mgr` Project CLI

- [ ] 7.1 Add `project agent-blueprints list` and `inspect` Click commands with maintained plain and structured output.
- [ ] 7.2 Add `project agent-deployments plan` and `apply` commands with explicit inputs, stable plan-id output, blocker reporting, and no automatic live launch.
- [ ] 7.3 Add `project agent-deployments list`, `get`, `doctor`, and `remove` commands plus explicit `plan --update` behavior.
- [ ] 7.4 Add CLI help, JSON-output, invalid-input, missing-overlay, migration-required, and end-to-end command tests.

## 8. System-Skill Routing

- [ ] 8.1 Add the `deploy-blueprint` command page to `houmao-agent-definition` using the maintained subcommand format, admin actor gate, typed-input synthesis phases, direct CLI snippets, preview, doctor, and launch-stop boundary.
- [ ] 8.2 Update `houmao-agent-definition` routing tables, manifest command metadata, help, and host metadata so the new lane is discoverable only through its existing admin-eligible parent route.
- [ ] 8.3 Update `houmao-admin-entrypoint` to recognize natural-language predefined-agent intent and route it implicitly through shared routines without inferring live-launch authority.
- [ ] 8.4 Update the explicit `houmao-shared-routines` route and metadata so direct default-admin invocation works and `as-agent` invocation rejects the admin-only operation.
- [ ] 8.5 Refresh and validate any automatically generated system-skill prompts, packaged metadata, content digests, and installation fixtures affected by the routing change.
- [ ] 8.6 Add static system-skill tests for route completeness, command-page existence, actor eligibility, sibling handoff notation, help behavior, and absence of runtime skill composition instructions.

## 9. Behavior Tests and Documentation

- [ ] 9.1 Add manual-invocation behavior cases for `$houmao-admin-entrypoint` and `$houmao-shared-routines agent-definition deploy-blueprint`, including missing inputs, preview, apply, and no-launch outcomes.
- [ ] 9.2 Add automatic-invocation behavior cases that distinguish predefined-agent deployment intent from ordinary specialist creation, agent-loop preparation, managed-agent self work, and explicit live launch.
- [ ] 9.3 Add behavior cases that verify fixed blueprint meaning survives hostile or competing task text and that undeclared fields cannot control paths, credentials, names, or mutation policy.
- [ ] 9.4 Document the agent blueprint package contract, local authoring workflow, built-in discovery, deployment lifecycle, drift/update rules, and separation from retired native-agent `blueprints/`.
- [ ] 9.5 Update CLI, project layout, agent-definition, and system-skill documentation with current command examples and the static materialization boundary.

## 10. Verification

- [ ] 10.1 Run focused blueprint, catalog, migration, deployment-service, CLI, packaging, and system-skill test suites and resolve failures.
- [ ] 10.2 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, and `pixi run test`.
- [ ] 10.3 Build and check wheel and source distributions, then verify the installed package can list and plan the packaged `repository-reviewer` blueprint.
- [ ] 10.4 Run OpenSpec validation and confirm every implemented behavior is covered by the change specs and recorded test evidence.
