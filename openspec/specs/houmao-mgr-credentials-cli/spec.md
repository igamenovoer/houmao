# houmao-mgr-credentials-cli Specification

## Purpose
Define the maintained credential-management command families for Houmao project overlays and retained direct native-agent credential internals.

## Requirements

### Requirement: Project credentials are selected through the project command group
Project-backed credential management SHALL be exposed through:

```text
houmao-mgr project [--project-dir <dir>] credentials <tool> list|get|add|set|rename|remove|login
```

`project credentials` SHALL use the selected project overlay supplied by the `project` command group. It SHALL NOT expose `--project`, `--agent-def-dir`, or direct native-agent root selectors.

At minimum, the project credential family SHALL expose Houmao-owned tool lanes for:

- `claude`
- `codex`
- `gemini`

#### Scenario: Explicit project directory selects project credentials
- **WHEN** `/repo/.houmao/houmao-config.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project --project-dir /repo credentials claude list`
- **THEN** the command manages credentials in `/repo/.houmao`
- **AND THEN** it does not require a top-level `credentials --project` wrapper

#### Scenario: Project credentials reject direct native target options
- **WHEN** an operator runs `houmao-mgr project credentials codex list --agent-def-dir /tmp/agents`
- **THEN** the command fails as an unsupported option
- **AND THEN** the diagnostic does not imply that project credentials can directly target native-agent roots

### Requirement: Direct native-agent credentials are internals-only when retained
Direct credential CRUD for a plain native-agent root, if retained, SHALL be exposed under the internal native-agent command family rather than as a public top-level command.

The retained internal shape SHALL be:

```text
houmao-mgr internals native-agent credentials <tool> list|get|add|set|rename|remove|login
```

The internal command SHALL use the native-agent root selection contract from `internals native-agent`, including explicit `--native-agent-root` or the maintained native-agent root environment selector.

#### Scenario: Direct native credentials use native-agent root
- **WHEN** `/tmp/native/tools/codex/auth/work/` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent credentials codex list --native-agent-root /tmp/native`
- **THEN** the command lists direct Codex credentials under `/tmp/native/tools/codex/auth/`
- **AND THEN** it does not require a Houmao project overlay

### Requirement: Project-targeted credential actions manage catalog-backed auth profiles
When the resolved target is a project overlay, `list|get|add|set|rename|remove|login` SHALL manage project-local catalog-backed auth profiles.

For the project backend:

- auth display names SHALL remain the operator-facing selector,
- opaque bundle refs SHALL remain the stable storage and projection identity,
- `rename` SHALL change only the display name,
- add, set, get, list, login, and remove SHALL use the catalog as the source of truth.

Credential list payloads SHALL preserve the existing credential-name list and SHALL also include timestamped credential records. For project-backed credentials, each record's last update time SHALL come from the project catalog database timestamp.

#### Scenario: Project add stores credential content under an opaque bundle ref
- **WHEN** an operator runs `houmao-mgr project credentials claude add --name work --base-url https://api.example.test --api-key sk-test`
- **THEN** the command creates one project-local Claude auth profile named `work`
- **AND THEN** the resulting stored content is owned by the project catalog and projected through an opaque bundle-ref path rather than `.houmao/agents/tools/claude/auth/work/`

#### Scenario: Project list reports last update time
- **WHEN** one project-local Claude auth profile named `work` exists
- **AND WHEN** an operator runs `houmao-mgr project credentials claude list`
- **THEN** the command preserves `work` in the credential-name list
- **AND THEN** the list payload includes a credential record for `work` with a catalog-backed last update time

#### Scenario: Project rename preserves stable identity
- **WHEN** one project-local Codex auth profile named `work` exists
- **AND WHEN** an operator runs `houmao-mgr project credentials codex rename --name work --to breakglass`
- **THEN** later project-backed credential inspection resolves the renamed profile by `breakglass`
- **AND THEN** the underlying bundle ref and downstream project relationships remain unchanged

### Requirement: Credential inspection and update semantics stay safe and patch-oriented across maintained backends
`get` SHALL report one credential safely as structured data selected by tool lane plus credential name.

By default, `get` SHALL redact secret-like values such as API keys, auth tokens, and OAuth tokens instead of printing them verbatim.

File-backed credential material SHALL be reported through presence and path metadata rather than by dumping raw file contents by default.

`set` SHALL only update fields explicitly provided by the operator. Omitted fields SHALL remain unchanged unless the operator uses an explicit clear-style flag supported by the selected tool lane.

Both project-backed and internal native-agent credential backends SHALL validate env names and file inputs against the selected tool adapter contract and SHALL reject unsupported env names, auth-file inputs, or clear flags.

