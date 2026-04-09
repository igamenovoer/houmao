## MODIFIED Requirements

### Requirement: `project agents tools <tool> auth` manages catalog-backed auth profiles and derived auth projections
`houmao-mgr project agents tools <tool> auth` SHALL create, inspect, update, list, rename, and remove auth profiles through the project-local catalog.

The project-local catalog SHALL be the source of truth for auth profile identity and relationships for this surface.

Auth content SHALL remain file-backed through managed auth content storage and a derived compatibility projection, but neither storage path nor projection path basename SHALL be the authoritative auth identity.

`auth add --name <name>` SHALL create a new auth profile for the selected tool and SHALL fail if that display name already exists for that tool.

`auth set --name <name>` SHALL update an existing auth profile selected by display name and SHALL fail if that named auth profile does not exist for that tool.

`auth list` SHALL enumerate existing auth display names for the selected tool.

`auth rename --name <name> --to <new-name>` SHALL rename one existing auth profile selected by display name and SHALL fail if the target display name already exists for that tool.

`auth remove --name <name>` SHALL remove the named auth profile selected by display name.

Tool-specific flags SHALL continue mapping onto the adapter-defined env/file contract for the selected tool, including `env/vars.env` content and any supported `files/*` content.

#### Scenario: Add creates a catalog-backed Claude auth profile with derived projection storage
- **WHEN** an operator runs `houmao-mgr project agents tools claude auth add --name work --base-url https://api.example.test --api-key sk-test`
- **THEN** the command creates one Claude auth profile named `work`
- **AND THEN** the resulting auth content is stored and projected through an opaque bundle-reference path rather than `.houmao/agents/tools/claude/auth/work/`

#### Scenario: Add rejects duplicate auth display names
- **WHEN** a Gemini auth profile named `work` already exists
- **AND WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name work --oauth-creds /tmp/oauth.json`
- **THEN** the command fails explicitly
- **AND THEN** it does not silently reinterpret `add` as an update

### Requirement: `project agents tools <tool> auth get` reports one auth profile safely and `auth set` uses patch semantics
`houmao-mgr project agents tools <tool> auth get --name <name>` SHALL report one existing auth profile as structured data selected by tool plus display name.

By default, `auth get` SHALL redact secret-like values such as API keys or auth tokens instead of printing them verbatim.

File-backed auth material SHALL be reported through presence and path metadata rather than by dumping raw file content by default.

`auth get` MAY expose advanced metadata such as the opaque bundle reference or derived projection path, but those values SHALL be treated as diagnostics rather than as the operator-facing identity contract.

`auth set` SHALL only update fields explicitly provided by the operator. Omitted fields SHALL remain unchanged unless the operator uses an explicit clear-style option for that field.

#### Scenario: Get redacts secret values by default
- **WHEN** one Claude auth profile named `work` stores both `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL`
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth get --name work`
- **THEN** the command reports that the API key is present without printing its raw value
- **AND THEN** the command may still report non-secret metadata such as the display name, opaque bundle reference, or configured base URL

#### Scenario: Set preserves unspecified fields
- **WHEN** one Claude auth profile named `work` already stores both `ANTHROPIC_API_KEY=sk-test` and `ANTHROPIC_BASE_URL=https://api.example.test`
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth set --name work --base-url https://proxy.example.test`
- **THEN** the command updates the stored base URL
- **AND THEN** it does not delete the existing API key only because `--api-key` was omitted

### Requirement: Gemini auth bundles support API key, optional endpoint override, and OAuth inputs
`houmao-mgr project agents tools gemini auth` SHALL support Gemini auth profiles that can represent:

- API-key-based Gemini access through `GEMINI_API_KEY`
- optional Gemini endpoint override through `GOOGLE_GEMINI_BASE_URL`
- OAuth-backed Gemini access through `oauth_creds.json`

The command surface SHALL preserve patch semantics so operators can configure one of these lanes without implicitly deleting other unspecified Gemini auth inputs.

The resulting auth payload SHALL be stored through the catalog-backed auth profile and its opaque bundle-reference-backed content, not by requiring the display name to be the projection directory basename.

#### Scenario: Add creates a Gemini API-key auth profile with an endpoint override
- **WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name proxy --api-key gm-test --base-url https://gemini.example.test`
- **THEN** the command creates one Gemini auth profile named `proxy`
- **AND THEN** that auth profile stores `GEMINI_API_KEY` and `GOOGLE_GEMINI_BASE_URL` using the Gemini adapter contract

