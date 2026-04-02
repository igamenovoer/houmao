## ADDED Requirements

### Requirement: Gemini auth bundles support API key, optional endpoint override, and OAuth inputs
`houmao-mgr project agents tools gemini auth` SHALL support Gemini auth bundles that can represent:

- API-key-based Gemini access through `GEMINI_API_KEY`
- optional Gemini endpoint override through `GOOGLE_GEMINI_BASE_URL`
- OAuth-backed Gemini access through `oauth_creds.json`

The command surface SHALL preserve patch semantics so operators can configure one of these lanes without implicitly deleting other unspecified Gemini auth inputs.

#### Scenario: Add creates a Gemini API-key auth bundle with an endpoint override
- **WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name proxy --api-key gm-test --base-url https://gemini.example.test`
- **THEN** the command creates `.houmao/agents/tools/gemini/auth/proxy/env/vars.env`
- **AND THEN** that bundle stores `GEMINI_API_KEY` and `GOOGLE_GEMINI_BASE_URL` using the Gemini adapter contract

#### Scenario: Set updates the Gemini endpoint override without removing the API key
- **WHEN** `.houmao/agents/tools/gemini/auth/proxy/env/vars.env` already contains `GEMINI_API_KEY=gm-test`
- **AND WHEN** an operator runs `houmao-mgr project agents tools gemini auth set --name proxy --base-url https://gemini-alt.example.test`
- **THEN** the command updates the stored `GOOGLE_GEMINI_BASE_URL`
- **AND THEN** it does not delete the existing `GEMINI_API_KEY` only because `--api-key` was omitted

#### Scenario: Add creates a Gemini OAuth auth bundle with the OAuth credential file
- **WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name personal --oauth-creds /tmp/oauth_creds.json`
- **THEN** the command creates `.houmao/agents/tools/gemini/auth/personal/files/oauth_creds.json`
- **AND THEN** the resulting Gemini auth bundle remains valid even when no API key is configured
