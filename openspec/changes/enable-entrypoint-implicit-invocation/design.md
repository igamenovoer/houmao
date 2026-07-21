## Context

The v4 static system-skill collection separates installation, discovery, and routing. The CLI-default admin pack contains the welcome skill, admin entrypoint, shared routines, and both loop siblings. Managed launch and join contain the agent entrypoint, shared routines, and both loop siblings. That deployment split is correct, but the manifest and both entrypoint `agents/openai.yaml` files currently declare explicit-only activation, while welcome is narrowly implicit. Natural Houmao requests therefore cannot reliably select the actor router, and informational operator requests can select welcome instead of the router that should own all automatic Houmao dispatch.

The behavior catalog inherited those assumptions. `ACT-001` expects automatic welcome selection, `ACT-003` expects no entrypoint for a concrete operator inspection request, `ADM-002` expects an empty explicit admin entrypoint to delegate to welcome, and `LOOP-001` observes only that neither loop root should activate. Most other route cases invoke an exact `$houmao-*` handle, so the suite does not independently qualify broad automatic entrypoint selection, informational-versus-operational phases, or downstream delegation.

The public entrypoints, welcome, shared routines, and loops are static sibling skill trees. This change must retain copy-paste and Skills CLI installation, avoid runtime composition, preserve shared and loop operational meaning, and follow the Imsight skill-handling format already used by the roots and the development behavior-testing skill.

## Goals / Non-Goals

**Goals:**

- Make the admin and agent entrypoints narrowly implicit for all Houmao-related requests within their intended actor contexts.
- Make welcome strictly manual and remove automatic entrypoint-to-welcome delegation.
- Classify informational versus operational requests before identity, target, or sibling work.
- Keep shared routines and both loop roots explicit as initial host-selected skills while allowing an entrypoint to delegate to them.
- Preserve manual operator installation of the admin pack and automatic agent-pack installation during managed launch and join.
- Add committed behavior cases that distinguish direct `$skill` prompts from natural-context prompts and test both entrypoint phases.
- Record initial root selection separately from downstream sibling delegation.
- Preserve reproducible functional-area and cumulative-coverage selection.

**Non-Goals:**

- Treat an incidental occurrence of the word `Houmao` in otherwise unrelated material as a Houmao request.
- Make welcome, shared routines, pro loop, or lite loop eligible for direct implicit host selection.
- Change any shared child, loop operation, target gate, runtime authorization rule, pack member, or installation projection.
- Verify managed identity for informational-only entrypoint responses.
- Treat generated runtime prompts or lifecycle bootstrap events as driver-origin automatic discovery cases.
- Generate cases from the runtime manifest, dynamically compose installed skill content, or execute live provider qualification as a repository unit test.

## Decisions

### 1. Treat Installation and Activation as Separate Constraints

Keep `defaults.cli = ["admin"]`, `defaults.managed_launch = ["agent"]`, and `defaults.managed_join = ["agent"]`, together with current pack membership. The CLI default is selected only after a user runs the installer; it is not automatic injection into an operator agent. Managed construction and join continue to project only the agent pack by default.

Change the two entrypoint manifest records from `explicit` to `narrow-implicit` and synchronize their OpenAI policy to `allow_implicit_invocation: true`. Change welcome from `narrow-implicit` to `explicit` and set its OpenAI policy to `false`. Keep shared routines and both loop roots explicit with `allow_implicit_invocation: false`.

Changing pack composition was rejected because the current actor deployment boundary already matches intended ownership. Making every public root implicit was rejected because it would bypass the actor router and weaken identity and target selection.

### 2. Use One Precedence-Ordered Trigger Contract

An explicit `$houmao-*` handle wins over implicit discovery and selects the named installed root. Without an explicit handle, classify the requested outcome semantically:

1. If the subject or requested outcome does not concern Houmao, select no Houmao root.
2. If it concerns Houmao in a human-operator context, select `houmao-admin-entrypoint`.
3. If it concerns Houmao in a genuine managed-agent context, select `houmao-agent-entrypoint`.

