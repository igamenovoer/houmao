## Context

Codex loads configuration from more than one place. Houmao currently writes model selection, reasoning effort, and unattended startup settings into the generated `CODEX_HOME/config.toml`, but Codex also loads project-local `.codex/config.toml` from the launch working directory. When a workspace config defines the same keys, it can override the generated home and the live Codex TUI can show a different preference than the Houmao manifest says it requested.

The observed failure is a Codex launch surface problem rather than a reasoning-ladder problem. Houmao resolved reasoning level `2` to `model_reasoning_effort = "low"` in the generated home, but the workspace's `.codex/config.toml` had `model_reasoning_effort = "high"`, so the live Codex status line used `high`.

Codex already exposes `-c, --config <key=value>` as a CLI config override layer. A manual spike confirmed that invoking the generated launch helper with `-c model_reasoning_effort="low"` made the live TUI show `gpt-5.4 low` despite the project config.

## Goals / Non-Goals

**Goals:**

- Make Houmao-owned Codex preferences win over cwd/project `.codex/config.toml` during provider startup.
- Keep generated `CODEX_HOME/config.toml` projection for fallback behavior, inspection, and launches where no project config overrides the generated home.
- Keep secrets out of process arguments.
- Apply the same effective Codex preference contract across generated raw `launch.sh`, runtime-managed local interactive launches, Codex headless launches, and headless request-scoped execution overrides.
- Preserve explicit last-mile manual override behavior for operators who intentionally append extra args to a generated `launch.sh` invocation.

**Non-Goals:**

- Do not mutate user or project `.codex/config.toml` files to solve precedence.
- Do not remove generated Codex home config projection.
- Do not put API keys, auth JSON, OAuth tokens, or other secrets in CLI args.
- Do not change the reasoning ladder semantics or the user-facing `reasoning.level` field.
- Do not add a new dependency solely for TOML writing unless existing repository utilities cannot safely serialize scalar CLI override values.

## Decisions

### Decision: Treat Codex CLI config overrides as the authoritative preference layer

For Codex, any non-secret setting that Houmao resolves as an effective launch preference should be emitted as a final CLI config override in addition to any generated home config mutation.

Examples:

```text
--config=model="gpt-5.4"
--config=model_reasoning_effort="low"
--config=approval_policy="never"
--config=sandbox_mode="danger-full-access"
--config=model_provider="yunwu-openai"
--config='model_providers."yunwu-openai".wire_api="responses"'
```

Rationale: CLI config overrides are the Codex-supported way to override loaded config layers and avoid accidental cwd-project precedence. The generated runtime home remains useful state, but it is not sufficient as the authority boundary.

Alternative considered: launch Codex from a neutral cwd to avoid project config discovery. That would change workspace semantics and would not help headless turns that must run in the target project.

Alternative considered: write or patch project `.codex/config.toml` to match Houmao preferences. That would mutate user project state and does not respect the user's explicit instruction to avoid modifying unrelated projects.

### Decision: Keep generated home config projection as fallback and provenance

The builder should still write the resolved Codex preferences to the generated runtime `config.toml`. This preserves current inspectability and makes behavior reasonable when a cwd has no project-local Codex config.

Rationale: Generated home config is still a useful durable artifact and keeps compatibility with direct provider invocations that do not consume Houmao's launch args. The new CLI layer is an additional authoritative launch surface, not a removal of existing projection.

### Decision: Build a small Codex preference-override helper instead of ad hoc arg strings

Implement a central helper that converts supported Codex preference projections into `--config=<toml-key-path>=<toml-value>` args. It should be used by both build-time launch-helper generation and runtime launch-plan reconstruction.

The helper should:

- only emit non-secret values,
- serialize TOML string/bool/int scalars safely,
- quote dotted key-path components when needed, especially provider names and filesystem project paths,
- preserve a secret-free manifest/provenance payload describing which CLI override keys were generated,
- de-duplicate or replace earlier Houmao-generated overrides for the same key when rebuilding launch plans.

Rationale: There are multiple launch paths. A central helper reduces the chance that generated `launch.sh`, runtime-managed `local_interactive`, and `codex_headless` diverge.

### Decision: Append Houmao-owned overrides after normal launch overrides and unattended canonicalization

The final provider command should put Houmao-owned Codex preference overrides after adapter defaults, recipe/direct launch overrides, and unattended strategy canonicalization.

For generated raw helpers, explicit operator passthrough supplied to `launch.sh "$@"` can remain after Houmao-generated args. That preserves manual debugging escape hatches without weakening normal managed launch behavior.

Rationale: Managed launches should not be accidentally overridden by stored project config or recipe launch args. A user who manually invokes a helper with extra args is making an explicit one-off choice.

### Decision: Extend launch policy with final Codex config override emission

The Codex unattended policy already canonicalizes conflicting caller `-c` overrides for strategy-owned keys and mutates runtime-home `config.toml`. It should also append final CLI config overrides for the strategy-owned non-secret startup preferences it promises, such as approval and sandbox posture.

Rationale: The same cwd project config layer that can override reasoning can also override no-prompt startup preferences. Strategy ownership should be represented in the final process argv, not only runtime-home files.

### Decision: Keep secrets in env/files

Provider API keys and auth state stay in env vars and projected files. If Houmao pins a selected env-only provider via CLI config, it may pass non-secret provider contract fields like provider name, base URL, `env_key`, `requires_openai_auth`, and `wire_api`, but the key value itself must remain env-provided.

Rationale: Process argv is easier to inspect from system tools and logs. It is not an appropriate channel for credentials.

## Risks / Trade-offs

- Codex CLI parsing may have edge cases for quoted dotted key paths → Mitigate with unit tests that assert exact argv strings and a live or smoke launch test for provider names and workspace paths that require quoting.
- CLI args become longer when provider contract fields are pinned → Mitigate by only emitting non-secret fields that affect Houmao-owned selection and by keeping generated config as the durable full-state artifact.
- Runtime-home config and CLI overrides can drift if generated independently → Mitigate by deriving both from the same resolved model/preference projection payload and recording the CLI override payload in manifest metadata.
- Manual `launch.sh "$@"` passthrough can still override Houmao-generated preferences → Accept as an intentional operator escape hatch and document/test the normal managed path separately.
- Some Codex startup state may be better represented as state than preference, such as trust or migration notice state → Start by pinning the non-secret preferences that Codex accepts cleanly through `--config`; keep stateful fallback mutation for runtime-home config and add CLI pinning for dynamic paths only when tests confirm reliable parsing.

## Migration Plan

Existing generated Codex homes can continue to work as before. New or rebuilt homes will include the same runtime `config.toml` settings plus final CLI config overrides in the launch helper and runtime launch plan.

Rollback is straightforward: remove the generated CLI override emission and rely on the existing runtime-home config mutation. No user project config migration is required.

## Open Questions

- Should dynamic project-trust entries be emitted through CLI config overrides for every Codex launch, or should they remain runtime-home state unless a regression demonstrates project config can override trust in practice?
- Should provider contract pinning include all selected provider fields from setup config, or only `model_provider` plus the minimal env-only provider fields needed for credential readiness?
