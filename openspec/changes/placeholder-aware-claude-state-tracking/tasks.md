## 1. Claude Prompt Classification

- [ ] 1.1 Add Claude prompt-area snapshot and behavior-classification helpers that inspect raw prompt rendering and distinguish placeholder, draft, empty, and unknown prompt states.
- [ ] 1.2 Update the selected Claude tracked-TUI detector profile to derive `surface.editing_input` from Claude prompt classification instead of ANSI-stripped prompt text alone.
- [ ] 1.3 Make unrecognized Claude prompt rendering degrade conservatively so styled placeholder content does not fall back to `editing_input=yes` by default.

## 2. Versioned Profile Integration

- [ ] 2.1 Refactor Claude prompt interpretation so version-family profiles can select profile-private prompt behavior variants without changing shared reducer APIs.
- [ ] 2.2 Add only the raw shared surface helpers Claude needs for prompt-region inspection while keeping placeholder semantics inside Claude-owned profile code.
- [ ] 2.3 Preserve existing detector notes or add new debug notes so placeholder-vs-draft decisions remain diagnosable in live-watch and replay artifacts.

## 3. Regression Coverage

- [ ] 3.1 Add unit fixtures and tests for raw ANSI Claude startup or idle placeholder surfaces that must classify as `surface.editing_input=no`.
- [ ] 3.2 Add unit tests for real Claude draft input and unrecognized prompt rendering to verify draft behavior still reports editing and ambiguous rendering stays conservative.
- [ ] 3.3 Run targeted shared TUI tracking tests and at least one Claude live-watch smoke check to confirm fresh startup no longer reports placeholder text as active editing.
