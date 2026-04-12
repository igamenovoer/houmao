## Context

Houmao already has a unified launch-owned model-selection contract. Recipes, specialists, launch profiles, and direct launch flags resolve into one effective model configuration, and the runtime records secret-free model-selection provenance in the brain manifest.

The current Claude projection uses `ANTHROPIC_MODEL` for model name and `settings.json` `effortLevel` for reasoning effort. That is valid Claude state in isolation, but the local interactive TUI path constructs a direct tmux `claude ...` command rather than executing the generated `launch.sh`. A live probe showed the generated home had `ANTHROPIC_MODEL=sonnet` in `launch.sh`, but the live Claude process did not receive that env var and rendered the Claude Max account default, `Opus 4.6 (1M context)`. A direct probe with `claude --model sonnet --effort high` rendered `Sonnet 4.6 with high effort`, so the Claude CLI arguments are the right startup authority for the user preference.

## Goals / Non-Goals

**Goals:**

- Make launch-owned Claude model preferences effective in both local interactive TUI and headless Claude launches.
- Make launch-owned Claude reasoning preset preferences effective in both local interactive TUI and headless Claude launches when the preset maps to a Claude effort level.
- Preserve existing model-selection precedence and secret-free provenance.
- Keep imported Claude env variables such as `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, and `CLAUDE_CODE_SUBAGENT_MODEL` available as native baseline/auth-bundle inputs.

**Non-Goals:**

- Do not remove support for Claude model-selection env vars from auth bundles or copied native state.
- Do not introduce exact token-budget or vendor-native advanced thinking controls beyond Houmao's existing reasoning preset index.
- Do not change Codex or Gemini model-selection behavior except where shared provenance plumbing needs to represent Claude CLI arguments.

## Decisions

1. Use Claude CLI args as the final authority for Houmao-managed Claude launch overrides.

   When the effective model name comes from a Houmao launch-owned layer above `baseline_native`, generate `--model <name>` for Claude provider startup. When the effective reasoning preset maps to a Claude native effort value, generate `--effort <low|medium|high|max>`. This matches Claude's documented/current CLI surface and avoids relying on env propagation through tmux.

   Alternative considered: continue using `ANTHROPIC_MODEL` and fix local interactive env injection. That would solve this specific TUI bug, but it would still leave the user preference less visible in final provider args and keep effort split between runtime-home mutation and launch semantics.

2. Keep Claude env vars as native baseline, not as the primary launch-owned override surface.

   Auth bundles and copied native state may still provide `ANTHROPIC_MODEL` or alias pinning vars. Those values should remain part of the low-priority baseline layer. Houmao-authored source/profile/direct overrides should become final CLI args so they win consistently for the managed launch without rewriting auth state.

   Alternative considered: remove `ANTHROPIC_MODEL` support entirely. That would be a breaking change for existing auth-bundle/native-state workflows and is not necessary for the bug.

3. Thread generated Claude CLI args through the launch plan.

   The brain build step should record Claude model/effort CLI projection in the model-selection contract. Launch-plan construction should append those non-secret final provider args for Claude in the same phase that it already appends Codex model-selection CLI config overrides. Local interactive and headless backends should consume the resulting launch plan args rather than re-deriving model preference.

   Alternative considered: special-case local interactive command construction. That would fix TUI only and risk leaving headless behavior inconsistent.

4. Preserve provenance and test against visible launch surfaces.

   The manifest should show the resolved model config, the native Claude projection, and any generated final CLI args. Tests should assert the launch plan or backend command includes `--model` and `--effort`, and at least one live or integration-style validation should cover that Claude TUI displays the selected model/effort when practical.

## Risks / Trade-offs

- Claude CLI version drift could rename or change `--effort` semantics -> keep behavior tied to the existing version-scoped launch-policy coverage and fail clearly if a maintained Claude version no longer supports the arg.
- Passing model names in CLI args makes preferences visible in process listings -> acceptable because model names and effort levels are non-secret launch preferences; do not pass auth tokens or API keys this way.
- Baseline env values and launch-owned CLI args can disagree -> this is expected precedence; CLI args represent the higher-priority Houmao launch-owned override, while env values remain native baseline/imported state.
- Request-scoped headless overrides may need temporary args as well as temporary home projection -> keep those args scoped to the accepted prompt execution and do not mutate later default execution state.
