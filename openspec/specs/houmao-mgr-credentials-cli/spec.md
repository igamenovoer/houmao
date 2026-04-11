# houmao-mgr-credentials-cli Specification

## Purpose
Define the dedicated `houmao-mgr credentials` and `houmao-mgr project credentials` command families for credential management across project overlays and plain agent-definition directories.

## Requirements

### Requirement: `houmao-mgr credentials` exposes a dedicated credential-management tree
`houmao-mgr` SHALL expose a first-class credential-management family shaped as:

```text
houmao-mgr credentials [--project|--agent-def-dir <path>] <tool> list|get|add|set|rename|remove
```

`houmao-mgr project` SHALL also expose a project-scoped wrapper shaped as:

```text
houmao-mgr project credentials <tool> list|get|add|set|rename|remove
```

At minimum, both command families SHALL expose Houmao-owned tool lanes for:

- `claude`
- `codex`
- `gemini`

At minimum, each supported tool lane SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `rename`
- `remove`

The help text for these command families SHALL present them as the supported credential-management surface rather than as manual filesystem editing guidance.

#### Scenario: Operator sees the dedicated top-level credential family
- **WHEN** an operator runs `houmao-mgr credentials --help`
- **THEN** the help output lists the supported tool lanes
- **AND THEN** the help output presents `credentials` as the supported credential-management surface

#### Scenario: Operator sees the project-scoped credential wrapper
- **WHEN** an operator runs `houmao-mgr project credentials --help`
- **THEN** the help output lists the supported tool lanes
- **AND THEN** the help output presents `project credentials` as project-scoped credential management

### Requirement: `credentials` resolves one target backend before running actions
`houmao-mgr credentials ...` SHALL resolve exactly one target backend before listing, inspecting, or mutating credentials.

Target resolution SHALL use this order:

1. explicit `--agent-def-dir`,
2. explicit `--project`,
3. `HOUMAO_AGENT_DEF_DIR`,
4. active project-overlay discovery,
5. otherwise fail with a clear target-resolution error.

If an explicit or env-provided agent-definition directory resolves to the compatibility projection owned by a valid project overlay, the command SHALL use the project backend for that target instead of the plain-directory backend.

`houmao-mgr project credentials ...` SHALL always resolve the active project overlay and SHALL NOT require `--project`.

#### Scenario: Explicit agent-definition directory selects the direct-dir backend
- **WHEN** an operator runs `houmao-mgr credentials codex list --agent-def-dir /tmp/agents`
- **AND WHEN** `/tmp/agents` is a valid plain agent-definition directory and not an overlay-managed compatibility tree
- **THEN** the command manages credentials through the direct directory backend

#### Scenario: Overlay-managed compatibility tree is promoted to the project backend
- **WHEN** an operator runs `houmao-mgr credentials claude get --agent-def-dir /repo/.houmao/agents --name work`
- **AND WHEN** `/repo/.houmao/agents` is the compatibility projection for a valid project overlay
- **THEN** the command resolves the owning project overlay
- **AND THEN** it uses the project backend instead of treating `/repo/.houmao/agents` as a plain direct-dir backend

#### Scenario: Missing target fails clearly
- **WHEN** an operator runs `houmao-mgr credentials gemini list`
- **AND WHEN** no explicit selector, `HOUMAO_AGENT_DEF_DIR`, or active project overlay can be resolved
- **THEN** the command fails explicitly
- **AND THEN** the error explains how to select either a project target or an agent-definition directory target

### Requirement: Project-targeted credential actions manage catalog-backed auth profiles
When the resolved target is a project overlay, `list|get|add|set|rename|remove` SHALL manage project-local catalog-backed auth profiles.

For the project backend:

- auth display names SHALL remain the operator-facing selector,
- opaque bundle refs SHALL remain the stable storage and projection identity,
- `rename` SHALL change only the display name,
- add, set, get, list, and remove SHALL use the catalog as the source of truth.

`houmao-mgr project credentials ...` and `houmao-mgr credentials ...` when they resolve to the same project overlay SHALL expose the same project-backed credential behavior.

