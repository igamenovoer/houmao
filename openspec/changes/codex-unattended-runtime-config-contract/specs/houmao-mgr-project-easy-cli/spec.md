## ADDED Requirements

### Requirement: `project easy specialist create` persists explicit tool setup selection
`houmao-mgr project easy specialist create` SHALL accept an optional `--setup <name>` input with a default of `default`.

The command SHALL validate that the selected setup exists for the selected tool before writing project-local specialist state.

The command SHALL persist the selected setup consistently into:

- the stored project catalog specialist metadata,
- the generated compatibility preset for that specialist,
- later project-aware launch inputs derived from that specialist definition.

The command SHALL NOT infer the selected setup from credential bundle names, auth payload shape, or API endpoint values.

This requirement SHALL apply to any project-easy specialist tool that uses setup bundles today or in the future.

#### Scenario: Explicit non-default setup is persisted through specialist creation
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --setup yunwu-openai --api-key sk-test`
- **THEN** the command persists specialist `researcher` successfully
- **AND THEN** the stored specialist metadata records `setup = yunwu-openai`
- **AND THEN** the generated preset for `researcher` records the same setup instead of silently substituting `default`

#### Scenario: Omitted setup still persists the default setup explicitly
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool claude --api-key sk-test`
- **THEN** the command persists specialist `reviewer` successfully
- **AND THEN** the stored specialist metadata records `setup = default`
- **AND THEN** later project-aware launch resolves that same stored setup without inferring a different setup from credentials
