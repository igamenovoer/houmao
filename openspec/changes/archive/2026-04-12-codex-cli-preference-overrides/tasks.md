## 1. Codex CLI Override Projection

- [x] 1.1 Add a shared Codex CLI config override helper that renders non-secret TOML scalar values and quoted dotted key paths safely.
- [x] 1.2 Extend Codex model-name projection so resolved launch-owned model values still patch runtime `config.toml` and also produce CLI override records.
- [x] 1.3 Extend Codex reasoning projection so resolved native `model_reasoning_effort` values still patch runtime `config.toml` and also produce CLI override records.
- [x] 1.4 Record generated Codex CLI override metadata in the brain manifest or launch metadata without including secret values.
- [x] 1.5 Add provider-selection CLI override support for non-secret Codex provider fields that Houmao owns, keeping API keys and auth state in env/files.

## 2. Launch Path Integration

- [x] 2.1 Update generated Codex `launch.sh` synthesis to include Houmao-generated CLI config overrides after adapter/recipe/direct launch args and before explicit helper passthrough args.
- [x] 2.2 Update runtime launch-plan reconstruction so `local_interactive` and `codex_headless` Codex launches receive the same resolved CLI preference overrides.
- [x] 2.3 Update Codex headless request-scoped `execution.model` handling so per-turn model/reasoning overrides are passed as CLI config overrides for that turn.
- [x] 2.4 Ensure generated runtime-home `config.toml` projection remains in place for fallback and inspection.

## 3. Launch Policy Integration

- [x] 3.1 Extend Codex unattended launch policy handling to append final CLI config overrides for strategy-owned approval and sandbox posture.
- [x] 3.2 Ensure Codex unattended canonicalization removes or replaces conflicting caller `-c`/`--config` overrides before strategy-owned overrides are appended.
- [x] 3.3 Update Codex launch-policy registry metadata to describe CLI config override surfaces alongside runtime-home `config.toml` mutation.
- [x] 3.4 Keep strategy-owned secret handling out of argv by validating that emitted CLI override values exclude API keys, auth JSON, OAuth tokens, cookies, and bearer tokens.

## 4. Tests

- [x] 4.1 Add unit coverage for Codex CLI override serialization, including quoted provider names and non-secret scalar values.
- [x] 4.2 Add `build_brain_home` coverage proving Codex model and reasoning projection writes runtime `config.toml` and emits matching launch-helper CLI overrides.
- [x] 4.3 Add runtime launch-plan coverage proving `local_interactive` and `codex_headless` retain Houmao-owned Codex CLI overrides after launch policy application.
- [x] 4.4 Add Codex headless command coverage proving request-scoped `execution.model.reasoning.level = 2` emits a per-turn `model_reasoning_effort = "low"` CLI override.
- [x] 4.5 Add launch-policy coverage proving unattended Codex approval/sandbox conflicts are canonicalized and final strategy-owned CLI overrides are present.
- [x] 4.6 Add regression coverage with a cwd project `.codex/config.toml` value that conflicts with a generated Codex home value, verifying the final command carries the Houmao-owned override.
- [x] 4.7 Add negative coverage proving secret env/auth values are not copied into generated CLI override args or manifest metadata.

## 5. Validation

- [x] 5.1 Run `openspec validate codex-cli-preference-overrides --strict`.
- [x] 5.2 Run focused unit tests for model mapping, brain builder, launch policy, launch-plan reconstruction, and Codex headless command assembly.
- [x] 5.3 Run the smallest practical live or smoke Codex launch in a temporary project with a conflicting `.codex/config.toml` to confirm the live TUI/headless status uses Houmao's CLI-provided preference.
