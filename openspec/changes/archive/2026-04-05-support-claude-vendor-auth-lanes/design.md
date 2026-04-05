## Context

Houmao’s current Claude auth contract is narrower than upstream Claude Code’s maintained auth surfaces.

Today Houmao can persist Claude auth only through:

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_AUTH_TOKEN`
- optional endpoint/model env

Houmao can also carry optional Claude runtime bootstrap state through `claude_state.template.json`, but that file is not itself a credential-providing method.

That is reflected in the low-level project auth CLI, the project-easy specialist CLI, the Claude adapter allowlist, and the `houmao-create-specialist` skill guidance. The result is a user-visible mismatch: a machine can be fully healthy for `claude auth login`, but Houmao still cannot turn that login into a reusable Claude specialist without a separate manual export step.

The local upstream Claude source shows two vendor-supported lanes that Houmao does not currently model:

- explicit OAuth-token auth through `CLAUDE_CODE_OAUTH_TOKEN`,
- full login state under `CLAUDE_CONFIG_DIR`, especially `.credentials.json` plus `.claude.json`.

Houmao already launches Claude inside an isolated runtime home selected through `CLAUDE_CONFIG_DIR`, and the current bootstrap path already preserves an existing `.claude.json` when it finds one. That makes this a contract gap more than a greenfield runtime design.

## Goals / Non-Goals

**Goals:**

- Let Houmao represent the maintained vendor-supported Claude auth lanes that operators actually use today.
- Make those lanes available on both low-level project auth management and high-level easy specialist creation.
- Let `houmao-create-specialist` treat a normal Claude login as importable when the user explicitly opts into discovery.
- Preserve unattended Claude startup without rewriting or breaking vendor-owned login files that Houmao imported into the runtime home.
- Keep the new behavior aligned with the existing project auth-bundle model rather than inventing a side channel outside `.houmao/agents/tools/claude/auth/`.
- Make the docs, CLI reference, and packaged skill guidance describe Claude credential methods separately from optional runtime-state templates so operators are not misled.

**Non-Goals:**

- Executing `claude auth login`, `claude setup-token`, or any other auth-generation flow on the user’s behalf.
- Supporting every possible Claude auth source such as `apiKeyHelper`, remote-control-only flows, or file-descriptor-only OAuth transport.
- Copying an entire Claude config directory blindly into Houmao auth bundles.
- Redesigning the general auth-bundle storage model for Codex, Gemini, or unrelated tools.

## Decisions

### 1. Add two explicit Claude vendor auth lanes, and keep them distinct

Houmao will add support for:

- a long-lived OAuth token lane represented as `CLAUDE_CODE_OAUTH_TOKEN`,
- a full login-state lane imported from a Claude config root and persisted as vendor-owned files inside the auth bundle.

These lanes will remain distinct from:

- `ANTHROPIC_API_KEY`,
- `ANTHROPIC_AUTH_TOKEN`,
- optional bootstrap inputs such as `claude_state.template.json`, which remain runtime-state templates rather than credential methods.

Why this approach:

- It matches upstream Claude Code behavior instead of forcing operators to reinterpret vendor auth into Houmao-only terms.
- It resolves both real operator postures we saw during investigation: already logged in through `claude auth login`, or using the supported `claude setup-token` output.
- It avoids conflating full-scope login state with inference-only token state.

Alternatives considered:

- Support only `CLAUDE_CODE_OAUTH_TOKEN`. Rejected because it does not solve the main ergonomics gap for already-logged-in Claude users.
- Translate imported login state into `ANTHROPIC_AUTH_TOKEN`. Rejected because it collapses distinct upstream auth semantics and risks lifetime/scope errors.

### 1a. Keep `claude_state.template.json` as optional bootstrap state, not as a Claude credential lane

Houmao will continue to support `claude_state.template.json` as optional Claude runtime-state seed data carried inside the auth bundle.

That file will be treated as:

- optional input,
- runtime bootstrap material,
- separate from credential-providing Claude auth lanes.

It will not be described as one of the ways to authenticate Claude, and discovery guidance must not count the presence of only a reusable state template as proof that usable Claude credentials exist.

Why this approach:

- It matches what the runtime actually does with the file today: seed or patch `.claude.json` startup state.
- It makes the operator-facing Claude auth model easier to understand.
- It avoids overstating what a template file can do on its own.

Alternatives considered:

- Keep listing the state template alongside credential lanes for convenience. Rejected because that wording is misleading and obscures the real credential contract.

### 2. Expose login-state import through `CLAUDE_CONFIG_DIR`-style input, but persist only selected vendor files

The operator-facing import surface will be a Claude config-root input:

- low-level Claude auth management gets a Claude config-dir import flag,
- easy specialist creation gets the corresponding Claude-prefixed config-dir import flag.

When Houmao imports that directory, it will copy only the Claude-owned files needed for reusable login state:

- `.credentials.json`
- `.claude.json` when present

Those files will be stored under the Claude auth bundle’s `files/` directory and later projected back into the isolated runtime home under the same filenames.

Why this approach:

- `CLAUDE_CONFIG_DIR` is the maintained upstream unit of Claude login state.
- A config-dir import is simpler and more natural for operators than asking for two separate file paths.
- Copying only the known vendor auth files avoids dragging unrelated history, logs, plugins, or local state into the auth bundle.

Alternatives considered:

- Separate `--credentials-file` and `--global-state-file` flags only. Rejected because the common real-world source is a config root, not two hand-picked files.
- Copy the full config directory. Rejected because it would import unrelated and drift-prone Claude state into Houmao.

### 3. Treat imported vendor login files as opaque auth artifacts, and keep runtime bootstrap additive

Houmao will treat imported `.credentials.json` and `.claude.json` as opaque vendor-owned artifacts:

- auth bundle storage copies them as files,
- `auth get` reports their presence and paths without dumping content,
- adapter projection copies them into the runtime Claude home,
- runtime bootstrap does not parse or rewrite `.credentials.json`,
- runtime bootstrap preserves imported `.claude.json` and limits its own mutations to strategy-owned startup/trust surfaces.

If projected vendor login state already provides `.claude.json`, Houmao must not require `claude_state.template.json` just to start unattended. Template-driven `.claude.json` synthesis remains the fallback path for the existing minimal-credential lanes.

Why this approach:

- Upstream owns these file formats and may evolve them; opaque copy is more stable than partial semantic rewriting.
- The current bootstrap contract already prefers preserving an existing runtime `.claude.json`, so the change fits the current model.
- This keeps the new login-state lane compatible with the existing unattended strategy ownership boundaries.

Alternatives considered:

- Parse and normalize imported `.credentials.json` into Houmao-native fields. Rejected because Houmao would become responsible for vendor token schema churn.
- Rebuild `.claude.json` from imported login data every launch. Rejected because it is unnecessary when vendor state is already present and makes Houmao the owner of more Claude state than needed.

### 4. Make auto-credentials map vendor-supported Claude state into explicit Houmao inputs

The `houmao-create-specialist` skill and Claude lookup reference will treat these as importable discovered Claude shapes:

- `CLAUDE_CODE_OAUTH_TOKEN`,
- a Claude config root containing `.credentials.json` and/or `.claude.json` in the maintained locations needed for the login-state lane.

The skill will continue to reject genuinely non-importable Claude shapes such as `apiKeyHelper`-only configurations.

Why this approach:

- It fixes the current “Claude is logged in, but Houmao still says unsupported” mismatch.
- It preserves the existing explicit-consent model because the skill still scans only when the user asks for `auto credentials` or another supported discovery mode.
- It keeps importability aligned with the actual CLI flags Houmao now exposes.

Alternatives considered:

- Keep skill behavior unchanged and only add low-level CLI support. Rejected because it would leave the easy-specialist UX gap unresolved.

## Risks / Trade-offs

- [Imported login bundles contain stronger credential material than API-key lanes] → Keep storage inside the existing project auth-bundle secret boundary, preserve redaction in `auth get`, and require explicit user input or explicit credential-discovery opt-in before importing.
- [Upstream Claude login-file formats may drift] → Treat vendor files as opaque copied artifacts and avoid schema-dependent rewrites wherever possible.
- [Full login state and `CLAUDE_CODE_OAUTH_TOKEN` do not have identical capability scope] → Expose them as separate lanes and document the distinction instead of pretending they are interchangeable.
- [Config-dir import may pull stale or partial login state] → Require the maintained vendor files that define the selected lane and fail clearly when the requested config root does not contain enough Claude login material.
- [Docs or skill guidance still present the state template as credentials] → Add explicit skill and docs requirements that describe `claude_state.template.json` as optional bootstrap state rather than a credential lane.

## Migration Plan

1. Extend Claude auth bundle CLI surfaces and easy-specialist CLI surfaces with the new vendor-lane inputs.
2. Extend the Claude adapter projection contract to include `CLAUDE_CODE_OAUTH_TOKEN` and imported vendor login files.
3. Update Claude runtime bootstrap so imported vendor login-state files remain valid unattended inputs.
4. Update the `houmao-create-specialist` skill/reference guidance and related docs to describe the new importable Claude lanes and to classify `claude_state.template.json` only as optional bootstrap state.
5. Add regression coverage for low-level auth bundles, easy specialists, skill text, and unattended runtime preparation.

No repository data migration is required for existing Claude bundles. Existing API-key, `ANTHROPIC_AUTH_TOKEN`, and template-driven bundles remain valid. Rollback is straightforward: revert the new CLI/adapter/bootstrap behavior and remove any newly created vendor-lane Claude bundles from the overlay if they are no longer desired.

## Open Questions

- No blocking open questions. The follow-up implementation should explicitly document whether `.claude.json` is mandatory or optional during config-dir import, but that does not change the overall design direction.
