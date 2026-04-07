## 1. Prompt Composition

- [x] 1.1 Add a shared managed-prompt-header composition helper that renders the general Houmao-managed header from resolved managed identity and policy.
- [x] 1.2 Update local managed launch and easy delegated launch to resolve managed-header policy, compose the effective launch prompt after prompt-overlay resolution, and persist the effective prompt plus structured managed-header metadata in the build manifest.
- [x] 1.3 Update runtime relaunch and compatibility-generated provider profile paths to reuse the same managed-prompt composition contract, including the default-on recompute path for older manifests that lack managed-header metadata.

## 2. Launch Policy Storage And CLI

- [x] 2.1 Extend shared launch-profile storage, projection payloads, and inspection payloads with the optional tri-state managed-header policy.
- [x] 2.2 Add `--managed-header` and `--no-managed-header` to `houmao-mgr agents launch` and enforce one-shot override precedence without rewriting stored profile state.
- [x] 2.3 Add managed-header policy controls to `houmao-mgr project agents launch-profiles add/set` and report the stored policy from `get`.
- [x] 2.4 Add managed-header policy controls to `houmao-mgr project easy profile create` and one-shot override controls to `houmao-mgr project easy instance launch`.
- [x] 2.5 Add or update focused tests for launch-profile storage, launch-time precedence, promptless managed-launch behavior, compatibility prompt generation, and relaunch fallback for older manifests.

## 3. Docs And Verification

- [x] 3.1 Update the launch-profiles guide, easy-specialists guide, and CLI reference to document the managed prompt header, its general wording, its composition order, and its opt-out semantics.
- [x] 3.2 Run `openspec validate add-managed-prompt-header` and the focused unit or integration tests covering launch profiles, managed launch, easy launch, and compatibility prompt generation.