#### Scenario: Project add stores credential content under an opaque bundle ref
- **WHEN** an operator runs `houmao-mgr project credentials claude add --name work --base-url https://api.example.test --api-key sk-test`
- **THEN** the command creates one project-local Claude auth profile named `work`
- **AND THEN** the resulting stored content is owned by the project catalog and projected through an opaque bundle-ref path rather than `.houmao/agents/tools/claude/auth/work/`

#### Scenario: Project rename preserves stable identity
- **WHEN** one project-local Codex auth profile named `work` exists
- **AND WHEN** an operator runs `houmao-mgr credentials codex rename --project --name work --to breakglass`
- **THEN** later project-backed credential inspection resolves the renamed profile by `breakglass`
- **AND THEN** the underlying bundle ref and downstream project relationships remain unchanged

### Requirement: Credential inspection and update semantics stay safe and patch-oriented across both backends
`get` SHALL report one credential safely as structured data selected by tool lane plus credential name.

By default, `get` SHALL redact secret-like values such as API keys, auth tokens, and OAuth tokens instead of printing them verbatim.

File-backed credential material SHALL be reported through presence and path metadata rather than by dumping raw file contents by default.

`set` SHALL only update fields explicitly provided by the operator. Omitted fields SHALL remain unchanged unless the operator uses an explicit clear-style flag supported by the selected tool lane.

Both backends SHALL validate env names and file inputs against the selected tool adapter contract and SHALL reject unsupported env names, auth-file inputs, or clear flags.

#### Scenario: Credential inspection stays redacted
- **WHEN** one credential stores both a secret env value and a non-secret endpoint override
- **AND WHEN** an operator runs the supported `credentials <tool> get --name <name>` command against either backend
- **THEN** the command reports presence and non-secret metadata without printing the raw secret value
- **AND THEN** file-backed credential material is reported by presence and path metadata rather than raw file content

#### Scenario: Set preserves unspecified fields
- **WHEN** one existing credential already stores both an API key and a base URL
- **AND WHEN** an operator runs `credentials <tool> set --name <name> --base-url https://proxy.example.test`
- **THEN** the command updates the stored base URL
- **AND THEN** it does not delete the existing API key only because `--api-key` was omitted

### Requirement: Direct agent-definition-dir credential actions manage named auth directories
When the resolved target is a plain agent-definition directory, such as a copied temp root derived from `tests/fixtures/plain-agent-def/`, `list|get|add|set|remove` SHALL manage named auth directories under `tools/<tool>/auth/<name>/`.

For the direct-dir backend:

- the directory basename SHALL remain the stored credential identity,
- add SHALL create a new named auth directory and fail on duplicate names,
- set SHALL update an existing named auth directory and fail when the target does not exist,
- remove SHALL delete the named auth directory,
- list SHALL enumerate the existing credential directory names for the selected tool lane.

The direct-dir backend SHALL still enforce the adapter-defined env/file contract for the selected tool lane.

Maintained examples for this backend SHALL use generic direct-dir paths or copied temp roots rather than the removed `tests/fixtures/agents/` path.

#### Scenario: Direct-dir add creates one named credential directory
- **WHEN** an operator runs `houmao-mgr credentials codex add --agent-def-dir /tmp/agents --name sandbox --api-key sk-test --auth-json /tmp/auth.json`
- **THEN** the command creates `/tmp/agents/tools/codex/auth/sandbox/`
- **AND THEN** the selected Codex env values and supported auth file are stored under that named directory

#### Scenario: Direct-dir list reports directory-backed credential names
- **WHEN** an operator runs `houmao-mgr credentials gemini list --agent-def-dir /tmp/agents`
- **THEN** the command reports the Gemini credential names discovered under `/tmp/agents/tools/gemini/auth/`
- **AND THEN** the command does not require a project overlay or project catalog for that inspection

### Requirement: Direct agent-definition-dir rename rewrites maintained in-tree auth references
When the resolved target is a plain agent-definition directory, `rename` SHALL:

