## 1. Gemini Unattended Launch Policy

- [x] 1.1 Update the maintained Gemini unattended launch-policy strategy so runtime-owned `gemini_headless` launches apply `--approval-mode yolo` and `--sandbox false` on top of the headless `-p` flow.
- [x] 1.2 Extend Gemini unattended launch-surface normalization so conflicting caller-supplied approval, sandbox, or equivalent weakening startup inputs are removed or replaced before provider start.
- [x] 1.3 Define how Gemini unattended runtime-home config ownership handles copied setup or settings values that would weaken the maintained approval, sandbox, or tool-availability posture, and implement the minimal required override path.

## 2. Verification Coverage

- [x] 2.1 Add or update launch-policy and runtime unit tests that assert the effective Gemini unattended command and conflict-replacement behavior for initial and resumed turns.
- [x] 2.2 Add or update Gemini runtime or integration coverage showing a managed unattended Gemini session can use shell/file tools during a direct prompt with the maintained OAuth fixture.
- [x] 2.3 Add or update gateway/demo coverage showing Gemini unattended can process a gateway-notified email task without losing required tools from the active registry.

## 3. Documentation

- [x] 3.1 Update `docs/reference/build-phase/launch-policy.md` to document Gemini unattended launch ownership, including approval-mode, sandbox posture, and replacement of conflicting startup inputs.
- [x] 3.2 Review Gemini-facing easy/demo documentation for stale “read-only-compatible” wording and align any maintained references with the new unattended full-permission posture.