#### Scenario: Set updates the Gemini endpoint override without removing the API key
- **WHEN** one Gemini auth profile named `proxy` already stores `GEMINI_API_KEY=gm-test`
- **AND WHEN** an operator runs `houmao-mgr project agents tools gemini auth set --name proxy --base-url https://gemini-alt.example.test`
- **THEN** the command updates the stored `GOOGLE_GEMINI_BASE_URL`
- **AND THEN** it does not delete the existing `GEMINI_API_KEY` only because `--api-key` was omitted

#### Scenario: Add creates a Gemini OAuth auth profile with the OAuth credential file
- **WHEN** an operator runs `houmao-mgr project agents tools gemini auth add --name personal --oauth-creds /tmp/oauth_creds.json`
- **THEN** the command creates one Gemini auth profile named `personal`
- **AND THEN** the resulting auth profile remains valid even when no API key is configured

### Requirement: Claude auth bundles support vendor OAuth token and imported login state
`houmao-mgr project agents tools claude auth` SHALL support Claude auth profiles that can represent:

- API-key-based Claude access through `ANTHROPIC_API_KEY`
- auth-token-based Claude access through `ANTHROPIC_AUTH_TOKEN`
- OAuth-token-based Claude access through `CLAUDE_CODE_OAUTH_TOKEN`
- optional endpoint and model env values already supported by the Claude adapter contract
- imported vendor login state through `.credentials.json` and optional `.claude.json` copied from a Claude config root

The command surface SHALL accept a Claude config-dir import input for the vendor login-state lane and SHALL preserve patch semantics across both env-backed and file-backed Claude auth inputs.

`claude_state.template.json` MAY remain supported as optional Claude runtime-state template content inside the auth profile, but it SHALL NOT be treated, counted, or documented as a Claude credential-providing lane.

The resulting auth payload SHALL be stored through the catalog-backed auth profile and its opaque bundle-reference-backed content, not by requiring the display name to be the projection directory basename.

#### Scenario: Add creates a Claude OAuth-token auth profile
- **WHEN** an operator runs `houmao-mgr project agents tools claude auth add --name personal --oauth-token token123`
- **THEN** the command creates one Claude auth profile named `personal`
- **AND THEN** that auth profile stores `CLAUDE_CODE_OAUTH_TOKEN` without requiring `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`

#### Scenario: Add imports Claude login state from a config root
- **WHEN** `/tmp/claude-home` contains `.credentials.json` and `.claude.json`
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth add --name logged-in --config-dir /tmp/claude-home`
- **THEN** the command copies the supported vendor login-state files into the selected Claude auth profile's managed auth content
- **AND THEN** later inspection reports those files as present for `logged-in`

#### Scenario: Set refreshes imported Claude login files without deleting other explicit settings
- **WHEN** one Claude auth profile named `logged-in` already stores `ANTHROPIC_MODEL=claude-sonnet`
- **AND WHEN** that auth profile already contains imported Claude login-state files
- **AND WHEN** an operator runs `houmao-mgr project agents tools claude auth set --name logged-in --config-dir /tmp/claude-home-2`
- **THEN** the command updates the copied vendor login-state files from `/tmp/claude-home-2`
- **AND THEN** it does not delete the stored `ANTHROPIC_MODEL` only because `--model` was omitted

#### Scenario: Claude state template remains optional and separate from credentials
- **WHEN** an operator creates or updates a Claude auth profile using a supported credential lane
- **AND WHEN** no `claude_state.template.json` is provided
- **THEN** the resulting auth profile remains valid for that selected credential lane
- **AND THEN** the operator-facing contract does not describe the missing template as missing credentials

## ADDED Requirements

### Requirement: `project agents tools <tool> auth rename` changes only the display name
`houmao-mgr project agents tools <tool> auth rename --name <name> --to <new-name>` SHALL rename exactly one existing auth profile selected by tool plus current display name.

Rename SHALL preserve the underlying auth content, opaque bundle reference, and downstream auth relationships.

`auth rename` SHALL fail clearly when the selected auth profile does not exist or when the target display name already exists for that tool.

#### Scenario: Rename preserves projection identity and auth content
- **WHEN** one Codex auth profile named `work` exists
- **AND WHEN** an operator runs `houmao-mgr project agents tools codex auth rename --name work --to breakglass`
- **THEN** later `auth get --name breakglass` resolves the same auth profile
- **AND THEN** the auth profile still points at the same opaque bundle reference and auth content
