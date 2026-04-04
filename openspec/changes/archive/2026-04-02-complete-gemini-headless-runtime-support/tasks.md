## 1. Gemini auth contract and runtime prep

- [x] 1.1 Extend the Gemini adapter and project-tool auth flow to support `GEMINI_API_KEY`, optional `GOOGLE_GEMINI_BASE_URL`, and `oauth_creds.json`.
- [x] 1.2 Update Gemini runtime-home preparation so OAuth-backed Gemini homes inject the supported Google-login auth selector for headless startup without depending on user-global Gemini settings.
- [x] 1.3 Ensure the Gemini runtime prep preserves explicit API-key auth and endpoint overrides instead of overriding them when OAuth credential material is also present.
- [x] 1.4 Change Gemini managed skill projection to use `.agents/skills` for constructed homes and default Houmao-owned join-time projection.
- [x] 1.5 Add automated coverage for Gemini auth-bundle persistence, `.agents/skills` projection, and runtime-home env behavior for API-key, endpoint-override, and OAuth-backed cases.

## 2. Exact Gemini session continuation

- [x] 2.1 Change the Gemini headless backend to resume follow-up turns with the persisted Gemini `session_id` instead of `--resume latest`.
- [x] 2.2 Keep Gemini's same-working-directory/project-context enforcement intact and add regression coverage for successful exact-ID resume and mismatched-context failure cases.
- [x] 2.3 Add or update headless-output parsing tests so Gemini `stream-json` `session_id` capture remains the canonical continuation identity.

## 3. Documentation and validation

- [x] 3.1 Update Gemini runtime, backend, and project-tool reference docs to describe the supported API-key plus optional endpoint lane, the OAuth lane, and exact-ID resume behavior.
- [x] 3.2 Update Gemini skill-projection documentation and related mailbox/internal docs so Gemini's Houmao-owned skill root is documented as `.agents/skills`, with `.gemini/skills` treated as a compatibility path rather than the target contract.
- [x] 3.3 Add or refresh Gemini-specific validation notes or manual smoke guidance so operators can verify API-key startup, OAuth startup, skill projection under `.agents/skills`, first-turn session capture, and resumed turns against the supported contract.