Houmao-related requests include explanation, command or route learning, state inspection, incomplete operations, and executable operations involving Houmao projects, credentials, definitions, specialists, agents, mailboxes, messaging, gateways, memory, workspaces, graphing, AG-UI, lifecycle, or loops. A raw token occurrence in unrelated text is insufficient; the subject or requested outcome must depend on Houmao domain knowledge, state, or action.

Restricting implicit selection to fully specified operations was rejected because missing targets and inputs are post-trigger gates owned by the entrypoint. Making any literal token occurrence sufficient was rejected because an unrelated summarization or code-editing task may contain the word without requesting Houmao behavior.

### 3. Make Welcome Strictly Manual

Only an explicit `$houmao-admin-welcome ...` invocation selects welcome. A natural first-contact, route-comparison, command-learning, or guided-tour request selects the admin entrypoint, which returns concise read-only information and may recommend the exact manual welcome command. It never invokes welcome automatically.

An empty `$houmao-admin-entrypoint` invocation and retained welcome-style compatibility subcommands remain read-only entrypoint requests. They return entrypoint guidance and a manual welcome recommendation rather than delegating. Once welcome is explicitly invoked, it remains read-only and may hand an actionable task outward to the admin entrypoint under its existing safety contract.

Keeping welcome as a competing implicit root was rejected because automatic ownership should resolve to exactly one actor entrypoint. Treating entrypoint-to-welcome delegation as compatible with manual-only welcome was rejected because the user selected literal manual invocation semantics.

### 4. Use a Shared Phase Model with an Agent-Only Identity Gate

Both entrypoints use these conceptual phases:

1. **Classify intent** as informational, operational, unrelated, unsupported, or an explicitly selected downstream route.
2. **Handle informational intent locally** with read-only guidance, no target discovery, and no sibling loading. The admin entrypoint may recommend manual welcome. The agent entrypoint does not verify identity for informational-only output.
3. **Establish operational actor posture**. Admin sets an immutable admin frame. Agent runs exactly `houmao-mgr --print-json agents self identity`, validates fresh evidence, and fails closed before substantive routing when verification fails.
4. **Select exactly one eligible route**. Ordinary work maps to shared routines; explicitly distinguished pro or lite work maps to that loop sibling; generic loop wording asks for the required choice.
5. **Resolve target and required inputs**. Missing values cause one focused question rather than preventing initial activation or authorizing a guess.
6. **Delegate** with the complete immutable sibling handoff frame.
7. **Handle lifecycle transition** for the admin join route without mutating the current actor frame in place.
8. **Report the outcome** with material actor, target, route, and evidence.

Verifying managed identity before intent classification was rejected because informational questions should remain command-free, matching the existing explicit-help posture. Deferring identity until a child needs self was rejected because the agent entrypoint owns actor verification for every operational route.

### 5. Keep Downstream Siblings Explicit as Initial Roots

After automatic entrypoint selection, ordinary work may delegate to `houmao-shared-routines`, and a request that explicitly distinguishes pro or lite may delegate to the corresponding loop sibling. Downstream access is recorded as delegation, not direct implicit sibling selection. Generic loop wording may activate the actor entrypoint but must not select pro or lite until the user distinguishes the desired loop.

Direct advanced users retain manual `$houmao-shared-routines`, `$houmao-agent-loop-pro`, and `$houmao-agent-loop-lite` invocation. Calling these roots directly from automatic context was rejected because it bypasses the actor-specific entrypoint.

### 6. Use Actor Context to Disambiguate Installations

Entrypoint descriptions and metadata keep their actor restrictions explicit: the admin entrypoint acts for a human operator, while the agent entrypoint applies only in a genuine Houmao-managed session. Managed self remains established for operational work by runtime context and the exact identity command, never by prompt wording.

