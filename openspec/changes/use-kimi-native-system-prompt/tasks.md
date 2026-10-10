## 1. Native Kimi Prompt Model

- [x] 1.1 Add a Kimi native-system-prompt module that rejects every `${identifier}` token in the effective Houmao prompt, renders canonical `${base_prompt}` plus effective-prompt bytes, atomically writes or removes `SYSTEM.md`, verifies hashes, and returns typed provenance.
- [x] 1.2 Add focused unit tests for canonical bytes, empty prompt removal, rejection of every `${identifier}` form, allowed bare-dollar text, atomic repair, permissions, and provenance hashes.
- [x] 1.3 Add `native_home_system_prompt` to the runtime role-injection model, remove `auto_skill_system_prompt`, and update model docstrings so `RoleInjectionPlan.prompt` means the complete effective launch prompt.
- [x] 1.4 Update Pydantic boundary models and launch/session JSON schemas to accept the native home method and reject the retired auto-skill method, with schema-consistency and old-manifest rejection tests.

## 2. Brain Build and Provider-Start Enforcement

- [x] 2.1 Integrate native Kimi `SYSTEM.md` projection after setup and auth projection in brain construction, make the path runtime-owned, and record construction provenance in the brain manifest.
- [x] 2.2 Revalidate and repair native Kimi prompt projection before fresh headless, fresh TUI, and relaunch provider starts, then publish verification metadata in the launch plan and session manifest.
- [x] 2.3 Implement exact Kimi prompt-precedence validation for `--agent`, `--agent-file`, project default-agent overrides, and configured extra-agent directories without mutating project-owned files.
- [x] 2.4 Force `KIMI_CODE_LEGACY_FLAG=0` in every managed Kimi process after other environment layers and reject any later truthy override.
- [x] 2.5 Add brain-builder, launch-plan, headless, local-interactive, relaunch, empty-role, drift-repair, and precedence-conflict tests for the native prompt lifecycle.

## 3. Launch Policy and Version Boundary

- [x] 3.1 Replace `system_prompt_bootstrap` and its three booleans with an explicit native system-prompt contract in launch-policy models, parsing, payloads, registry validation, and Claude/Codex registry entries.
- [x] 3.2 Replace the Kimi 0.23 strategy entries with `>=0.34.0` headless and TUI strategies with no upper bound that declare native `SYSTEM.md`, v2-engine, permission, credential, owned-path, and current source-evidence boundaries.
- [x] 3.3 Update Kimi provider hooks to validate native prompt readiness and canonicalize Kimi 0.34.0-or-later headless and TUI arguments while keeping credential, permission, and prompt concerns separate.
- [x] 3.4 Add registry and hook tests proving selection at 0.34.x and representative newer versions, pre-0.34 rejection, headless flag exclusions, resumed TUI `--auto`, and engine/prompt conflict failures.

## 4. Auto-Skill and CLI Removal

- [x] 4.1 Delete the packaged `houmao-auto-system-prompt` asset, auto-skill module, asset package, and packaging entries.
- [x] 4.2 Remove auto-skill fields, collision checks, projection, discovery mutation, manifest provenance, constants, and call sites from brain construction, runtime planning, and manager launch flows.
- [x] 4.3 Remove `auto_skill_name` from the system-skill manifest, bump the source schema and parser to `houmao-system-skills.v5`, and update lifecycle, doctor, manifest, and pack tests without changing installed skill-config ownership.
- [x] 4.4 Remove `houmao-mgr agents self system-prompt show` and its prompt-loading helper, tests, help snapshots, and command-reference entries while retaining supported manifest inspection data.
- [x] 4.5 Remove active managed-auto-skill concepts from developer behavior-testing skills, case catalogs, fixtures, system-skill boundaries, and tests; replace relevant evidence fields and cases with native prompt projection evidence.

## 5. Kimi 0.34 Compatibility and Qualification

- [x] 5.1 Update the deprecated Kimi CAO compatibility adapter to emit a valid Kimi 0.34 Markdown agent file with `${base_prompt}` and all-placeholder validation, and add command/profile tests without extending CAO resume support.
- [x] 5.2 Replace selectable pre-0.34 Kimi TUI signal profiles and fixture metadata with a `>=0.34.0` registration with no upper bound; mark any retained older recordings historical and exclude them from maintained selection.
- [ ] 5.3 Capture and manually label fresh unattended Kimi 0.34.x high-rate headless/TUI evidence for startup, ready, active, approval, queued input, fresh session, and resumed session behavior, including proof that no role-bootstrap turn occurs.
- [ ] 5.4 Run strict and sparse recorded replay against the new 0.34.x corpus, update source-backed detector rules where evidence requires it, and keep the profile unmaintained until all required qualification cells pass.
- [ ] 5.5 Run live integration coverage with the repository's Kimi fixture credentials for composed prompt delivery, built-in prompt retention, skills and `AGENTS.md` visibility, unattended TUI startup, headless turns, and supported relaunch.

## 6. Documentation and Breaking Migration

- [x] 6.1 Update README and getting-started pages to require Kimi 0.34.0 or later with no upper limit, describe native managed-home role delivery, and remove every manual auto-skill, pre-0.34, and role-bootstrap instruction.
- [x] 6.2 Update build-phase launch-policy and run-phase backend, role-injection, lifecycle, and relaunch references with `SYSTEM.md`, `${base_prompt}`, placeholder rejection, precedence, engine, provenance, and minimum-version details.
- [x] 6.3 Update CLI and system-skill references for the removed self-prompt command, deleted auto-skill category, and v5 static system-skill manifest while preserving admin/agent pack behavior.
- [x] 6.4 Document the required clean brain rebuild and fresh-session boundary, including explicit diagnostics for stale auto-skill homes or old role-injection manifests and the release-level-only rollback posture.

## 7. Verification

- [x] 7.1 Run targeted unit and runtime tests for prompt projection, launch policy, brain building, manager commands, system skills, Kimi backends, manifests, provider adapters, and TUI tracking.
- [x] 7.2 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, and `pixi run test-runtime`, and resolve every regression caused by the breaking removal.
- [x] 7.3 Run strict OpenSpec validation and repository scans proving that no active code, schema, test, skill, README, or maintained documentation still selects `auto_skill_system_prompt`, exposes `houmao-auto-system-prompt`, documents `agents self system-prompt show`, or claims pre-0.34 Kimi support.
