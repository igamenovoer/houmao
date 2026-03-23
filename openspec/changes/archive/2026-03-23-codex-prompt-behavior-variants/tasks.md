## 1. Prompt Behavior Boundary

- [x] 1.1 Refactor the existing Codex `build_prompt_context()` seam into a prompt-area snapshot model that preserves bounded raw prompt-region context for prompt behavior variants without exposing tracker-engine internals.
- [x] 1.2 Add a `CodexPromptBehaviorVariant` `Protocol` plus frozen dataclass result/value objects that classify prompt-area snapshots into coarse prompt kinds and debug metadata.
- [x] 1.3 Implement an initial prompt behavior variant for the current Codex version family and a conservative fallback variant for unrecognized or missing-version cases.

## 2. Versioned Codex Profile Selection

- [x] 2.1 Split Codex tracked-TUI detection into version-visible profile registrations with an initial concrete `0.116.x` family (`minimum_supported_version=(0, 116, 0)`) plus fallback in the shared tracker registry.
- [x] 2.2 Wire each selected Codex profile to its profile-private prompt behavior variant and ensure detector/variant identity can be surfaced through profile-owned notes for debugging.

## 3. Editing-State Integration

- [x] 3.1 Refactor Codex prompt handling so `editing_input` derives from the prompt behavior result instead of detector-local placeholder literal heuristics.
- [x] 3.2 Ensure prompt-visible unrecognized prompt presentation degrades to `editing_input=unknown` with diagnostic notes rather than manufacturing `editing_input=yes` or `editing_input=no`.
- [x] 3.3 Update Codex tracker/debug outputs as needed so live-watch and replay artifacts show which prompt behavior family classified the surface.

## 4. Verification

- [x] 4.1 Add ANSI-backed unit fixtures/tests for placeholder, real draft, disabled-input composer, dynamic placeholder, and unrecognized prompt presentation cases.
- [x] 4.2 Migrate or replace existing Codex prompt tests that currently assert `_CODEX_PLACEHOLDER_TEXTS` / `_normalize_prompt_text()` behavior directly so they validate the new prompt behavior boundary instead.
- [x] 4.3 Add or update Codex tracker/profile tests that cover version selection and fallback behavior for prompt-area classification.
- [x] 4.4 Run targeted shared-TUI tracker tests and a live/demo verification pass to confirm Codex `editing_input` now follows the selected prompt behavior variant.