1. rename `tools/<tool>/auth/<old-name>/` to `tools/<tool>/auth/<new-name>/`,
2. rewrite maintained auth references for that tool under:
   - `presets/*.yaml`
   - `launch-profiles/*.yaml`
3. report the rewritten files in the command result.

Direct-dir rename SHALL fail clearly when the selected credential does not exist or when the target name already exists for that tool lane.

Direct-dir rename SHALL NOT claim to rewrite arbitrary prose, tests, or external scripts outside the maintained in-tree reference set.

#### Scenario: Direct-dir rename rewrites preset and launch-profile auth references
- **WHEN** `/tmp/agents/tools/codex/auth/work/` exists in a plain agent-definition directory
- **AND WHEN** `/tmp/agents/presets/reviewer.yaml` and `/tmp/agents/launch-profiles/reviewer.yaml` both store `auth: work`
- **AND WHEN** an operator runs `houmao-mgr credentials codex rename --agent-def-dir /tmp/agents --name work --to breakglass`
- **THEN** the command renames the credential directory to `/tmp/agents/tools/codex/auth/breakglass/`
- **AND THEN** the maintained preset and launch-profile YAML now store `auth: breakglass`

#### Scenario: Direct-dir rename rejects duplicate target names
- **WHEN** `/tmp/agents/tools/claude/auth/work/` and `/tmp/agents/tools/claude/auth/breakglass/` both exist
- **AND WHEN** an operator runs `houmao-mgr credentials claude rename --agent-def-dir /tmp/agents --name work --to breakglass`
- **THEN** the command fails explicitly
- **AND THEN** it does not rename either credential directory

### Requirement: Supported credential lanes remain available through the dedicated credential interface
The dedicated credential interface SHALL preserve the current tool-specific credential input lanes for each supported tool.

At minimum:

- Codex SHALL support `--api-key`, `--base-url`, `--org-id`, and optional `--auth-json`.
- Gemini SHALL support `--api-key`, `--base-url`, `--google-api-key`, `--use-vertex-ai`, and optional `--oauth-creds`.
- Claude SHALL support `--api-key`, `--auth-token`, `--oauth-token`, optional `--config-dir`, optional endpoint/model env values, and optional `--state-template-file`.

For Claude, `--state-template-file` SHALL remain optional runtime bootstrap state and SHALL NOT be treated as a credential-providing lane by itself.

#### Scenario: Codex credential interface accepts API env and auth file inputs
- **WHEN** an operator creates or updates a Codex credential through the dedicated interface
- **THEN** the command accepts `--api-key`, `--base-url`, `--org-id`, and `--auth-json` as the supported Codex inputs
- **AND THEN** the command does not require provider-neutral replacement flags outside that supported Codex contract

#### Scenario: Gemini credential interface keeps API-key and OAuth lanes
- **WHEN** an operator creates or updates a Gemini credential through the dedicated interface
- **THEN** the command accepts API-key-based and OAuth-based inputs for Gemini
- **AND THEN** omitted Gemini inputs remain unchanged unless the operator uses an explicit supported clear flag

#### Scenario: Claude state template remains optional bootstrap state
- **WHEN** an operator creates or updates a Claude credential through the dedicated interface using a supported credential lane
- **AND WHEN** no `--state-template-file` is provided
- **THEN** the resulting Claude credential remains valid for that selected credential lane
- **AND THEN** the command does not report the missing template as missing credentials

### Requirement: Credential login helper imports provider auth artifacts from isolated homes
The dedicated credential interface SHALL expose a `login` verb for each maintained credential lane:

```text
houmao-mgr credentials [--project|--agent-def-dir <path>] <tool> login --name <credential-name>
houmao-mgr project credentials <tool> login --name <credential-name>
```

At minimum, `<tool>` SHALL include `claude`, `codex`, and `gemini`.

The `login` verb SHALL resolve the same project-backed or direct agent-definition-dir target backend as the existing credential verbs before mutating credential storage.

The `login` verb SHALL create a secure temporary provider home, run the installed provider CLI login flow with the selected provider home environment variable pointed at that temporary home, validate that the expected provider auth artifact exists, and import that artifact through the same storage path used by the selected tool lane's existing `add` behavior.

