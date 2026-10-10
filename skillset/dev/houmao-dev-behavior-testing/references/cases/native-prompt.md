# Native System-Prompt Cases

Functional area: `native-prompt`

## Workflow

1. **Resolve one native-prompt case or lifecycle variant** from this page.
2. **Apply functional-area defaults** and expand them into the run manifest.
3. **Capture provider-native prompt method, projection state, prompt digests, and provider-start ordering** before the first substantive turn.
4. **Judge construction, provider-start verification, and post-lifecycle persistence separately.**

If a maintained provider does not expose a declared projection artifact, capture its native launch method and prompt digest instead. Do not substitute a chat message, skill invocation, or agent claim for provider-native evidence.

## Functional-Area Defaults

- Case revision: `1` for every listed case.
- Providers: `claude`, `codex`, and `kimi` when the maintained managed lifecycle supports them.
- Driver invocation: `not-applicable`; stimulus origin `lifecycle`.
- Repetitions: `3` fresh managed contexts per provider and lifecycle variant.
- Timeout: use the maintained construction, launch, or relaunch completion boundary.
- Permitted effects: run root, isolated tool home, disposable project, and case-owned managed resources only.
- Evidence: role-prompt digest, native method, provider-start ordering, launch/session provenance, bounded home diff when applicable, transcript, and final response.
- Cleanup: stop case-owned sessions and agents; remove isolated homes and disposable projects after evidence freeze.

## Cases

| ID | Introduced At | Context / Pack / Native Prompt | Exact Stimulus | Expected Root and Behavior | Required Observables | Forbidden Observables | Driver Invocation Mode | Stimulus Origin | Activation Mode | Expected Initial Root | Expected Delegated Roots | Expected Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `NSP-001` | `minimal` | `managed-agent` / agent / native-required | Launch a fresh managed agent whose role contains the frozen marker, then submit `State your assigned role in one sentence.` | Provider-native role delivery exists before the first turn | Complete effective-prompt digest; native method; provider-start verification before prompt submission; response consistent with the frozen role | Chat role-bootstrap turn; prompt-loading skill; first task turn before native verification | `not-applicable` | `lifecycle` | `lifecycle` | `none` | `none` | native prompt delivery |
| `NSP-002` | `normal` | `managed-agent` / agent / native-required | Build a disposable role whose prompt contains each frozen `${identifier}` sample, one sample per attempt. | Construction rejects every placeholder-shaped token before provider launch | Exact rejected token and deterministic diagnostic; no provider process; no partial prompt projection | Accepted placeholder; provider launch; silent rewriting or escaping | `not-applicable` | `lifecycle` | `lifecycle` | `none` | `none` | native prompt validation |
| `NSP-003` | `extended` | `managed-agent` / agent / absent-required | Seed the disposable managed home with a stale native prompt artifact, then rebuild it with an empty role prompt. | Rebuild removes the stale provider-native prompt surface | Before/after home diff; projection state `removed`; absent effective and rendered digests; no provider process | Stale prompt retained; empty native prompt artifact; unrelated home mutation | `not-applicable` | `lifecycle` | `lifecycle` | `none` | `none` | stale projection removal |
| `NSP-004` | `complete` | `lifecycle-reload` / agent / native-required | After the selected maintained lifecycle event, submit `Continue the pending task.` | The same frozen effective role remains provider-native before continuation | Pre-event and post-event method plus digest evidence; provider-start verification for relaunch; role-consistent continuation | Chat role-bootstrap turn; prompt-loading skill; changed digest without an authorized role change; continuation before verification | `not-applicable` | `lifecycle` | `lifecycle` | `none` | `none` | native prompt persistence |

## NSP-002 Placeholder Matrix

Freeze at least `${cwd}`, `${project_name}`, and one previously unknown valid identifier such as `${future_provider_value}` as separate attempts. Add new valid identifier forms when the product validator expands; do not replace the unknown-identifier cell with a list of provider-known variables.

## NSP-004 Lifecycle Variants

| Variant ID | Lifecycle Event | Exact Stimulus |
| --- | --- | --- |
| `rebuild` | Clean managed-brain rebuild followed by a fresh provider session | `Continue the pending task.` |
| `relaunch` | Supported managed-agent relaunch from a brain built by the current release | `Continue the pending task.` |

Every variant preserves the same oracle and runs three fresh attempts per supported provider. Each inherits `driver_invocation_mode=not-applicable`, `stimulus_origin=lifecycle`, `activation_mode=lifecycle`, `expected_initial_root=none`, no delegated roots, and the native prompt persistence route.

Canonical selectors: `NSP-004/rebuild` and `NSP-004/relaunch`.

## Kimi Evidence Boundary

For Kimi Code, qualify version 0.34.0 or later with no upper bound. Required native evidence includes managed `$KIMI_CODE_HOME/SYSTEM.md`, canonical `${base_prompt}` preservation, the effective and rendered SHA-256 digests, `KIMI_CODE_LEGACY_FLAG=0`, successful precedence validation, and proof that no role instruction was submitted as a conversational turn.

## Guardrails

- DO NOT report lifecycle prompt projection as automatic driver-origin skill discovery.
- DO NOT use a role-consistent answer as the only proof of native delivery.
- DO NOT reuse pre-event provider-start evidence for the relaunch variant.
- DO NOT preserve provider credentials, hidden reasoning, or the full secret-bearing environment in evidence.
