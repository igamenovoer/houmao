## Context

`houmao-create-specialist` is a deployed system skill that teaches downstream agents how to call `houmao-mgr project easy specialist create`. The current skill keeps most credential logic inline and treats discovery as a single `auto credentials` flow. That is already too coarse for real deployment use:

- users may want to provide all auth explicitly,
- users may want to tell the agent to inspect only certain env vars or env-name patterns,
- users may want to point the agent at one directory and let it scan there,
- users may want tool-specific automatic lookup behavior.

The three supported tools also differ materially in how they store or select auth:

- Claude uses `CLAUDE_CONFIG_DIR`, `~/.claude`, `~/.claude.json`, `~/.claude/.credentials.json`, and terminal-only auth surfaces such as `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, and `apiKeyHelper`.
- Codex uses `CODEX_HOME`, `~/.codex`, cached `auth.json`, and config-backed provider selection in `config.toml`.
- Gemini uses `GEMINI_CLI_HOME`, `~/.gemini`, `oauth_creds.json`, `.env` loading, `GEMINI_API_KEY`, Vertex AI selectors, and other Google auth paths.

Houmao’s create command only accepts a narrower set of import surfaces:

- Claude: `--api-key`, `--base-url`, `--claude-auth-token`, `--claude-model`, `--claude-state-template-file`
- Codex: `--api-key`, `--base-url`, `--codex-org-id`, `--codex-auth-json`
- Gemini: `--api-key`, `--base-url`, `--google-api-key`, `--use-vertex-ai`, `--gemini-oauth-creds`

So the design has to separate credential discovery from credential import. It also has to stay grounded in real deployed lookup surfaces, not test fixtures that only exist inside the Houmao repository.

## Goals / Non-Goals

**Goals:**

- Make the skill’s credential behavior explicit and predictable through four source modes.
- Keep the main `SKILL.md` short enough to stay readable while moving tool-specific lookup detail into dedicated reference pages.
- Base lookup guidance on authoritative evidence from official docs, `extern/orphan` upstream source, and installed executable behavior.
- Prevent the skill from guessing or silently translating auth shapes that `project easy specialist create` cannot represent.
- Avoid any dependency on `tests/fixtures/agents`, demo assets, or other repository-only host assumptions.

**Non-Goals:**

- Changing `houmao-mgr project easy specialist create` flags or adding new auth import formats in this change.
- Making the skill scan arbitrary directories or environment state unless the selected mode explicitly allows it.
- Supporting every auth shape a tool can possibly use when Houmao cannot currently import that shape.
- Rewriting launcher-order behavior, skill installation behavior, or unrelated specialist-authoring guidance.

## Decisions

### 1. Model credential lookup as four explicit source modes

The skill will describe four credential-source modes:

1. explicit auth values or files from the user,
2. user-directed env lookup by exact names or explicit name patterns,
3. user-directed directory scan,
4. tool-specific auto discovery.

If the user does not request any of those modes, the skill should only reuse an already-existing credential bundle or ask the user for missing auth.

Why this approach:

- It matches the user’s mental model and avoids overloading `auto credentials` with every credential lookup case.
- It keeps scope clear. User-directed env and directory scans are narrower and safer than open-ended auto discovery.
- It lets the skill preserve the current “do not scan unless asked” rule while still supporting explicit scan requests other than `auto credentials`.

Alternatives considered:

- Keep one `auto credentials` mode and treat env names or directories as implementation details. Rejected because it obscures user intent and makes scanning scope ambiguous.
- Always auto-discover likely credentials when auth is missing. Rejected because it violates the current explicit-consent model.

### 2. Move tool-specific lookup rules into separate reference pages

The main `SKILL.md` will act as a dispatcher and policy surface. Tool-specific lookup detail will live in one reference page per tool, for example:

- `references/claude-credential-lookup.md`
- `references/codex-credential-lookup.md`
- `references/gemini-credential-lookup.md`

The main skill should load only the reference page for the selected tool and only when a credential-discovery mode needs it.

Why this approach:

- The per-tool lookup rules are already complex and drift independently.
- Splitting them keeps the main skill short and procedural.
- It isolates future updates when one upstream tool changes auth behavior without forcing a large rewrite of the core skill text.

Alternatives considered:

- Keep all lookup rules inline in `SKILL.md`. Rejected because the skill becomes long, repetitive, and fragile.
- Put the rules only in external web docs. Rejected because deployed skills need local instructions that remain available offline once packaged.

### 3. Define an evidence-backed authoring contract for the reference pages

Each tool-specific reference page will be written from three evidence classes:

- official tool documentation,
- `extern/orphan` upstream source already checked into the repo,
- direct inspection of the installed executable (`--help`, `auth --help`, `login --help`, versioned behavior probes).

The reference pages must describe only deployment-realistic surfaces such as tool homes, redirected tool homes, stored auth files, supported env vars, and maintained config files. They must not refer agents to `tests/fixtures/agents`, demo fixtures, or other repository-only paths that do not exist on a deployed host.

Why this approach:

- Tool auth behavior can diverge between docs, source, and shipped binaries; using all three reduces stale assumptions.
- The user explicitly wants correctness grounded in upstream tool behavior rather than Houmao-only test assets.

Alternatives considered:

- Use Houmao test fixtures as lookup guidance. Rejected because those paths do not exist on deployment targets.
- Trust only official docs. Rejected because some auth details, especially config-backed provider behavior, are clearer in source and CLI help than in high-level docs.

### 4. Separate discovery from importability

The skill may discover that a tool is authenticated through a mechanism that Houmao cannot currently import into `project easy specialist create`. The design will require the skill to distinguish:

- discovered and importable auth,
- discovered but not importable auth.

Only importable auth may be converted into create flags. Unsupported live auth shapes must be reported back to the user instead of being guessed or partially translated.

Examples:

- Claude `apiKeyHelper` configuration is a real auth source, but it is not directly representable by current Houmao create flags unless the actual reusable key or state template is separately available.
- Codex config-backed custom providers are only importable when the provider is env-only, `requires_openai_auth=false`, `wire_api=responses`, and enough values are discoverable to map into Houmao’s supported flags.
- Gemini service-account JSON via `GOOGLE_APPLICATION_CREDENTIALS` or pure ADC may describe current auth, but those forms are not directly importable today unless they correspond to an importable Houmao input such as `oauth_creds.json` or a supported API-key lane.

Why this approach:

- It keeps the skill honest about what Houmao can actually create.
- It avoids silently producing broken credential bundles from incomplete or incompatible evidence.

Alternatives considered:

- Best-effort translation of partially compatible auth shapes. Rejected because the failure mode is hidden and user-hostile.
- Expanding the skill to execute provider-specific auth helpers or login flows. Rejected because that changes the product surface and belongs in CLI design, not in skill text.

## Risks / Trade-offs

- Drift in upstream tool auth behavior -> Keep the main skill thin, isolate lookup rules per tool, and require each reference page to be refreshed from official docs, upstream source, and CLI inspection.
- User-directed scans can be broad -> Keep mode boundaries explicit and require env and directory scans to stay within the user-provided scope.
- Some real auth setups will still fail import -> Make unsupported-shape reporting a first-class skill behavior instead of masking it.
- More files in one skill directory -> Accept the small packaging cost because the split greatly improves maintainability and correctness.

## Migration Plan

1. Add per-tool credential lookup reference pages under the `houmao-create-specialist` skill directory.
2. Rewrite the main `SKILL.md` to dispatch between the four credential-source modes and load the selected-tool reference page only when needed.
3. Update regression tests so packaged skill content checks for the new mode descriptions, reference-page structure, and the absence of fixture-only path guidance.
4. Reinstall or re-project the system skill so deployed tool homes receive the updated content.

Rollback is low risk: revert the skill text and reference pages to the previous narrower credential contract. No runtime data migration is required.

## Open Questions

- No blocking design questions. Future Houmao CLI changes may add more import surfaces, but this change assumes the current create-command auth flags remain unchanged.
