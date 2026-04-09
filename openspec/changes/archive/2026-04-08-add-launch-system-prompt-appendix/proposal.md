## Why

Managed launch already composes several prompt-owned inputs into one effective launch prompt, but operators cannot add a one-shot launch-only appendix without editing the role prompt or storing a reusable profile overlay. That makes quick launch-specific guidance awkward, and the current flat string composition does not expose clear structure once managed header, role content, and overlays all participate.

## What Changes

- Add optional one-shot launch-time system-prompt appendix input to maintained managed launch surfaces so an operator can append extra prompt content for the current launch only.
- Render the effective launch prompt as one Houmao-owned structured envelope rooted at `<houmao_system_prompt>` with explicit section tags for the managed header, prompt body, role prompt, launch-profile overlay, and launch appendix.
- Extend effective prompt composition so the launch appendix is appended after launch-profile overlay resolution while preserving current overlay semantics and managed-header policy precedence.
- Persist secret-free prompt-layout metadata alongside the final rendered launch prompt so relaunch, resume, and compatibility prompt generation reuse the same structured prompt contract.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `brain-launch-runtime`: change effective launch-prompt composition and persistence so launch-owned appendix input and structured prompt layout survive build, launch, resume, and compatibility generation.
- `managed-launch-prompt-header`: change the managed-header composition contract from flat marker-delimited text to a section within the `<houmao_system_prompt>` envelope and extend composition order with the launch appendix.
- `houmao-mgr-agents-launch`: add one-shot launch-owned appendix options for `houmao-mgr agents launch`.
- `houmao-mgr-project-easy-cli`: add the same one-shot launch-owned appendix options for delegated `houmao-mgr project easy instance launch`.

## Impact

- Affected code: managed prompt composition helpers, brain-manifest prompt persistence, runtime relaunch/resume prompt reconstruction, launch CLI parsing, and compatibility prompt generation.
- Affected APIs: `houmao-mgr agents launch` and `houmao-mgr project easy instance launch` gain new launch-only prompt appendix options.
- Affected state: built manifests gain structured prompt-layout metadata in addition to the final rendered prompt text.
- Affected tests/docs: prompt-composition unit coverage, launch-surface CLI tests, manifest persistence tests, and prompt-composition reference docs.