#### Scenario: Credential inspection stays redacted
- **WHEN** one credential stores both a secret env value and a non-secret endpoint override
- **AND WHEN** an operator runs a maintained credential `get --name <name>` command against either backend
- **THEN** the command reports presence and non-secret metadata without printing the raw secret value
- **AND THEN** file-backed credential material is reported by presence and path metadata rather than raw file content

#### Scenario: Set preserves unspecified fields
- **WHEN** one existing credential already stores both an API key and a base URL
- **AND WHEN** an operator runs a maintained credential `set --name <name> --base-url https://proxy.example.test`
- **THEN** the command updates the stored base URL
- **AND THEN** it does not delete the existing API key only because `--api-key` was omitted

### Requirement: Direct native credential actions manage named auth directories
When the resolved target is a plain native-agent root, such as a copied temp root derived from `tests/fixtures/plain-agent-def/`, `list|get|add|set|remove|login` SHALL manage named auth directories under `tools/<tool>/auth/<name>/`.

For the direct native backend:

- the directory basename SHALL remain the stored credential identity,
- add SHALL create a new named auth directory and fail on duplicate names,
- set SHALL update an existing named auth directory and fail when the target does not exist,
- remove SHALL delete the named auth directory,
- list SHALL enumerate the existing credential directory names for the selected tool lane.

The direct native backend SHALL still enforce the adapter-defined env/file contract for the selected tool lane.

Credential list payloads SHALL preserve the existing credential-name list and SHALL also include timestamped credential records. For direct native credentials, each record's last update time SHALL be derived best-effort from the credential bundle's filesystem metadata.

#### Scenario: Direct native add creates one named credential directory
- **WHEN** an operator runs `houmao-mgr internals native-agent credentials codex add --native-agent-root /tmp/native --name sandbox --api-key sk-test --auth-json /tmp/auth.json`
- **THEN** the command creates `/tmp/native/tools/codex/auth/sandbox/`
- **AND THEN** the selected Codex env values and supported auth file are stored under that named directory

#### Scenario: Direct native list reports directory-backed credential names
- **WHEN** an operator runs `houmao-mgr internals native-agent credentials gemini list --native-agent-root /tmp/native`
- **THEN** the command reports the Gemini credential names discovered under `/tmp/native/tools/gemini/auth/`
- **AND THEN** the command does not require a project overlay or project catalog for that inspection
- **AND THEN** the list payload includes a credential record with the credential name and filesystem-derived last update time

### Requirement: Direct native rename rewrites maintained in-tree auth references
When the resolved target is a plain native-agent root, `rename` SHALL:

1. rename `tools/<tool>/auth/<old-name>/` to `tools/<tool>/auth/<new-name>/`,
2. rewrite maintained auth references for that tool under:
   - `presets/*.yaml`
   - `launch-profiles/*.yaml`
3. report the rewritten files in the command result.

Direct native rename SHALL fail clearly when the selected credential does not exist or when the target name already exists for that tool lane.

Direct native rename SHALL NOT claim to rewrite arbitrary prose, tests, or external scripts outside the maintained in-tree reference set.