By default, `login` SHALL fail when the selected credential name already exists. When the operator passes an explicit update option, `login` SHALL import the provider artifact through the selected tool lane's existing `set` behavior instead.

The provider-home and artifact mapping SHALL include:

- Codex: `CODEX_HOME=<temp-home>` and `<temp-home>/auth.json`.
- Claude: `CLAUDE_CONFIG_DIR=<temp-home>` and `<temp-home>/.credentials.json`, including companion Claude state such as `.claude.json` when supported by the existing Claude config-dir importer.
- Gemini: `GEMINI_CLI_HOME=<temp-home>` and `<temp-home>/.gemini/oauth_creds.json`.

The provider command mapping SHALL include:

- Codex login defaults to device-auth mode, equivalent to `codex login --device-auth`, while allowing an explicit operator option for the ordinary browser-login mode.
- Claude login runs `claude auth login` and allows supported Claude login-mode flags to pass through when the CLI exposes them.
- Gemini login runs the interactive Gemini OAuth flow in the isolated home and allows the operator to complete the browser or manual-code flow before exiting Gemini so Houmao can import the OAuth artifact.

The `login` verb SHALL scrub common ambient provider credential environment variables by default so the provider login flow does not silently reuse the operator's current API-key or token account instead of the isolated temporary home. If an override exists to inherit auth-related environment variables, it SHALL be explicit.

After a successful Houmao import, the `login` verb SHALL delete the temporary provider home by default. If the provider login fails, the expected auth artifact is missing, or the Houmao import fails, the command SHALL preserve the temporary provider home and report its path. If an explicit keep-temp option is provided, the command SHALL preserve the temporary provider home even after a successful import and report its path.

#### Scenario: Codex device login imports auth json into a new project credential
- **WHEN** an operator runs `houmao-mgr project credentials codex login --name work`
- **AND WHEN** the Codex login flow completes successfully in an isolated `CODEX_HOME`
- **THEN** the command imports the resulting `auth.json` into one new project-local Codex credential named `work`
- **AND THEN** the command deletes the temporary Codex home after the import succeeds

#### Scenario: Existing credential requires explicit update
- **WHEN** one project-local Claude credential named `work` already exists
- **AND WHEN** an operator runs `houmao-mgr project credentials claude login --name work`
- **THEN** the command fails without replacing the existing stored credential
- **AND THEN** the result tells the operator to use the explicit update option when replacement is intended

#### Scenario: Explicit update imports through set behavior
- **WHEN** one direct-dir Gemini credential named `work` already exists under `/tmp/agents`
- **AND WHEN** an operator runs `houmao-mgr credentials gemini login --agent-def-dir /tmp/agents --name work --update`
- **AND WHEN** the Gemini OAuth artifact is produced in the isolated `GEMINI_CLI_HOME`
- **THEN** the command updates the existing Gemini credential through the direct-dir `set` behavior
- **AND THEN** omitted credential fields follow the same preservation semantics as `credentials gemini set`

#### Scenario: Failed provider login preserves the temp home
- **WHEN** an operator runs `houmao-mgr credentials codex login --project --name work`
- **AND WHEN** the Codex login command fails or no `auth.json` is created
- **THEN** the command fails without creating or updating the Houmao credential
- **AND THEN** it preserves the temporary Codex home and reports its path

#### Scenario: Successful import can keep the temp home when requested
- **WHEN** an operator runs `houmao-mgr project credentials claude login --name work --keep-temp-home`
- **AND WHEN** the Claude login flow and Houmao import both succeed
- **THEN** the command creates one project-local Claude credential named `work`
- **AND THEN** it preserves the temporary Claude config home and reports its path

#### Scenario: Login helper avoids ambient provider auth by default
- **WHEN** an operator has provider API-key or token environment variables set in the current shell
- **AND WHEN** the operator runs `houmao-mgr project credentials codex login --name alt-account`
- **THEN** the provider login process runs with the isolated provider home
- **AND THEN** common ambient provider credential environment variables are not inherited unless the operator explicitly asks to inherit them
