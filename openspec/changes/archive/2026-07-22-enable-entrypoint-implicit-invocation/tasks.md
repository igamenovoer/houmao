## 1. Correct Entrypoint Activation and Trigger Policy

- [x] 1.1 Change the admin and agent entrypoint manifest records to `narrow-implicit` without changing pack membership, default lanes, route lists, dependencies, or static source paths.
- [x] 1.2 Set both entrypoint `agents/openai.yaml` policies to `allow_implicit_invocation: true` and describe their broad actor-scoped trigger: any semantically Houmao-related request in the matching operator or genuine managed-agent context.
- [x] 1.3 Keep admin welcome, shared routines, pro loop, lite loop, and every parent-scoped shared child explicit-only in manifest and host metadata; set admin welcome `allow_implicit_invocation: false`.
- [x] 1.4 Update manifest validation invariants so exactly two implicit roots and four explicit standalone roots are checked, with parent-scoped shared children remaining explicit-only.
- [x] 1.5 Rewrite both entrypoint workflows to classify informational versus operational intent before target checks, identity checks, route selection, or delegation.
- [x] 1.6 Remove automatic admin-entrypoint delegation to welcome for empty and welcome-style requests; answer locally and recommend explicit `$houmao-admin-welcome` only when a tour would help.
- [x] 1.7 Make the agent entrypoint skip identity verification for informational requests and require exact fresh `houmao-mgr --print-json agents self identity` verification before substantive routing for operational requests.

## 2. Preserve Deployment and Prompt Boundaries

- [x] 2.1 Retain manual CLI default installation of the admin pack and managed launch and join default installation of the agent pack, with no actor-pack membership changes.
- [x] 2.2 Retain complete static copy and symlink projection with no runtime skill composition or generated subskill tree.
- [x] 2.3 Keep generated mailbox and notifier prompts explicitly routed through the agent entrypoint and classify those generated prompts as non-driver-origin rather than automatic discovery tests.
- [x] 2.4 Update system-skill list, README, overview, and CLI reference activation descriptions so actor entrypoints are broad implicit roots while welcome, shared routines, and loops remain explicit direct roots.
- [x] 2.5 Document and validate actor-context selection for explicitly combined-pack homes: raw operator sessions select admin, and genuine managed sessions select agent, without treating prompt wording as managed identity.

## 3. Extend the Behavior Case Schema and Selectors

- [x] 3.1 Advance the committed behavior catalog to `houmao-dev-behavior-cases.v3` and add `driver_invocation_mode`, stimulus origin, expected initial root, expected delegated roots, and expected route to the resolved case contract.
- [x] 3.2 Classify every existing case and stable variant as manual, automatic, or not applicable according to the driving-stimulus contract, preserving unchanged case meaning and revision.
- [x] 3.3 Add `<area>/<manual|automatic>/<profile>` and `all/<manual|automatic>/<profile>` selectors with stable profile expansion, mode filtering, union, deduplication, validation, and no-selector help.
- [x] 3.4 Freeze invocation mode, stimulus origin, initial-root oracle, delegated-root oracle, exact stimulus digest, and contributing selectors in every planned run manifest.
- [x] 3.5 Update list, planning, suite, artifact, verdict, and report references to distinguish manual invocation, automatic informational selection, automatic operational selection, automatic intentional non-selection, and non-driver-origin results.

## 4. Revise and Add Committed Behavior Cases

- [x] 4.1 Advance `ACT-001` to revision 2 so its natural first-use Houmao question selects the admin entrypoint, receives local informational guidance, and may receive a manual welcome recommendation without welcome activation or delegation.
- [x] 4.2 Advance `ACT-003` to revision 2, move it to minimal, and require implicit admin-entrypoint selection followed by the inspect route for its existing natural operator stimulus.
- [x] 4.3 Add minimal `ACT-005` with stable informational and operational managed-agent variants: the informational variant skips identity and delegation, while the operational variant requires exact fresh identity before downstream routing.
- [x] 4.4 Add extended `ACT-006` raw-operator and genuine-managed variants for actor-entrypoint disambiguation in an explicitly combined-pack home.
- [x] 4.5 Advance `ADM-002` to revision 2 so an empty explicit admin-entrypoint invocation stays local, recommends manual welcome when useful, and does not delegate.
- [x] 4.6 Add normal `SHR-009` admin and managed-agent variants that select the matching entrypoint first and then delegate to one intended shared child without direct implicit shared-root selection.
- [x] 4.7 Advance `LOOP-001` to revision 2 so generic loop wording may select the admin entrypoint but still forbids automatic pro or lite choice and filesystem mutation.
- [x] 4.8 Add normal `LOOP-008` admin-pro and agent-lite variants that use natural wording to distinguish the loop, select the actor entrypoint first, and delegate to the correct top-level loop sibling.
- [x] 4.9 Update catalog links, stable variant selectors, tags where applicable, and cumulative counts to global `13/25/45/46` and the specified version 3 per-area totals.

## 5. Add Deterministic Validation Coverage

- [x] 5.1 Update system-skill manifest and metadata tests for exactly two implicit actor entrypoints, explicit welcome, shared, and loop roots, explicit parent-scoped children, and unchanged admin-versus-agent default deployment.
- [x] 5.2 Add behavior-catalog tests for the 46 stable case ids, version 3 profile counts, unique invocation-mode classification, mode-aware selectors, stable variants, and valid local links.
- [x] 5.3 Add integrity tests that reject skill handles in automatic driver stimuli, missing intended handles in manual stimuli, invalid not-applicable origins, automatic welcome activation or delegation, and explicit-only roots declared as automatic initial roots.
- [x] 5.4 Update semantic-preservation coverage to retain every unchanged version 2 stimulus and oracle while allowing only the four revision-2 cases and four new cases declared by this change.
- [x] 5.5 Add focused assertions that informational agent requests skip identity, operational agent requests verify identity before routing, generated-prompt and lifecycle cases are not driver automatic discovery, and downstream shared or loop routing is not direct implicit selection.
- [x] 5.6 Validate combined-pack actor disambiguation metadata and case structure while keeping live provider attempts manual and credential-gated.
- [x] 5.7 Add focused manual-invocation coverage for `$houmao-admin-welcome` and prove that entrypoint recommendations do not activate or delegate to welcome.

## 6. Verify the Change

- [x] 6.1 Run the focused development behavior-testing and system-skill unit tests.
- [x] 6.2 Run the skill-creator validator and retain only the established generic-validator exception for Imsight `skill_invocation_notation` if it remains.
- [x] 6.3 Run `pixi run format`, `pixi run lint`, and `git diff --check`.
- [x] 6.4 Run strict OpenSpec validation for `enable-entrypoint-implicit-invocation` and mark every completed task accurately.
