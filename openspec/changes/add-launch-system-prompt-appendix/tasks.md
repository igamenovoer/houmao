## 1. Structured Prompt Composer

- [x] 1.1 Add a shared structured prompt-composition model and renderer for `<houmao_system_prompt>` with `managed_header`, `prompt_body`, `role_prompt`, `launch_profile_overlay`, and `launch_appendix` sections.
- [x] 1.2 Update managed-launch prompt assembly to use the structured renderer while preserving managed-header policy behavior and launch-profile append/replace semantics.
- [x] 1.3 Persist secret-free `houmao_system_prompt_layout` metadata together with the final rendered effective launch prompt during brain construction.

## 2. Launch Surface Integration

- [x] 2.1 Add `--append-system-prompt-text` and `--append-system-prompt-file` parsing and validation to `houmao-mgr agents launch`, then thread the launch-owned appendix into managed local launch composition.
- [x] 2.2 Add the same appendix options and validation to `houmao-mgr project easy instance launch`, then forward the appendix through delegated native managed launch without rewriting stored easy profiles or specialists.
- [x] 2.3 Update relaunch, resume, and compatibility prompt generation paths to reuse the structured rendered prompt contract and the new layout metadata for newly built manifests while preserving fallback behavior for older manifests.

## 3. Verification And Reference Updates

- [x] 3.1 Add or update unit tests for structured prompt rendering, replace-overlay omission of `role_prompt`, appendix ordering, and manifest persistence of `houmao_system_prompt_layout`.
- [x] 3.2 Add or update CLI tests for both launch surfaces covering text/file appendix input, mutual exclusion validation, and one-shot non-persistence behavior.
- [x] 3.3 Update prompt-composition and launch-surface reference docs to describe the `<houmao_system_prompt>` layout and the new launch-owned appendix options.