The installer may continue to support an explicitly requested combined pack. In that advanced configuration, raw operator context must not select the agent entrypoint, and genuine managed context must not select the admin entrypoint. Focused metadata tests and an extended live disambiguation case cover this boundary without banning combined installation.

Disallowing combined packs was rejected because it is a separate lifecycle policy change and shared receipt ownership already supports the combination. Allowing prompt text to choose the actor was rejected because it would undermine immutable actor-frame rules.

### 7. Add a Driver-Invocation Axis without Overloading Runtime Origins

Add `driver_invocation_mode` to case records with these values:

- `manual`: the driving agent submits an exact prompt containing the intended top-level `$houmao-*` invocation.
- `automatic`: the driving agent submits natural task context without a `$houmao-*` handle and the oracle evaluates automatic selection or intentional non-selection.
- `not-applicable`: the tested stimulus originates from maintained generated-prompt or lifecycle machinery rather than a direct driving-agent prompt.

Add `expected_initial_root` and `expected_delegated_roots` so a case can distinguish implicit actor selection from explicit sibling routing. Preserve `expected_route` for the final child or operation path. Invocation mode describes how the driving prompt reaches the tested agent; it does not replace activation verdict or stimulus-origin evidence.

Forcing generated prompts and lifecycle cases into `automatic` was rejected because those prompts may contain explicit skill handles and do not test natural-context discovery. Replacing the existing activation field was rejected because invocation stimulus and observed activation are independent dimensions.

### 8. Add Mode-Aware Selectors while Preserving Existing Selectors

Add canonical `<functional-area>/<manual|automatic>/<coverage-profile>` and `all/<manual|automatic>/<coverage-profile>` selectors. Existing `<functional-area>/<coverage-profile>` and `all/<coverage-profile>` selectors continue to resolve every invocation mode in that functional slice, including applicable generated and lifecycle cases. Exact case, exact variant, tag, bare-area, and composite selectors retain their current meanings.

The frozen run manifest records the requested mode-aware selectors, each resolved cell's driver invocation mode, exact stimulus source, initial-root oracle, delegated-root oracle, and contributing selectors. Reports show selected and qualified counts separately for manual, automatic-positive, automatic-non-activation, and non-driver-origin cases.

Replacing existing selectors was rejected because functional coverage runs still need generated and lifecycle cases. Treating invocation modes as tags was rejected because the mode is required schema data with validation rules, not an optional overlapping diagnostic label.

### 9. Advance the Catalog to Version 3 with Four New Cases

Advance the catalog to `houmao-dev-behavior-cases.v3` and add these committed cases:

- `ACT-005` at `minimal`: an informational variant naturally asks a managed agent about its Houmao capabilities and expects agent-entrypoint selection without identity verification; an operational variant naturally requests eligible self work and expects fresh identity before delegation.
- `ACT-006` at `extended`: raw-operator and genuine-managed variants run from an explicitly combined-pack home and require the actor entrypoint matching execution context rather than prompt wording.
- `SHR-009` at `normal`: admin and managed-agent natural-prompt variants select their actor entrypoint first and then delegate to the intended shared child without direct implicit shared-root selection.
- `LOOP-008` at `normal`: admin-pro and agent-lite natural-prompt variants explicitly identify the desired loop in ordinary language, select the actor entrypoint first, and then delegate to the named top-level loop sibling without making either loop directly implicit.

Advance these existing cases to revision 2 because their semantic oracles change:

- `ACT-001`: a natural first-use Houmao question selects the admin entrypoint, receives local informational guidance, and may receive a manual welcome recommendation; welcome must not activate or be delegated.
- `ACT-003`: a natural operator inspection request selects the admin entrypoint and then the inspect route; move it from normal to minimal.
- `ADM-002`: an empty explicit admin-entrypoint invocation returns local read-only entrypoint guidance and a manual welcome recommendation without delegating.
- `LOOP-001`: generic loop wording may select the admin entrypoint but still forbids automatic pro or lite choice and filesystem mutation.

