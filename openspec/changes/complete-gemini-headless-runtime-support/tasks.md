## 1. Gemini auth-ready startup

- [ ] 1.1 Update Gemini runtime-home preparation so OAuth-backed Gemini homes inject the supported Google-login auth selector for headless startup without depending on user-global Gemini settings.
- [ ] 1.2 Ensure the auth-selection logic preserves explicit non-OAuth Gemini auth modes instead of overriding API-key or Vertex-based launches.
- [ ] 1.3 Add automated coverage for Gemini runtime-home auth preparation, including fresh OAuth-backed homes and explicit non-OAuth override cases.

## 2. Exact Gemini session continuation

- [ ] 2.1 Change the Gemini headless backend to resume follow-up turns with the persisted Gemini `session_id` instead of `--resume latest`.
- [ ] 2.2 Keep Gemini's same-working-directory/project-context enforcement intact and add regression coverage for successful exact-ID resume and mismatched-context failure cases.
- [ ] 2.3 Add or update headless-output parsing tests so Gemini `stream-json` `session_id` capture remains the canonical continuation identity.

## 3. Documentation and validation

- [ ] 3.1 Update Gemini runtime and backend reference docs to describe the supported OAuth headless startup contract and exact-ID resume behavior.
- [ ] 3.2 Add or refresh Gemini-specific validation notes or manual smoke guidance so operators can verify first-turn startup and resumed turns against the supported contract.
