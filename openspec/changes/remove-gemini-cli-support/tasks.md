## 1. Remove Provider Runtime and Schema Surfaces

- [x] 1.1 Delete the Gemini headless backend module and remove its imports, exports, construction, turn dispatch, resume behavior, and backend collections from the realm controller.
- [x] 1.2 Delete the Gemini launch-policy registry entry and remove Gemini strategy ids, hook dispatch, settings mutation, owned-path logic, and launch-argument canonicalization.
- [x] 1.3 Remove `gemini`, `gemini_cli`, and `gemini_headless` from launch plans, manifests, boundary models, registries, gateway models, server models, AG-UI runtime types, launch overrides, and native launch resolution.
- [x] 1.4 Remove Gemini values from JSON schemas for launch plans, session manifests, live and managed registry records, and every other persisted current-state contract.
- [x] 1.5 Remove Gemini model-name and reasoning projection, brain-home environment handling, provider auth environment mappings, and any `.gemini/settings.json` mutation.
- [x] 1.6 Add or update unit tests that assert the exact remaining provider and backend sets while Claude, Codex, and Kimi still resolve their maintained paths; add no Gemini-specific compatibility tests.

## 2. Remove Interactive, Headless, Server, and Passive-Server Integration

- [x] 2.1 Remove the CAO `gemini_cli` compatibility provider, startup command, rendered-state parser, input path, interrupt path, and provider registration.
- [x] 2.2 Remove Gemini from local-interactive process mappings, shared TUI ownership, passive observation, native process recognition, and any TUI-facing provider lists.
- [x] 2.3 Remove Gemini from headless bridge choices, headless base/output parsing, passive-server compatibility and reconstruction, and managed headless command support.
- [x] 2.4 Remove Gemini backend branches from gateway service/storage, server recovery and dispatch, managed-agent state, runtime-artifact join paths, and scoped agent commands.
- [x] 2.5 Remove Gemini stream parsing and renderer fixtures, then keep canonical headless output coverage for the remaining providers.
- [x] 2.6 Delete Gemini cases from server, gateway, passive-server, CAO, TUI ownership, headless, resume, and manifest tests while preserving remaining-provider behavior tests.

## 3. Remove Project Authoring, Credentials, and Starter Assets

- [x] 3.1 Remove Gemini from project and native-agent tool choices, easy specialist/profile/instance logic, configuration drafts, tool inspection, and launch-time validation.
- [x] 3.2 Remove the Gemini credential command group, provider-specific flags, API-key/OAuth/config/home import, login handling, auth-profile mappings, and rename/remove behavior.
- [x] 3.3 Delete `src/houmao/project/assets/starter_agents/tools/gemini/` and remove Gemini adapter/setup projection from project initialization and brain construction.
- [x] 3.4 Remove Gemini model, auth, setup, provider, and required-headless fields from CLI output payloads, help text, and config schemas.
- [x] 3.5 Update project, credential, config-draft, agent-tool, model-selection, launch-policy, and brain-builder tests for the Claude/Codex/Kimi provider set.

## 4. Remove Gemini System-Skill Support and Guidance

- [x] 4.1 Remove Gemini from system-skill destination resolution, default-home resolution, list/install/status/uninstall tool choices, and projection modes; delete stale Gemini cleanup logic instead of retaining a retirement path.
- [x] 4.2 Delete Gemini-only credential reference pages from packaged skills and remove every Gemini provider branch from current agent-definition, agent-instance, credential-manager, touring, and related skill instructions.
- [x] 4.3 Preserve `.gemini` mentions only where a provider-neutral workspace-safety rule treats it as third-party local state; ensure those mentions do not claim Houmao support.
- [x] 4.4 Update packaged system-skill catalog/content tests and CLI installation tests so Gemini is rejected and Claude, Codex, Kimi, and non-launch skill-only targets remain correct where applicable.

## 5. Remove Demos and Test Fixtures

- [x] 5.1 Remove the Gemini lane from `single-agent-gateway-wakeup-headless` code, parameters, README, preflight, auth import, verification, and provider matrix.
- [x] 5.2 Delete the dedicated legacy Gemini headless demo and remove maintained demo-index links or commands that route to it.
- [x] 5.3 Delete tracked Gemini starter fixtures under `tests/fixtures/plain-agent-def/tools/gemini/` and Gemini auth-bundle marker directories under `tests/fixtures/auth-bundles/gemini/`.
- [x] 5.4 Delete the obsolete `tests/fixtures/auth-bundles/tools.tar.gz.enc` credential archive and its checksum instead of carrying outdated credentials into the next release.
- [x] 5.5 Remove Gemini from manual smoke scripts, demo tests, fixture expectations, provider parametrization, and CLI-shape contracts while preserving remaining-provider coverage.

## 6. Update Maintained Documentation and Context

- [x] 6.1 Update `README.md`, `AGENTS.md`, `CLAUDE.md`, and other maintained root guidance for the Claude/Codex/Kimi provider set, and delete `GEMINI.md`.
- [x] 6.2 Update all maintained getting-started, CLI, build-phase, run-phase, gateway, mailbox, server, TUI-parsing, and system-skills documentation to remove Gemini workflows, values, paths, fixtures, and support claims.
- [x] 6.3 Update demo documentation and the `houmao-dev-testing` feature design to contain only Claude, Codex, and Kimi testing scope, with no Gemini exclusion or retirement guidance.
- [x] 6.4 Delete maintained Gemini issue, knowledge-summary, and obsolete design pages that exist only to support Gemini, and remove links from maintained indexes.
- [x] 6.5 Preserve archived OpenSpec changes and immutable historical logs, document the exact search exclusions, and ensure no maintained page routes readers into historical Gemini workflows.

## 7. Verify Complete Removal

- [x] 7.1 Run a repository-wide case-insensitive Gemini audit over maintained source, tests, docs, demos, context, schemas, and system skills; classify every retained match as an approved archive, immutable history, cache/external path, or provider-neutral safety mention.
- [x] 7.2 Verify supported CLI help and API/schema inventories expose only Claude, Codex, and Kimi as applicable, with no Gemini-specific alias, parser, tombstone, or error branch.
- [x] 7.3 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, and `pixi run test-runtime`, fixing failures caused by provider-set removal.
- [x] 7.4 Run targeted server, passive-server, gateway, CAO, project, credential, launch-policy, schema, demo, documentation, and system-skill test suites.
- [x] 7.5 Run package build and distribution checks to confirm deleted Gemini assets or modules are not referenced by package metadata.
- [x] 7.6 Run `openspec validate remove-gemini-cli-support --strict` and `git diff --check`, then record the maintained-root audit command and all test evidence in the implementation handoff.