Every other existing case keeps its id, revision, exact stimulus, and semantic oracle. Existing manual welcome coverage remains through explicit welcome cases, including the `ACT-004/admin-welcome` root variant.

The resulting cumulative case-record counts before matrix expansion are 13, 25, 45, and 46 for `all/minimal`, `all/normal`, `all/extended`, and `all/complete`. Per-area counts become activation `4/5/6/6`, managed bootstrap `1/1/2/2`, admin entrypoint `1/3/8/9`, agent entrypoint `1/3/9/9`, shared routines `2/5/9/9`, agent loops `3/6/8/8`, and generated prompts `1/2/3/3`.

Duplicating every manual case as an automatic case was rejected because many explicit advanced and failure-injection routes are not natural discovery surfaces. Stable variants cover informational and operational agent phases without increasing the case-record count.

### 10. Validate Static Policy and Case Integrity Deterministically

Update manifest validation and focused tests to require narrow implicit activation for exactly the two actor entrypoints and explicit activation for welcome, shared routines, and both loop roots. Validate synchronized OpenAI metadata and actor-specific descriptions. Keep generated mailbox and notifier prompts explicitly routed through the agent entrypoint; they remain generated-prompt cases rather than evidence of implicit discovery.

Behavior-catalog structural tests require exactly one driver invocation mode per case or variant, forbid `$houmao-*` handles in automatic driver stimuli, require the intended handle in manual driver stimuli, restrict `not-applicable` to generated-prompt and lifecycle origins, validate initial-versus-delegated roots against packaged policy, preserve old case semantics except for the four declared revision-2 cases, and assert version 3 ids and cumulative counts.

The behavior-testing skill remains an explicit-only development skill. Its top-level router stays concise, and mode-specific detail remains in linked references and command pages according to the existing Imsight complex-procedure format.

## Risks / Trade-offs

- [Broad implicit triggering may capture unrelated work containing Houmao text] → Define relevance by the requested subject or outcome rather than raw token occurrence and retain an unrelated-task negative case.
- [Informational agent responses are not identity-verified] → Prohibit operational routing, target claims, and sibling loading until fresh identity succeeds.
- [Providers expose different skill-selection telemetry] → Preserve activation as a dimensional verdict and report unobservable selection rather than infer it from final prose.
- [Entrypoint delegation could be mistaken for direct shared or loop activation] → Record initial root, delegated roots, and final route independently in case schema and evidence.
- [Mode-aware selectors increase catalog complexity] → Use one required field, two canonical driver modes, stable selector grammar, and existing deterministic union rules.
- [Combined-pack installations can select the wrong actor] → Keep descriptions context-specific and cover raw versus managed actor disambiguation as extended behavior.
- [Changing four existing oracles breaks historical comparison] → Increment `ACT-001`, `ACT-003`, `ADM-002`, and `LOOP-001` to revision 2 and retain frozen older run manifests by catalog digest.

## Migration Plan

1. Update activation metadata and validation invariants without changing pack membership or projection.
2. Update system-skill trigger descriptions, informational and operational phases, manual welcome behavior, and documentation.
3. Advance the behavior catalog and schema, revise the four affected cases, add the four new cases and variants, and update selectors and reports.
4. Update structural tests, generated-prompt assertions, profile counts, and semantic-preservation snapshots.
5. Run focused unit tests, skill validation with the established Imsight notation exception, formatting, lint, diff checks, and strict OpenSpec validation.

Rollback restores explicit entrypoint activation metadata, implicit welcome activation, automatic entrypoint-to-welcome delegation, and catalog version 2 with previous case oracles. No installed-skill receipt migration is required; copied installations update through the normal upgrade path, and symlink installations observe source metadata directly.

## Open Questions

None. Automatic selection means actor-entrypoint discovery from a Houmao-related driver prompt without a skill handle. Explicit skill handles take precedence; generated prompt delivery, lifecycle bootstrap, and entrypoint-to-sibling delegation remain separately observable mechanisms.