#### Scenario: Direct native rename rewrites preset and launch-profile auth references
- **WHEN** `/tmp/native/tools/codex/auth/work/` exists in a plain native-agent root
- **AND WHEN** `/tmp/native/presets/reviewer.yaml` and `/tmp/native/launch-profiles/reviewer.yaml` both store `auth: work`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent credentials codex rename --native-agent-root /tmp/native --name work --to breakglass`
- **THEN** the command renames the credential directory to `/tmp/native/tools/codex/auth/breakglass/`
- **AND THEN** the maintained preset and launch-profile YAML now store `auth: breakglass`

#### Scenario: Direct native rename rejects duplicate target names
- **WHEN** `/tmp/native/tools/claude/auth/work/` and `/tmp/native/tools/claude/auth/breakglass/` both exist
- **AND WHEN** an operator runs `houmao-mgr internals native-agent credentials claude rename --native-agent-root /tmp/native --name work --to breakglass`
- **THEN** the command fails explicitly
- **AND THEN** it does not rename either credential directory

### Requirement: Supported credential lanes remain available through maintained credential surfaces
The maintained credential surfaces SHALL preserve the current tool-specific credential input lanes for each supported tool.

At minimum:

- Codex SHALL support `--api-key`, `--base-url`, `--org-id`, and optional `--auth-json`.
- Gemini SHALL support `--api-key`, `--base-url`, `--google-api-key`, `--use-vertex-ai`, and optional `--oauth-creds`.
- Claude SHALL support `--api-key`, `--auth-token`, `--oauth-token`, optional `--config-dir`, optional endpoint/model env values, and optional `--state-template-file`.

For Claude, `--state-template-file` SHALL remain optional runtime bootstrap state and SHALL NOT be treated as a credential-providing lane by itself.

#### Scenario: Codex credential interface accepts API env and auth file inputs
- **WHEN** an operator creates or updates a Codex credential through a maintained credential surface
- **THEN** the command accepts `--api-key`, `--base-url`, `--org-id`, and `--auth-json` as the supported Codex inputs
- **AND THEN** the command does not require provider-neutral replacement flags outside that supported Codex contract

#### Scenario: Gemini credential interface keeps API-key and OAuth lanes
- **WHEN** an operator creates or updates a Gemini credential through a maintained credential surface
- **THEN** the command accepts API-key-based and OAuth-based inputs for Gemini
- **AND THEN** omitted Gemini inputs remain unchanged unless the operator uses an explicit supported clear flag

#### Scenario: Claude state template remains optional bootstrap state
- **WHEN** an operator creates or updates a Claude credential through a maintained credential surface using a supported credential lane
- **AND WHEN** no `--state-template-file` is provided
- **THEN** the resulting Claude credential remains valid for that selected credential lane
- **AND THEN** the command does not report the missing template as missing credentials

### Requirement: Credential login helper imports provider auth artifacts from isolated homes
The maintained credential surfaces SHALL expose a `login` verb for each maintained credential lane:

```text
houmao-mgr project [--project-dir <dir>] credentials <tool> login --name <credential-name>
houmao-mgr internals native-agent credentials <tool> login --native-agent-root <path> --name <credential-name>
```

At minimum, `<tool>` SHALL include `claude`, `codex`, and `gemini`.

The `login` verb SHALL resolve the same project-backed or direct native-agent target backend as the existing credential verbs before mutating credential storage.

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
- **WHEN** one direct native Gemini credential named `work` already exists under `/tmp/native`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent credentials gemini login --native-agent-root /tmp/native --name work --update`
- **AND WHEN** the Gemini OAuth artifact is produced in the isolated `GEMINI_CLI_HOME`
- **THEN** the command updates the existing Gemini credential through the direct native `set` behavior
- **AND THEN** omitted credential fields follow the same preservation semantics as `internals native-agent credentials gemini set`

#### Scenario: Failed provider login preserves the temp home
- **WHEN** an operator runs `houmao-mgr project credentials codex login --name work`
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

### Requirement: Credential mutations stay within managed credential bundle roots
Credential create, set, rename, and remove flows SHALL mutate only lexical artifact paths inside the selected Houmao-managed credential bundle roots.

When credential commands consume caller-provided source files, those files SHALL be treated as read-only inputs.

#### Scenario: Clearing a symlink-backed managed credential file removes only the artifact
- **WHEN** one managed credential bundle already contains a file entry whose lexical path under the managed bundle root is a symlink
- **AND WHEN** an operator runs a credential update that clears that managed file entry
- **THEN** Houmao removes only the lexical artifact path under the managed bundle root
- **AND THEN** it does not delete or rewrite the symlink target

#### Scenario: Importing one source credential file preserves the caller-owned input
- **WHEN** an operator runs a credential update that copies one caller-provided source file into a managed credential bundle
- **THEN** the managed credential bundle is updated
- **AND THEN** the caller-provided source file remains intact

### Requirement: Credential CLI surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide template entries for project-scoped and internal native-agent credential command surfaces for Claude, Codex, and Gemini.

Template entries SHALL cover credential command verbs `add`, `set`, `login`, `list`, `get`, `rename`, and `remove` where those verbs exist in the maintained `houmao-mgr project credentials` or `houmao-mgr internals native-agent credentials` command surfaces.

Each credential template SHALL map structured fields to CLI options, SHALL describe required target fields, SHALL describe tool-specific credential material fields, and SHALL report conflicts between mutually exclusive credential sources.

#### Scenario: Project credential add has tool-specific metadata
- **WHEN** an agent shows `project.credentials.gemini.add`
- **THEN** the template reports Gemini credential source fields such as API key, Vertex AI key posture, OAuth credentials, and base URL
- **AND THEN** it does not report Claude-only or Codex-only credential fields

#### Scenario: Native credential list carries native-agent target
- **WHEN** an agent renders an internal native credential list template
- **THEN** the rendered argv includes the explicit native-agent root target
- **AND THEN** it does not render the project-scoped command path

#### Scenario: Credential source conflicts block rendering
- **WHEN** an agent renders a credential add template with two mutually exclusive credential sources for the same tool
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv
