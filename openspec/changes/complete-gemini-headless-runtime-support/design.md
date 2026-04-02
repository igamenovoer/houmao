## Context

Houmao already exposes a `gemini_headless` backend, but the current implementation is incomplete relative to both upstream `gemini-cli` behavior and Houmao's own runtime spec.

The current gaps are operational, not conceptual:

- Houmao builds Gemini runtime homes by projecting static auth files and allowlisted env vars from the selected auth bundle.
- Upstream Gemini CLI `0.36.0` rejects non-interactive OAuth startup if no auth type is selected, even when `oauth_creds.json` is present.
- Houmao's Gemini adapter currently does not allow `GOOGLE_GENAI_USE_GCA`, and Houmao does not generate any Gemini auth-selection config.
- Houmao's Gemini backend still resumes with `--resume latest`, while upstream Gemini supports full UUID resume and Houmao already persists `headless.session_id`.

The relevant implementation constraint is that Houmao's current brain-builder path already has a first-class way to project auth files and launch env vars, but it does not have a generic contract for generating derived runtime config files from auth-bundle state.

## Goals / Non-Goals

**Goals:**

- Make freshly constructed Gemini runtime homes non-interactive-ready for OAuth-backed headless turns.
- Align Gemini continuation with the persisted `session_id` contract already captured in Houmao manifests.
- Preserve Gemini's project-scoped resume behavior by keeping the same-working-directory guard.
- Add regression coverage for Gemini auth preparation and resumed headless turns.
- Update Gemini runtime documentation so the operator contract matches the implementation.

**Non-Goals:**

- Add Gemini TUI parsing or a Gemini CAO transport.
- Make Gemini part of the maintained unattended launch-policy lane in this change.
- Redesign the entire Gemini auth-bundle CLI surface.
- Import or mirror the user's full `~/.gemini/settings.json` into Houmao runtime homes.

## Decisions

### 1. Use env-based auth selection for OAuth-backed Gemini homes

Houmao will treat the presence of projected `oauth_creds.json` as the signal that the session is intended to use Gemini's Google-login OAuth path, unless the selected auth bundle or launch contract already explicitly chooses a different Gemini auth mode.

For those OAuth-backed Gemini launches, Houmao will export `GOOGLE_GENAI_USE_GCA=true` into the launched environment.

Why:

- This fits Houmao's existing runtime construction model, which already projects auth files and exports allowlisted env vars.
- It works for both new and existing Gemini auth bundles without requiring a new required file in the auth bundle tree.
- It avoids copying or synthesizing a broad `settings.json` whose unrelated contents may include user-specific MCP config, local preferences, or secrets.
- Upstream Gemini CLI already recognizes `GOOGLE_GENAI_USE_GCA=true` as the auth-type selector for the Google-login path.

Alternatives considered:

- Generate a minimal `.gemini/settings.json` with `security.auth.selectedType: oauth-personal`.
  Rejected because the current builder does not have a general derived-config-file contract, and a settings file is a broader surface that is easier to couple accidentally to unrelated user preferences.
- Require operators to place `GOOGLE_GENAI_USE_GCA=true` manually in every Gemini auth bundle.
  Rejected because that leaves existing OAuth bundles broken and does not satisfy the goal of reliable fresh-home startup.

### 2. Keep `oauth_creds.json` as the required Gemini credential file

Houmao will continue to treat `oauth_creds.json` as the required Gemini auth file for the OAuth-backed headless lane.

`google_accounts.json` may remain optional metadata, but it will not be the runtime-critical credential input for this change.

Why:

- Upstream Gemini stores OAuth credentials in `oauth_creds.json`.
- Live probing showed `google_accounts.json` is not required for successful non-interactive startup when auth type is selected correctly.
- Keeping the required file set minimal reduces auth-bundle surface area and avoids expanding project-tool workflows unnecessarily.

Alternatives considered:

- Make `google_accounts.json` required and project it unconditionally.
  Rejected because it is not necessary for the headless runtime contract being fixed here.

### 3. Resume Gemini with the persisted `session_id`, not `latest`

Houmao will update Gemini headless continuation to use `--resume <session_id>` whenever a persisted Gemini session ID exists in the manifest.

Why:

- This matches upstream Gemini CLI behavior.
- This matches Houmao's current OpenSpec contract.
- It avoids attaching to the wrong conversation when multiple Gemini runs exist in the same project.

Alternatives considered:

- Keep `--resume latest`.
  Rejected because it is weaker than the manifest-backed session identity Houmao already persists and can select the wrong session under concurrent or repeated project use.

### 4. Keep same-working-directory enforcement as part of the resume contract

Houmao will keep the existing runtime check that Gemini resumed turns must use the same working directory as the persisted session.

Why:

- Upstream Gemini stores sessions in a project-scoped chat store.
- Live probing confirmed session listing and session reuse are tied to the active project/workspace.
- Keeping the guard prevents silent cross-project resume mismatches.

Alternatives considered:

- Relax the working-directory constraint and rely only on `session_id`.
  Rejected because it does not reflect Gemini's project-scoped storage model and would weaken operator guarantees.

### 5. Keep `stream-json` as the canonical Gemini machine-readable format

Houmao will continue treating `stream-json` as the canonical Gemini headless output format and will continue to capture `session_id` from the initial `init` event.

Why:

- It is the most stable machine-readable surface for start and resume flows.
- It preserves the existing headless runner structure already used in Houmao.

Alternatives considered:

- Switch Gemini to one-shot JSON output parsing.
  Rejected because `stream-json` already provides the needed session identity and progressive output structure without reducing capability.

## Risks / Trade-offs

- [Implicit auth inference could conflict with explicit non-OAuth Gemini auth settings] → Only inject `GOOGLE_GENAI_USE_GCA=true` when OAuth credential material is present and no explicit Gemini auth selector is already being used.
- [Upstream Gemini auth-selection behavior could drift in future CLI releases] → Add regression coverage around Gemini startup env projection and keep one live/manual validation path documented.
- [Existing operators may be informally relying on `--resume latest`] → Use persisted UUID resume only when a valid `session_id` exists; keep manifest validation explicit so broken sessions fail clearly instead of silently retargeting.
- [Documentation can drift from implementation again] → Update backend and setup docs as part of the same change and tie examples to the supported auth-selection policy.

## Migration Plan

1. Update Gemini runtime preparation so OAuth-backed bundles inject the supported auth selector for fresh homes.
2. Update Gemini headless backend command construction to use the persisted `session_id`.
3. Add or revise tests that cover:
   - Gemini OAuth auth-selection preparation for fresh homes
   - first-turn `session_id` capture
   - resumed Gemini turns using exact UUID resume
4. Update Gemini runtime and setup documentation to describe the supported contract.

Rollback is straightforward because this change is isolated to Gemini runtime preparation and Gemini resume command construction. Reverting the affected adapter/runtime logic restores the current partial behavior.

## Open Questions

None for this implementation-focused change. Future work may still decide whether Gemini should later gain a maintained unattended policy lane or a non-headless transport, but those are intentionally out of scope here.
